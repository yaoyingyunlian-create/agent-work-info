from collections import defaultdict
from common import InputError

DEFAULT_RULES = [
    {'id': 'quality-daily-limit', 'type': 'daily_limit', 'max': 2, 'level': 'hard'},
    {'id': 'quality-half-day', 'type': 'same_half_day', 'level': 'hard'},
    {'id': 'quality-consecutive', 'type': 'consecutive', 'max_break_minutes': 15, 'level': 'hard'}]


def apply_policy(data):
    policy = data.setdefault('quality_policy', 'senior-standard' if data['profile'] == 'senior' else 'custom')
    if policy not in {'senior-standard', 'custom'}:
        raise InputError('quality_policy必须为senior-standard/custom')
    if data['profile'] == 'senior' and policy == 'custom' and not data.get('quality_policy_reason'):
        raise InputError('高中关闭标准质量策略必须填写quality_policy_reason')
    if policy != 'senior-standard':
        return
    for default in DEFAULT_RULES:
        same_id = next((r for r in data['rules'] if r['id'] == default['id']), None)
        if same_id is not None and any(same_id.get(k) != v for k, v in default.items()):
            raise InputError('不得用同名规则覆盖标准质量策略；特殊场景请显式选择custom并说明原因')
        equivalent = any(r.get('enabled', True) and r.get('level', 'hard') == 'hard' and
                         r.get('by', 'demand') == 'demand' and
                         not any(k in r for k in ['teacher_ids', 'group_ids', 'course_ids', 'demand_ids']) and
                         all(r.get(k) == v for k, v in default.items() if k not in {'id', 'level'})
                         for r in data['rules'])
        if not equivalent:
            if same_id:
                raise InputError('标准质量规则不能被关闭')
            data['rules'].append(dict(default))


def assess_quality(data, rows):
    buckets, courses = defaultdict(list), defaultdict(set)
    for row in rows:
        for gid in set(row['group_ids']):
            buckets[gid, row['course_id'], row['date']].append(row)
            courses[gid, row['course_id']].add(row['date'])
    issues = []
    counts = {'daily_over_limit': 0, 'split_half_day': 0, 'nonconsecutive': 0}
    for (gid, course, day), items in buckets.items():
        ordered = sorted(items, key=lambda a: a['start'])
        violations = []
        if len(items) > 2:
            counts['daily_over_limit'] += 1
            violations.append('daily_over_limit')
        if len({a['half_day'] for a in items}) > 1:
            counts['split_half_day'] += 1
            violations.append('split_half_day')
        if any(b['start'] - a['end'] > 15 for a, b in zip(ordered, ordered[1:])):
            counts['nonconsecutive'] += 1
            violations.append('nonconsecutive')
        if violations:
            issues.append({'group_id': gid, 'course_id': course, 'date': day, 'types': violations,
                           'sessions': [a['session_id'] for a in ordered]})
    enforced = data['quality_policy'] == 'senior-standard'
    return {'policy': data['quality_policy'], 'enforced': enforced,
            'gate_passed': not issues if enforced else True,
            'metric_scope': '按教学组、实际课程、日期统计；即使课程分拆为多个需求也合并检查',
            'counts': counts, 'issues': issues,
            'distribution': [{'group_id': g, 'course_id': c, 'days': len(ds)} for (g, c), ds in courses.items()]}
