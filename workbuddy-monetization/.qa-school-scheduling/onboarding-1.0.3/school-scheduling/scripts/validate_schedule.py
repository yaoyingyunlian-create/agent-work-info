from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from common import digest, minute, stamp
from expand_calendar import available, window_applies
from model_data import sessions, demand_variant, participants, groups_conflict, required_travel, fits_spec
from rule_spec import selected, entities, preferred, bad, absolute


def evaluate_rules(data, rows):
    results = []
    for rule in data['rules']:
        if not rule.get('enabled', True):
            results.append({'rule_id': rule['id'], 'enabled': False, 'penalty': None})
            continue
        items = [c for c in rows if selected(rule, c)]
        typ, details, penalty = rule['type'], [], 0
        grouped = defaultdict(list)
        for c in items:
            for e in entities(rule, c):
                key = (e, c['date']) if typ in {'daily_limit', 'same_half_day', 'consecutive', 'minimize_gaps'} else (e, c['scope'])
                grouped[key].append(c)
        if typ == 'preferred_time':
            penalty = sum(not preferred(rule, c) for c in items)
        elif typ in {'synchronize', 'precedence', 'min_gap'}:
            for a, b in combinations(items, 2):
                if typ == 'synchronize':
                    if a['session_id'].rsplit('#', 1)[1] != b['session_id'].rsplit('#', 1)[1]:
                        continue
                    if not rule.get('across_weeks') and (a['scope'] != b['scope'] or a['demand_id'] == b['demand_id']):
                        continue
                    mismatch = (a['weekday'], a['start']) != (b['weekday'], b['start']) if rule.get('across_weeks') else (a['date'], a['start']) != (b['date'], b['start'])
                elif typ == 'precedence':
                    dids = rule['demand_ids']
                    if {a['demand_id'], b['demand_id']} != set(dids) or len(dids) != 2:
                        continue
                    first, second = (a, b) if a['demand_id'] == dids[0] else (b, a)
                    mismatch = absolute(first) + first['end'] - first['start'] + rule.get('minutes', 0) > absolute(second)
                else:
                    if not set(entities(rule, a)) & set(entities(rule, b)):
                        continue
                    first, second = sorted([a, b], key=absolute)
                    mismatch = absolute(second) - absolute(first) - (first['end'] - first['start']) < rule['minutes']
                if mismatch:
                    penalty += 1
                    details.append([a['session_id'], b['session_id']])
        else:
            for key, group in grouped.items():
                value = 0
                if typ == 'daily_limit':
                    total = sum(c['end'] - c['start'] if rule.get('unit') == 'minutes' else 1 for c in group)
                    value = max(0, total - rule['max'])
                elif typ == 'same_half_day':
                    value = max(0, len({c['half_day'] for c in group}) - 1)
                elif typ in {'workdays', 'daily_distribution'}:
                    value = max(0, rule['target'] - len({c['date'] for c in group}))
                elif typ == 'ampm_balance':
                    value = sum(not any(c['half_day'] == h for c in group) for h in ['am', 'pm'])
                elif typ == 'no_all_bad':
                    value = int(bool(group) and all(bad(rule, c) for c in group))
                elif typ == 'tail_excess':
                    value = max(0, sum(bad(rule, c) for c in group) - rule.get('max', 1))
                elif typ in {'consecutive', 'minimize_gaps'}:
                    ordered = sorted(group, key=lambda c: c['start'])
                    for a, b in zip(ordered, ordered[1:]):
                        gap = b['start'] - a['end']
                        if gap > rule.get('max_break_minutes', 15 if typ == 'consecutive' else 0):
                            value += 1 if typ == 'consecutive' else gap
                penalty += value
                details.append({'entity': key[0], 'scope': key[1], 'penalty': value,
                                'sessions': len(group), 'minutes': sum(c['end'] - c['start'] for c in group)})
        results.append({'rule_id': rule['id'], 'enabled': True, 'level': rule.get('level', 'hard'),
                        'tier': rule.get('tier', 2), 'weight': rule.get('weight', 1),
                        'penalty': penalty, 'details': details})
    return results


def coverage(data, rows):
    demands = data['demands']
    dims = {}
    def put(key, missing, total, na=False):
        state = 'not_applicable' if na else 'complete' if not missing else 'not_provided' if len(missing) == total else 'partial'
        dims[key] = {'status': state, 'missing': missing, 'expected': total, 'checked': max(0, total - len(missing))}
    missing_teachers = []
    for d in demands:
        for wt in d.get('week_types', data['calendar'].get('week_types', ['all'])):
            variant = demand_variant(d, wt)
            if not (variant.get('teacher_ids') or variant.get('eligible_teacher_ids') or variant.get('teacher_not_applicable_reason')):
                missing_teachers.append(d['id'])
                break
    put('teacher', missing_teachers, len(demands))
    put('teacher_availability', [t['id'] for t in data['teachers'] if 'availability' not in t], len(data['teachers']))
    put('participants', [g['id'] for g in data['groups'] if not g.get('membership_complete') and not g.get('conflicts_confirmed')], len(data['groups']))
    put('student_availability', [s['id'] for s in data['students'] if 'availability' not in s], len(data['students']), not data['students'])
    put('classroom', [d['id'] for d in demands if not (d.get('resource_ids') or d.get('eligible_resource_ids') or d.get('resource_not_applicable_reason'))], len(demands))
    put('resource_availability', [r['id'] for r in data['resources'] if 'availability' not in r], len(data['resources']), not data['resources'])
    put('external_occupancy', [] if data.get('external_scope_confirmed') else ['未确认本任务之外的占用范围'], 1)
    campuses = {c['campus_id'] for c in rows}
    missing = [f'{a}->{b}' for a in campuses for b in campuses if a != b and required_travel(data, a, b) is None]
    put('travel', missing, max(1, len(campuses) * (len(campuses) - 1)), len(campuses) <= 1)
    put('calendar', [], len(data['expanded_calendar']))
    return dims


def validate(data, solution):
    errors = []
    def fail(code, message, **context):
        errors.append(dict(code=code, message=message, **context))
    if solution.get('input_hash') != digest(data):
        fail('STALE_INPUT', '方案输入哈希与当前输入不一致')
    if solution.get('rule_hash') != digest(data['rules']):
        fail('STALE_RULES', '方案规则版本不一致')
    if solution.get('calendar_hash') != digest(data['expanded_calendar']):
        fail('STALE_CALENDAR', '方案日历版本不一致')
    assignments = solution.get('assignments', [])
    if solution.get('solution_hash') != digest(assignments):
        fail('STALE_SOLUTION', '课表哈希不匹配')
    expected = {s['id']: s for s in sessions(data)}
    days = {x['date']: x for x in data['expanded_calendar']}
    slots = {s['id']: s for s in data['slots']}
    teacher_ids = {p['id'] for p in data['teachers']}
    resource_ids = {p['id'] for p in data['resources']}
    counts = Counter()
    valid_rows = []
    canceled = set(data.get('canceled_sessions', []))
    for c in assignments:
        sid = c.get('session_id')
        if c.get('status', 'scheduled') not in {'scheduled', 'canceled'}:
            fail('ACTIVITY_STATUS', '未知活动状态，不允许影响公式计数', session_id=sid)
        if c.get('status', 'scheduled') == 'canceled':
            continue
        counts[sid] += 1
        if sid not in expected:
            fail('UNKNOWN_SESSION', '未知教学实例', session_id=sid)
            continue
        required_fields = {'date', 'start', 'end', 'scope', 'demand_id', 'course_id', 'week_type', 'weekday',
                           'group_ids', 'teacher_ids', 'resource_ids', 'slot_id', 'half_day', 'campus_id'}
        if not required_fields <= set(c):
            fail('MALFORMED_ASSIGNMENT', '活动缺少必填字段', session_id=sid, missing=sorted(required_fields-set(c)))
            continue
        s = expected[sid]
        base_d = s['demand']
        override = data.get('session_overrides', {}).get(sid, {})
        allowed_days = {day['date']: day for day in s['days']}
        if override.get('date'):
            allowed_days = {k: v for k, v in days.items() if k == override['date']}
        day = allowed_days.get(c.get('date'))
        if not day:
            fail('CALENDAR', '不在该实例允许日期范围', session_id=sid)
            continue
        d = demand_variant(base_d, day['week_type'])
        if override:
            d = dict(d, **override.get('demand', {}))
        start, end = c.get('start'), c.get('end')
        if type(start) is not int or type(end) is not int or start < 0 or end > 1440 or start >= end:
            fail('TIME', '非法起止时间', session_id=sid)
            continue
        valid_rows.append(c)
        if c.get('scope') != s['scope'] or c.get('demand_id') != s['demand_id'] or c.get('course_id') != d['course_id'] or c.get('week_type') != day['week_type'] or c.get('weekday') != day['weekday']:
            fail('IDENTITY', '活动身份、轮换或作用域不一致', session_id=sid)
        if set(c.get('group_ids', [])) != set(d['group_ids']):
            fail('GROUPS', '教学组与需求不一致', session_id=sid)
        slot = slots.get(c.get('slot_id'))
        if not slot or not window_applies(slot, day) or (slot.get('group_ids') and not set(d['group_ids']) <= set(slot['group_ids'])):
            fail('SLOT', '非法课位或课位不属于教学组', session_id=sid)
        else:
            a, b = minute(slot['start']), minute(slot['end'])
            if not (a <= start < end <= b) or (not slot.get('flexible') and (start != a or end != b)) or (slot.get('flexible') and (start - a) % slot.get('step_minutes', 5)):
                fail('SLOT_TIME', '实际时间不符合课位窗口', session_id=sid)
            if d.get('slot_ids') and slot['id'] not in d['slot_ids']:
                fail('DEMAND_SLOT', '需求不允许该课位', session_id=sid)
            if c.get('half_day') != slot.get('half_day', 'am' if start < 720 else 'pm'):
                fail('HALF_DAY', '半天标签不匹配', session_id=sid)
        if end - start not in d['duration_options']:
            fail('DURATION', '课程时长不符合需求', session_id=sid)
        chosen_t, chosen_r = c.get('teacher_ids', []), c.get('resource_ids', [])
        for chosen, required, eligible, registry, label in [
            (chosen_t, d.get('teacher_ids', []), d.get('eligible_teacher_ids', []), teacher_ids, 'TEACHER'),
            (chosen_r, d.get('resource_ids', []), d.get('eligible_resource_ids', []), resource_ids, 'RESOURCE')]:
            valid = set(chosen) <= registry and set(required) <= set(chosen) and len(chosen) == len(set(chosen))
            if eligible:
                valid = valid and any(set(chosen) == set(required) | {x} for x in eligible)
            else:
                valid = valid and set(chosen) == set(required)
            if not valid:
                fail(label + '_ASSIGNMENT', '未授权的人员或场地分配', session_id=sid)
        for name, ids in [('teachers', chosen_t), ('students', participants(data, c['group_ids'], c['date'])), ('groups', c['group_ids'])]:
            for person in data[name]:
                if person['id'] in ids and not available(person, c, day):
                    fail('AVAILABILITY', '参与者不在可用窗口', session_id=sid, person_id=person['id'])
                if name == 'teachers' and person['id'] in ids and d.get('required_qualification') and d['required_qualification'] not in person.get('qualifications', []):
                    fail('QUALIFICATION', '教师资格不符合需求', session_id=sid)
        if not available(d, c, day):
            fail('DEMAND_AVAILABILITY', '需求禁排或可用窗口冲突', session_id=sid)
        if c['date'] in d.get('exclude_dates', []):
            fail('EXCLUDED_DATE', '活动落入需求明确排除的日期', session_id=sid)
        for spec in d.get('fixed', []):
            if spec.get('session_index', 1) == s['index'] and spec.get('scope', s['scope']) == s['scope'] and not fits_spec(c, spec) and not override.get('replace_fixed'):
                fail('FIXED', '违反固定课位', session_id=sid)
        for lock in data.get('locks', []):
            if lock['session_id'] == sid and not fits_spec(c, lock):
                fail('LOCK', '违反锁定维度', session_id=sid)
        members = participants(data, c['group_ids'], c['date'])
        headcount = len(members) if members else sum(g.get('size', 0) for g in data['groups'] if g['id'] in c['group_ids'])
        campuses = set()
        for r in data['resources']:
            if r['id'] not in chosen_r:
                continue
            campuses.add(r.get('campus_id', 'default'))
            ext = dict(c, start=start-r.get('setup_minutes', 0), end=end+r.get('cleanup_minutes', 0))
            if ext['start'] < 0 or ext['end'] > 1440 or not available(r, ext, day):
                fail('RESOURCE_WINDOW', '场地准备、清场或可用性冲突', session_id=sid)
            if r.get('seats') is not None and headcount > r['seats']:
                fail('SEATS', '场地人数容量不足', session_id=sid)
            if not set(d.get('required_features', [])) <= set(r.get('features', [])):
                fail('FEATURES', '场地功能不适配', session_id=sid)
        correct_campus = next(iter(campuses), d.get('campus_id', 'default'))
        if len(campuses) > 1 or c.get('campus_id') != correct_campus:
            fail('CAMPUS', '场地与校区不一致', session_id=sid)
    for sid in expected:
        desired = 0 if sid in canceled else 1
        if counts[sid] != desired:
            fail('SESSION_COUNT', '实例缺失、重复或已取消仍计入', session_id=sid, expected=desired, actual=counts[sid])
    quota = []
    grouped = defaultdict(list)
    for c in valid_rows:
        grouped[c['demand_id'], c['scope']].append(c)
    for s in expected.values():
        if s['index'] != 1:
            continue
        d = s['demand']
        count = sum(1 for x in expected.values() if x['demand_id'] == d['id'] and x['scope'] == s['scope'] and x['id'] not in canceled)
        rows = grouped[d['id'], s['scope']]
        target_minutes = s['target_minutes']
        if target_minutes is not None:
            target_minutes -= sum(data.get('canceled_minutes', {}).get(x['id'], x['demand']['duration_options'][0]) for x in expected.values() if x['id'] in canceled and x['demand_id'] == d['id'] and x['scope'] == s['scope'])
        actual = sum(c['end']-c['start'] for c in rows)
        item = {'demand_id': d['id'], 'scope': s['scope'], 'unit': d['quota']['unit'], 'expected_sessions': count,
                'actual_sessions': len(rows), 'session_delta': len(rows)-count,
                'expected_minutes': target_minutes, 'actual_minutes': actual,
                'minute_delta': actual-target_minutes if target_minutes is not None else None}
        quota.append(item)
        if item['session_delta'] or item['minute_delta'] not in (None, 0):
            fail('QUOTA', '课时配额不一致', **item)
    # Independent overlap and travel sweep; no solver variables or candidate-generation result used.
    for a, b in combinations(valid_rows, 2):
        if a['date'] != b['date']:
            continue
        ap = set(a['teacher_ids']) | participants(data, a['group_ids'], a['date'])
        bp = set(b['teacher_ids']) | participants(data, b['group_ids'], b['date'])
        if not (ap & bp or groups_conflict(data, a['group_ids'], b['group_ids'], a['date'])):
            continue
        first, second = sorted([a, b], key=lambda x: x['start'])
        if second['start'] < first['end']:
            fail('PERSON_CONFLICT', '教师、学生或互斥组时间重叠', sessions=[a['session_id'], b['session_id']], date=a['date'])
        else:
            travel = required_travel(data, first['campus_id'], second['campus_id'])
            rest = max([p.get('rest_minutes', 0) for k in ['teachers', 'students'] for p in data[k] if p['id'] in ap & bp] or [0])
            if travel is None or second['start']-first['end'] < max(travel, rest):
                fail('TRAVEL_REST', '转场或休息时间不足/缺失', sessions=[a['session_id'], b['session_id']])
    for c in valid_rows:
        persons = set(c['teacher_ids']) | participants(data, c['group_ids'], c['date'])
        for ext in data.get('external_occupancy', []):
            if ext['date'] != c['date'] or not (persons & set(ext.get('person_ids', [])) or groups_conflict(data, c['group_ids'], ext.get('group_ids', []), c['date'])):
                continue
            start, end = minute(ext['start']), minute(ext['end'])
            if c['start'] < end and start < c['end']:
                fail('EXTERNAL_CONFLICT', '与外部占用冲突', session_id=c['session_id'], source=ext.get('source'))
            else:
                before = end <= c['start']
                travel = required_travel(data, ext.get('campus_id', 'default') if before else c['campus_id'], c['campus_id'] if before else ext.get('campus_id', 'default'))
                gap = c['start']-end if before else start-c['end']
                shared = persons & set(ext.get('person_ids', []))
                rest = max([p.get('rest_minutes', 0) for k in ['teachers', 'students'] for p in data[k] if p['id'] in shared] or [0])
                if travel is None or gap < max(travel, rest):
                    fail('EXTERNAL_TRAVEL', '与外部占用的转场时间不足', session_id=c['session_id'])
    for r in data['resources']:
        events = defaultdict(list)
        for c in valid_rows:
            if r['id'] in c['resource_ids']:
                d = expected[c['session_id']]['demand']
                use = d.get('resource_usage', {}).get(r['id'], 1)
                events[c['date']].extend([(c['start']-r.get('setup_minutes', 0), use), (c['end']+r.get('cleanup_minutes', 0), -use)])
        for ext in data.get('external_occupancy', []):
            if r['id'] in ext.get('resource_ids', []):
                use = ext.get('resource_usage', {}).get(r['id'], 1)
                events[ext['date']].extend([(minute(ext['start']), use), (minute(ext['end']), -use)])
        for day, points in events.items():
            occupied = 0
            for t, delta in sorted(points):
                occupied += delta
                if occupied > r.get('capacity', 1):
                    fail('RESOURCE_CAPACITY', '资源并发容量超限', resource_id=r['id'], date=day, minute=t)
    for name in ['teachers', 'students', 'groups']:
        for person in data[name]:
            totals = defaultdict(lambda: [0, 0])
            for day in data['expanded_calendar']:
                totals[day['date']]
            for c in valid_rows:
                ids = c['teacher_ids'] if name == 'teachers' else c['group_ids'] if name == 'groups' else participants(data, c['group_ids'], c['date'])
                if person['id'] in ids:
                    totals[c['date']][0] += 1
                    totals[c['date']][1] += c['end']-c['start']
            for day, (count, mins) in totals.items():
                external = [e for e in data.get('external_occupancy', []) if e['date'] == day and person['id'] in e.get('group_ids' if name == 'groups' else 'person_ids', [])]
                count += len(external)
                mins += sum(minute(e['end'])-minute(e['start']) for e in external)
                if count > person.get('daily_sessions', 1000000) or mins > person.get('daily_minutes', 1000000):
                    fail('WORKLOAD', '人员或组每日负荷超限', person_id=person['id'], date=day)
    if data['fill_policy'] == 'full':
        for g in data['groups']:
            for day in data['expanded_calendar']:
                for slot in data['slots']:
                    if not slot.get('required', True) or slot.get('flexible') or not window_applies(slot, day) or (slot.get('group_ids') and g['id'] not in slot['group_ids']):
                        continue
                    n = sum(c['date'] == day['date'] and g['id'] in c['group_ids'] and c['start'] <= minute(slot['start']) and minute(slot['end']) <= c['end'] for c in valid_rows)
                    if n != 1:
                        fail('FILL', '必排课位未被唯一填充', group_id=g['id'], date=day['date'], slot_id=slot['id'])
    rule_results = evaluate_rules(data, valid_rows)
    for r in rule_results:
        if r.get('enabled') and r['level'] == 'hard' and r['penalty']:
            fail('HARD_RULE', '违反启用硬规则', rule_id=r['rule_id'], penalty=r['penalty'], details=r['details'])
    cov = coverage(data, valid_rows)
    complete = all(v['status'] in {'complete', 'not_applicable'} for v in cov.values())
    pending = bool(canceled)
    from quality import assess_quality
    quality = assess_quality(data, valid_rows)
    ready = not errors and complete and not pending and quality['gate_passed']
    draft_reason = ('硬约束失败' if errors else '教学质量未通过' if not quality['gate_passed'] else
                    '待补课' if pending else '资料待补全' if not complete else None)
    return {'valid': not errors, 'ready_for_acceptance': ready,
            'quality': quality, 'draft_reason': draft_reason,
            'delivery_status': '验收通过' if ready else '草稿' if errors or pending or not quality['gate_passed'] else '有限范围通过',
            'pending_makeup_sessions': sorted(canceled), 'coverage': cov,
            'teacher_coverage': cov['teacher'], 'classroom_coverage': cov['classroom'],
            'hard_violations': errors, 'soft_violations': [r for r in rule_results if r.get('enabled') and r['level'] == 'soft' and r['penalty']],
            'rule_results': rule_results, 'quota_deltas': quota, 'input_hash': digest(data),
            'rule_hash': digest(data['rules']), 'calendar_hash': digest(data['expanded_calendar']),
            'solution_hash': digest(assignments), 'checked_week_types': sorted({d['week_type'] for d in data['expanded_calendar']}),
            'checked_dates': sorted(days), 'calendar_scope': '周模板示意日期' if data['mode'] == 'weekly_template' else '实际日期范围',
            'generated_at': stamp()}
