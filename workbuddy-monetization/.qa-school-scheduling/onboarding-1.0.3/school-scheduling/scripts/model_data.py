from __future__ import annotations

from collections import defaultdict
from itertools import product
from common import InputError, minute, integer
from expand_calendar import available, window_applies


def participants(data, group_ids, day=None):
    students = set()
    for group in data['groups']:
        if group['id'] not in group_ids:
            continue
        students.update(group.get('student_ids', []))
        for member in group.get('memberships', []):
            if day is None or member.get('from', '0001-01-01') <= day <= member.get('to', '9999-12-31'):
                students.add(member['student_id'])
    return students


def groups_conflict(data, a, b, day):
    if set(a) & set(b) or participants(data, a, day) & participants(data, b, day):
        return True
    return any(g['id'] in a and set(g.get('exclusive_with', [])) & set(b) or
               g['id'] in b and set(g.get('exclusive_with', [])) & set(a) for g in data['groups'])


def demand_variant(demand, week_type):
    d = dict(demand)
    d.update(demand.get('rotation', {}).get(week_type, {}))
    return d


def scopes(data, demand):
    days = [x for x in data['expanded_calendar'] if x['week_type'] in demand.get('week_types', data['calendar'].get('week_types', ['all']))]
    groups = defaultdict(list)
    for day in days:
        scope = demand['quota'].get('scope', 'week')
        key = day['cycle'] if scope == 'week' else day['week_type'] if scope == 'week_type' else 'range'
        groups[key].append(day)
    if not groups:
        raise InputError(f'需求 {demand["id"]} 在排课范围内没有有效周期')
    return groups


def amount(d):
    q = d['quota']
    target = q['value'] * (q.get('minutes_per_unit', 1) if q['unit'] == 'units' else 1)
    if q['unit'] == 'sessions':
        return target, None
    if len(d['duration_options']) == 1:
        size = d['duration_options'][0]
        if target % size:
            raise InputError(f'{d["id"]} 配额分钟数不能由课长整除')
        return target // size, target
    return d['session_count'], target


def sessions(data):
    result = []
    for d in data['demands']:
        count, target = amount(d)
        for scope, days in scopes(data, d).items():
            for index in range(count):
                result.append({'id': f'{d["id"]}@{scope}#{index + 1}', 'demand_id': d['id'],
                               'scope': scope, 'index': index + 1, 'target_minutes': target,
                               'days': days, 'demand': d})
    return result


def location(data, resource_ids, d):
    campuses = {r.get('campus_id', 'default') for r in data['resources'] if r['id'] in resource_ids}
    if len(campuses) > 1:
        return None
    return next(iter(campuses), d.get('campus_id', 'default'))


def time_options(data, d, day, duration):
    for slot in data['slots']:
        if d.get('slot_ids') and slot['id'] not in d['slot_ids']:
            continue
        if slot.get('group_ids') and not set(d['group_ids']) <= set(slot['group_ids']):
            continue
        if not window_applies(slot, day):
            continue
        start, end = minute(slot['start']), minute(slot['end'])
        if slot.get('flexible', False):
            step = integer(slot.get('step_minutes', 5), 'slots.step_minutes', 1)
            for t in range(start, end - duration + 1, step):
                yield slot['id'], t, t + duration, slot.get('half_day', 'am' if t < 720 else 'pm')
        elif end - start == duration:
            yield slot['id'], start, end, slot.get('half_day', 'am' if start < 720 else 'pm')


def fits_spec(candidate, spec):
    for key in ['date', 'slot_id', 'start', 'teacher_ids', 'resource_ids', 'campus_id']:
        if key not in spec:
            continue
        value = minute(spec[key]) if key == 'start' and isinstance(spec[key], str) else spec[key]
        if isinstance(value, list):
            if set(candidate[key]) != set(value):
                return False
        elif candidate[key] != value:
            return False
    if 'weekday' in spec and candidate['weekday'] != spec['weekday']:
        return False
    return True


def candidate_allowed(data, d, c, day):
    if not available(d, c, day):
        return False
    for name, ids in [('teachers', c['teacher_ids']), ('groups', c['group_ids']),
                      ('students', participants(data, c['group_ids'], c['date']))]:
        for p in data[name]:
            if p['id'] in ids and not available(p, c, day):
                return False
    members = participants(data, c['group_ids'], c['date'])
    headcount = len(members) if members else sum(g.get('size', 0) for g in data['groups'] if g['id'] in c['group_ids'])
    for r in data['resources']:
        if r['id'] not in c['resource_ids']:
            continue
        if r.get('seats') is not None and headcount > r['seats']:
            return False
        if not set(d.get('required_features', [])) <= set(r.get('features', [])):
            return False
        extended = dict(c, start=c['start'] - r.get('setup_minutes', 0), end=c['end'] + r.get('cleanup_minutes', 0))
        if extended['start'] < 0 or extended['end'] > 1440 or not available(r, extended, day):
            return False
    if d.get('required_qualification'):
        for t in data['teachers']:
            if t['id'] in c['teacher_ids'] and d['required_qualification'] not in t.get('qualifications', []):
                return False
    return True


def external_conflict(data, c):
    persons = set(c['teacher_ids']) | participants(data, c['group_ids'], c['date'])
    for ext in data.get('external_occupancy', []):
        if ext['date'] != c['date']:
            continue
        a, b = minute(ext['start']), minute(ext['end'])
        if set(ext.get('person_ids', [])) & persons or groups_conflict(data, ext.get('group_ids', []), c['group_ids'], c['date']):
            shared = set(ext.get('person_ids', [])) & persons
            rest = max([p.get('rest_minutes', 0) for k in ['teachers', 'students'] for p in data[k] if p['id'] in shared] or [0])
            if c['start'] < b and a < c['end']:
                return True
            if b <= c['start']:
                gap = required_travel(data, ext.get('campus_id', 'default'), c['campus_id'])
                if gap is None or c['start'] - b < max(gap, rest):
                    return True
            elif c['end'] <= a:
                gap = required_travel(data, c['campus_id'], ext.get('campus_id', 'default'))
                if gap is None or a - c['end'] < max(gap, rest):
                    return True
        for r in data['resources']:
            if r['id'] in c['resource_ids'] and r['id'] in ext.get('resource_ids', []):
                # Capacity is handled cumulatively, not as an unconditional pair conflict.
                pass
    return False


def required_travel(data, source, target):
    if source == target or source == 'online' or target == 'online':
        return data.get('transition_minutes', 0)
    return data.get('travel_minutes', {}).get(source, {}).get(target)


def incompatible(data, a, b):
    if a['date'] != b['date']:
        return False
    ap = set(a['teacher_ids']) | participants(data, a['group_ids'], a['date'])
    bp = set(b['teacher_ids']) | participants(data, b['group_ids'], b['date'])
    shared = ap & bp or groups_conflict(data, a['group_ids'], b['group_ids'], a['date'])
    if not shared:
        return False
    if a['start'] < b['end'] and b['start'] < a['end']:
        return True
    first, second = (a, b) if a['start'] <= b['start'] else (b, a)
    travel = required_travel(data, first['campus_id'], second['campus_id'])
    rest = max([p.get('rest_minutes', 0) for k in ['teachers', 'students'] for p in data[k] if p['id'] in ap & bp] or [0])
    return travel is None or second['start'] - first['end'] < max(travel, rest)


def build_candidates(data):
    result, empty = [], []
    locks = {l['session_id']: l for l in data.get('locks', [])}
    for s in sessions(data):
        if s['id'] in data.get('canceled_sessions', []):
            continue
        opts = []
        override = data.get('session_overrides', {}).get(s['id'], {})
        days = [d for d in data['expanded_calendar'] if d['date'] == override['date']] if override.get('date') else s['days']
        for day in days:
            d = demand_variant(s['demand'], day['week_type'])
            if override:
                d = dict(d, **override.get('demand', {}))
            if day['date'] in d.get('exclude_dates', []):
                continue
            teacher_choices = d.get('eligible_teacher_ids', []) or [None]
            room_choices = d.get('eligible_resource_ids', []) or [None]
            for duration in d['duration_options']:
                for slot_id, start, end, half in time_options(data, d, day, duration):
                    for teacher, room in product(teacher_choices, room_choices):
                        tids = sorted(set(d.get('teacher_ids', []) + ([teacher] if teacher else [])))
                        rids = sorted(set(d.get('resource_ids', []) + ([room] if room else [])))
                        campus = location(data, rids, d)
                        if campus is None:
                            continue
                        c = {'session_id': s['id'], 'demand_id': s['demand_id'], 'scope': s['scope'],
                             'date': day['date'], 'week_type': day['week_type'], 'weekday': day['weekday'],
                             'slot_id': slot_id, 'start': start, 'end': end, 'half_day': half,
                             'course_id': d['course_id'], 'group_ids': d['group_ids'],
                             'teacher_ids': tids, 'resource_ids': rids, 'campus_id': campus,
                             'status': 'scheduled'}
                        fixed = [f for f in d.get('fixed', []) if f.get('session_index', 1) == s['index'] and
                                 f.get('scope', s['scope']) == s['scope']]
                        if not override.get('replace_fixed') and any(not fits_spec(c, f) for f in fixed):
                            continue
                        if s['id'] in locks and not fits_spec(c, locks[s['id']]):
                            continue
                        if candidate_allowed(data, d, c, day) and not external_conflict(data, c):
                            opts.append(c)
                            if len(opts) > 20000:
                                raise InputError('单实例候选超过20000，请缩小日期/时间窗口或增加时间步长', s['id'], 'SCALE_LIMIT')
        unique = {tuple([c['date'], c['start'], c['end'], c['slot_id'], tuple(c['teacher_ids']), tuple(c['resource_ids'])]): c for c in opts}
        opts = list(unique.values())
        if not opts:
            empty.append(s['id'])
        result.append((s, opts))
        if sum(len(cs) for _, cs in result) > 150000:
            raise InputError('候选总量超过150000，请缩小任务或锁定部分安排', code='SCALE_LIMIT')
    unknown = set(locks) - {s['id'] for s, _ in result}
    if unknown:
        raise InputError(f'锁定了不存在的教学实例 {sorted(unknown)}')
    return result, empty
