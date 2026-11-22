from __future__ import annotations

import time
from collections import defaultdict
from itertools import combinations
from ortools.sat.python import cp_model
from common import digest, stamp, VERSION, minute
from model_data import build_candidates, incompatible, participants, amount
from rule_spec import selected, entities, preferred, bad, absolute


def solve(data, time_limit=120, workers=1, seed=0):
    started = time.monotonic()
    model = cp_model.CpModel()
    prepared, empty = build_candidates(data)
    base = {'version': VERSION, 'input_hash': digest(data), 'rule_hash': digest(data['rules']),
            'calendar_hash': digest(data['expanded_calendar']), 'generated_at': stamp(),
            'parameters': {'time_limit': time_limit, 'workers': workers, 'seed': seed}}
    if empty:
        return dict(base, status='INFEASIBLE', assignments=[], diagnostics=[{'code': 'NO_CANDIDATES', 'session_id': s} for s in empty], layers=[])
    if time_limit <= 0:
        return dict(base, status='UNKNOWN', assignments=[], diagnostics=[{'code': 'TIME_BUDGET_EXHAUSTED'}], layers=[])
    records, by_session = [], {}
    for session, candidates in prepared:
        rows = []
        for candidate in candidates:
            var = model.new_bool_var(f'c{len(records)}')
            rows.append(len(records))
            records.append((candidate, var))
        by_session[session['id']] = rows
        model.add_exactly_one(records[j][1] for j in rows)
    # Quota minutes are independent of session count when lengths are selectable.
    scoped = defaultdict(list)
    for i, (c, v) in enumerate(records):
        scoped[c['demand_id'], c['scope']].append(i)
    quota_checked = set()
    for s, _ in prepared:
        key = (s['demand_id'], s['scope'])
        if key not in quota_checked and s['target_minutes'] is not None:
            quota_checked.add(key)
            canceled_minutes = sum(value for sid, value in data.get('canceled_minutes', {}).items() if sid.rsplit('#', 1)[0] == s['id'].rsplit('#', 1)[0])
            model.add(sum((records[j][0]['end'] - records[j][0]['start']) * records[j][1]
                          for j in scoped[s['demand_id'], s['scope']]) == s['target_minutes'] - canceled_minutes)
    # Index conflicts by actual participants, including split groups and mutual exclusion.
    buckets = defaultdict(set)
    for i, (c, _) in enumerate(records):
        keys = ['p:' + t for t in c['teacher_ids']] + ['p:' + s for s in participants(data, c['group_ids'], c['date'])]
        keys += ['g:' + g for g in c['group_ids']]
        for g in data['groups']:
            for other in g.get('exclusive_with', []):
                if g['id'] in c['group_ids'] or other in c['group_ids']:
                    keys.append('ex:' + '|'.join(sorted([g['id'], other])))
        for key in keys:
            buckets[c['date'], key].add(i)
    checked = set()
    for ids in buckets.values():
        for a, b in combinations(sorted(ids), 2):
            if (a, b) in checked:
                continue
            checked.add((a, b))
            ca, va = records[a]
            cb, vb = records[b]
            if ca['session_id'] != cb['session_id'] and incompatible(data, ca, cb):
                model.add(va + vb <= 1)
    # Resource capacity uses buffered optional intervals; external occupancy counts too.
    for resource in data['resources']:
        per_day = defaultdict(lambda: ([], []))
        rid = resource['id']
        for c, v in records:
            if rid not in c['resource_ids']:
                continue
            start, end = c['start'] - resource.get('setup_minutes', 0), c['end'] + resource.get('cleanup_minutes', 0)
            interval = model.new_optional_fixed_size_interval_var(start, end - start, v, f'{rid}:{c["session_id"]}')
            per_day[c['date']][0].append(interval)
            d = next(d for d in data['demands'] if d['id'] == c['demand_id'])
            per_day[c['date']][1].append(d.get('resource_usage', {}).get(rid, 1))
        for ext in data.get('external_occupancy', []):
            if rid in ext.get('resource_ids', []):
                a, b = minute(ext['start']), minute(ext['end'])
                per_day[ext['date']][0].append(model.new_fixed_size_interval_var(a, b - a, 'external'))
                per_day[ext['date']][1].append(ext.get('resource_usage', {}).get(rid, 1))
        for intervals, usage in per_day.values():
            model.add_cumulative(intervals, usage, resource.get('capacity', 1))
    if data['fill_policy'] == 'full':
        for g in data['groups']:
            for day in data['expanded_calendar']:
                from expand_calendar import window_applies
                for slot in data['slots']:
                    if not slot.get('required', True) or slot.get('flexible') or not window_applies(slot, day) or (slot.get('group_ids') and g['id'] not in slot['group_ids']):
                        continue
                    ids = [i for i, (c, _) in enumerate(records) if c['date'] == day['date'] and
                           g['id'] in c['group_ids'] and c['start'] <= minute(slot['start']) and minute(slot['end']) <= c['end']]
                    model.add(sum(records[i][1] for i in ids) == 1)
    # Label symmetry is removed only for demands without user-defined session locks/fixed positions.
    for session, _ in prepared:
        if session['index'] <= 1 or session['demand'].get('fixed') or data.get('locks'):
            continue
        previous = session['id'].rsplit('#', 1)[0] + '#' + str(session['index'] - 1)
        model.add(sum(absolute(records[j][0]) * records[j][1] for j in by_session[previous]) <
                  sum(absolute(records[j][0]) * records[j][1] for j in by_session[session['id']]))

    tiers = defaultdict(list)

    def any_var(ids, name='any'):
        v = model.new_bool_var(name)
        model.add_max_equality(v, [records[j][1] for j in ids] or [0])
        return v

    def conjunction(positive, negative=(), name='and'):
        v = model.new_bool_var(name)
        literals = [records[j][1] for j in positive] + [records[j][1].Not() for j in negative]
        model.add_bool_and(literals).only_enforce_if(v)
        model.add_bool_or([x.Not() for x in literals]).only_enforce_if(v.Not())
        return v

    def add_penalty(rule, expr):
        if rule.get('level', 'hard') == 'hard':
            model.add(expr == 0)
        else:
            tiers[rule.get('tier', 2)].append(rule.get('weight', 1) * expr)

    for rule in data['rules']:
        if not rule.get('enabled', True):
            continue
        ids = [i for i, (c, _) in enumerate(records) if selected(rule, c)]
        typ = rule['type']
        grouped = defaultdict(list)
        for i in ids:
            c = records[i][0]
            for entity in entities(rule, c):
                key = (entity, c['date']) if typ in {'daily_limit', 'same_half_day', 'consecutive', 'minimize_gaps'} else (entity, c['scope'])
                grouped[key].append(i)
        if typ == 'preferred_time':
            add_penalty(rule, sum(records[i][1] for i in ids if not preferred(rule, records[i][0])))
        elif typ in {'synchronize', 'precedence', 'min_gap'}:
            dids = rule.get('demand_ids', [])
            for a, b in combinations(ids, 2):
                ca, va = records[a]
                cb, vb = records[b]
                if ca['session_id'] == cb['session_id']:
                    continue
                if typ == 'synchronize':
                    # Same session index and cycle; across_weeks couples template slots.
                    if ca['demand_id'] not in dids or cb['demand_id'] not in dids:
                        continue
                    if ca['session_id'].rsplit('#', 1)[1] != cb['session_id'].rsplit('#', 1)[1]:
                        continue
                    if not rule.get('across_weeks') and ca['scope'] != cb['scope']:
                        continue
                    if ca['demand_id'] == cb['demand_id'] and not rule.get('across_weeks'):
                        continue
                    mismatch = (ca['weekday'], ca['start']) != (cb['weekday'], cb['start']) if rule.get('across_weeks') else (ca['date'], ca['start']) != (cb['date'], cb['start'])
                elif typ == 'precedence':
                    if {ca['demand_id'], cb['demand_id']} != set(dids) or len(dids) != 2:
                        continue
                    first, second = (ca, cb) if ca['demand_id'] == dids[0] else (cb, ca)
                    mismatch = absolute(first) + first['end'] - first['start'] + rule.get('minutes', 0) > absolute(second)
                else:
                    if not set(entities(rule, ca)) & set(entities(rule, cb)):
                        continue
                    first, second = sorted([ca, cb], key=absolute)
                    mismatch = absolute(second) - absolute(first) - (first['end'] - first['start']) < rule['minutes']
                if mismatch:
                    add_penalty(rule, conjunction([a, b]))
        else:
            for key, js in grouped.items():
                if typ == 'daily_limit':
                    total = sum((records[j][0]['end'] - records[j][0]['start'] if rule.get('unit') == 'minutes' else 1) * records[j][1] for j in js)
                    extra = model.new_int_var(0, 1000000, 'daily_excess')
                    model.add_max_equality(extra, [0, total - rule['max']])
                    add_penalty(rule, extra)
                elif typ == 'same_half_day':
                    halves = defaultdict(list)
                    for j in js:
                        halves[records[j][0]['half_day']].append(j)
                    hs = [any_var(v) for v in halves.values()]
                    excess = model.new_int_var(0, len(hs), 'split')
                    model.add_max_equality(excess, [0, sum(hs) - 1])
                    add_penalty(rule, excess)
                elif typ in {'workdays', 'daily_distribution'}:
                    dates = defaultdict(list)
                    for j in js:
                        dates[records[j][0]['date']].append(j)
                    total = sum(any_var(v) for v in dates.values())
                    short = model.new_int_var(0, rule['target'], 'missing_days')
                    model.add_max_equality(short, [0, rule['target'] - total])
                    add_penalty(rule, short)
                elif typ == 'ampm_balance':
                    halves = {h: [j for j in js if records[j][0]['half_day'] == h] for h in ['am', 'pm']}
                    active = any_var(js)
                    add_penalty(rule, 2 * active - sum(any_var(v) for v in halves.values()))
                elif typ == 'no_all_bad':
                    active = any_var(js)
                    good = any_var([j for j in js if not bad(rule, records[j][0])])
                    add_penalty(rule, active - good)
                elif typ == 'tail_excess':
                    total = sum(records[j][1] for j in js if bad(rule, records[j][0]))
                    excess = model.new_int_var(0, len(js), 'tail')
                    model.add_max_equality(excess, [0, total - rule.get('max', 1)])
                    add_penalty(rule, excess)
                elif typ in {'consecutive', 'minimize_gaps'}:
                    temporal = defaultdict(list)
                    for j in js:
                        c = records[j][0]
                        temporal[c['session_id'], c['date'], c['start'], c['end']].append(j)
                    states = [(records[values[0]][0], any_var(values)) for values in temporal.values()]
                    for (ca, va), (cb, vb) in combinations(states, 2):
                        if ca['session_id'] == cb['session_id']:
                            continue
                        if ca['start'] > cb['start']:
                            ca, cb, va, vb = cb, ca, vb, va
                        gap = cb['start'] - ca['end']
                        if gap <= rule.get('max_break_minutes', 15 if typ == 'consecutive' else 0):
                            continue
                        between = [v for c, v in states if ca['end'] <= c['start'] and c['end'] <= cb['start']]
                        literals = [va, vb] + [v.Not() for v in between]
                        if typ == 'consecutive' and rule.get('level', 'hard') == 'hard':
                            model.add_bool_or([v.Not() for v in literals])
                            continue
                        pen = model.new_bool_var('neighbour_gap')
                        model.add_bool_and(literals).only_enforce_if(pen)
                        model.add_bool_or([v.Not() for v in literals]).only_enforce_if(pen.Not())
                        add_penalty(rule, pen if typ == 'consecutive' else gap * pen)
    # Built-in individual workload limits are expressed as hard capacity constraints.
    for collection in ['teachers', 'students', 'groups']:
        for person in data[collection]:
            for day in data['expanded_calendar']:
                matches = [(c, v) for c, v in records if c['date'] == day['date'] and
                           person['id'] in (c['teacher_ids'] if collection == 'teachers' else c['group_ids'] if collection == 'groups' else participants(data, c['group_ids'], c['date']))]
                if 'daily_minutes' in person:
                    ext_minutes = sum(minute(e['end'])-minute(e['start']) for e in data.get('external_occupancy', [])
                                      if e['date'] == day['date'] and person['id'] in e.get('group_ids' if collection == 'groups' else 'person_ids', []))
                    model.add(sum((c['end'] - c['start']) * v for c, v in matches) + ext_minutes <= person['daily_minutes'])
                if 'daily_sessions' in person:
                    ext_count = sum(e['date'] == day['date'] and person['id'] in e.get('group_ids' if collection == 'groups' else 'person_ids', []) for e in data.get('external_occupancy', []))
                    model.add(sum(v for _, v in matches) + ext_count <= person['daily_sessions'])
    # Optional adjustment baseline: minimize change count at the configured layer.
    baseline = {a['session_id']: a for a in data.get('baseline_assignments', [])}
    if baseline:
        terms = []
        for c, v in records:
            old = baseline.get(c['session_id'])
            if old:
                cost = sum(c[k] != old[k] for k in ['date', 'start', 'teacher_ids', 'resource_ids'])
                if cost:
                    terms.append(cost * v)
        tiers[data.get('change_tier', 1)].extend(terms)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    layers, chosen, overall = [], [], 'UNKNOWN'
    objectives = sorted(tiers.items()) or [(None, [])]
    for tier, terms in objectives:
        remaining = time_limit - (time.monotonic() - started)
        if remaining <= 0:
            break
        solver.parameters.max_time_in_seconds = remaining
        if terms:
            model.minimize(sum(terms))
        status = solver.solve(model)
        name = solver.status_name(status)
        layer = {'tier': tier, 'status': name}
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            chosen = [c for c, v in records if solver.value(v)]
            value = int(round(solver.objective_value)) if terms else 0
            layer.update(value=value, bound=solver.best_objective_bound)
            overall = 'OPTIMAL' if name == 'OPTIMAL' and all(x['status'] == 'OPTIMAL' for x in layers) else 'FEASIBLE'
            if terms:
                model.add(sum(terms) == value)
        else:
            overall = 'FEASIBLE' if chosen else name
            layers.append(layer)
            break
        layers.append(layer)
    if len(layers) < len(objectives) and chosen:
        overall = 'FEASIBLE'
    diagnostics = []
    if not chosen:
        diagnostics.append({'code': overall, 'message': '约束组合不可行' if overall == 'INFEASIBLE' else '尚未找到可行解；未证明无解'})
    chosen.sort(key=lambda c: (c['date'], c['start'], c['session_id']))
    return dict(base, status=overall, assignments=chosen, layers=layers, diagnostics=diagnostics,
                elapsed_seconds=round(time.monotonic() - started, 3), candidate_count=len(records),
                solution_hash=digest(chosen), revision=1,
                version_hash=digest({'input': digest(data), 'assignments': chosen, 'revision': 1}),
                delivery_status='待独立校验')
