from __future__ import annotations

import copy
from common import InputError, entries, integer, minute, is_date
from expand_calendar import expand_calendar

RULE_TYPES = {'daily_limit', 'consecutive', 'same_half_day', 'synchronize', 'min_gap',
              'precedence', 'daily_distribution', 'workdays', 'ampm_balance',
              'no_all_bad', 'tail_excess', 'preferred_time', 'minimize_gaps'}


def normalize(data):
    data = copy.deepcopy(data)
    if data.get('schema_version') != '1.0':
        raise InputError('schema_version 必须为 1.0，不支持的版本不可隐式读取', 'schema_version')
    if data.get('profile') not in {'primary', 'junior', 'senior', 'training'}:
        raise InputError('profile 必须为 primary/junior/senior/training', 'profile')
    if data.get('mode') not in {'weekly_template', 'date_range'}:
        raise InputError('mode 必须为 weekly_template/date_range', 'mode')
    data.setdefault('task_id', 'schedule')
    data.setdefault('timezone', 'Asia/Shanghai')
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        ZoneInfo(data['timezone'])
    except ZoneInfoNotFoundError:
        raise InputError('未知时区，Windows请安装锁定依赖中的tzdata', 'timezone')
    for collection, key in [('groups', 'id'), ('teachers', 'id'), ('students', 'id'),
                            ('resources', 'id'), ('demands', 'id'), ('rules', 'id')]:
        data.setdefault(collection, [])
        entries(data[collection], key)
    if not data['demands'] or not data['groups']:
        raise InputError('至少提供一个教学需求及教学组')
    groups, teachers, students, resources = (entries(data[k], 'id') for k in
                                            ['groups', 'teachers', 'students', 'resources'])
    people = set(teachers) & set(students)
    for pid in people:
        if teachers[pid].get('name') != students[pid].get('name'):
            raise InputError('跨角色相同ID的姓名不一致')
    for group in groups.values():
        for sid in group.get('student_ids', []):
            if sid not in students:
                raise InputError(f'组 {group["id"]} 引用了未知学生 {sid}')
        for gid in group.get('exclusive_with', []):
            if gid not in groups:
                raise InputError(f'未知互斥组 {gid}')
        for m in group.get('memberships', []):
            if m.get('student_id') not in students:
                raise InputError('成员生效表引用未知学生')
            for k in ['from', 'to']:
                if k in m:
                    is_date(m[k])
            if m.get('from', '0001-01-01') > m.get('to', '9999-12-31'):
                raise InputError('成员生效日期倒置')
    slots = data.get('slots', [])
    entries(slots, 'id')
    for i, slot in enumerate(slots):
        if minute(slot['end']) <= minute(slot['start']):
            raise InputError('不支持跨午夜或非正时长', f'slots[{i}]')
        for gid in slot.get('group_ids', []):
            if gid not in groups:
                raise InputError(f'课位引用未知组 {gid}')
    for i, d in enumerate(data['demands']):
        path = f'demands[{i}]'
        if not d.get('group_ids') or not d.get('course_id'):
            raise InputError('需求必须有课程ID和教学组', path)
        for field, registry in [('group_ids', groups), ('teacher_ids', teachers),
                                ('eligible_teacher_ids', teachers), ('resource_ids', resources),
                                ('eligible_resource_ids', resources)]:
            if len(set(d.get(field, []))) != len(d.get(field, [])):
                raise InputError(f'{field} 包含重复ID', path)
            for identity in d.get(field, []):
                if identity not in registry:
                    raise InputError(f'未知引用 {identity}', f'{path}.{field}')
        for wt, override in d.get('rotation', {}).items():
            if wt not in data['calendar'].get('week_types', ['all']):
                raise InputError(f'未知轮换周型 {wt}', path)
            for tid in override.get('teacher_ids', []):
                if tid not in teachers:
                    raise InputError(f'轮换教师不存在 {tid}', path)
            if set(override) - {'teacher_ids', 'course_id'}:
                raise InputError('首版轮换仅改变课程名称和必需教师，课长与配额保持一致', path)
        durations = d.setdefault('duration_options', [d.get('duration_minutes', 40)])
        if not durations:
            raise InputError('duration_options 不能为空', path)
        for n in durations:
            integer(n, path + '.duration_options', 1)
        quota = d.setdefault('quota', {'unit': 'sessions', 'value': d.get('weekly_periods', 1), 'scope': 'week'})
        integer(quota.get('value'), path + '.quota.value', 1)
        if quota.get('scope', 'week') not in {'week', 'range', 'week_type'}:
            raise InputError('配额范围必须为week/range/week_type', path)
        if quota['unit'] not in {'sessions', 'minutes', 'units'}:
            raise InputError('配额单位必须为sessions/minutes/units', path)
        if quota['unit'] == 'units':
            integer(quota.get('minutes_per_unit'), path + '.quota.minutes_per_unit', 1)
        if quota['unit'] != 'sessions' and len(durations) > 1:
            integer(d.get('session_count'), path + '.session_count', 1)
        for fixed in d.get('fixed', []):
            if 'start' in fixed:
                minute(fixed['start'])
        for sid in d.get('slot_ids', []):
            if sid not in {s['id'] for s in slots}:
                raise InputError(f'未知课位 {sid}', path)
    ids = {d['id'] for d in data['demands']}
    from quality import apply_policy
    apply_policy(data)
    for i, rule in enumerate(data['rules']):
        if not rule.get('enabled', True):
            continue
        if rule.get('type') not in RULE_TYPES:
            raise InputError(f'启用规则尚未实现: {rule.get("type")}', f'rules[{i}]', 'UNSUPPORTED_RULE')
        if rule.get('level', 'hard') not in {'hard', 'soft'}:
            raise InputError('规则级别必须为hard/soft', f'rules[{i}]')
        integer(rule.get('tier', 2), f'rules[{i}].tier')
        integer(rule.get('weight', 1), f'rules[{i}].weight', 1)
        for did in rule.get('demand_ids', []):
            if did not in ids:
                raise InputError(f'规则引用未知需求 {did}', f'rules[{i}]')
        for tid in rule.get('teacher_ids', []):
            if tid not in teachers:
                raise InputError(f'规则引用未知教师 {tid}', f'rules[{i}]')
        required = {'daily_limit': ['max'], 'min_gap': ['minutes'], 'workdays': ['target'],
                    'daily_distribution': ['target'], 'preferred_time': ['windows'],
                    'synchronize': ['demand_ids'], 'precedence': ['demand_ids']}.get(rule['type'], [])
        if any(k not in rule for k in required):
            raise InputError(f'规则缺少参数 {required}', f'rules[{i}]')
        if rule['type'] == 'precedence' and len(rule['demand_ids']) != 2:
            raise InputError('precedence必须依次给出两个需求ID', f'rules[{i}]')
        if rule.get('by', 'demand') not in {'demand', 'teacher', 'group'}:
            raise InputError('by必须为demand/teacher/group', f'rules[{i}]')
        if 'unit' in rule and rule['unit'] not in {'minutes', 'sessions'}:
            raise InputError('规则unit必须为minutes/sessions', f'rules[{i}]')
        supported_fields = {'id', 'type', 'enabled', 'level', 'tier', 'weight', 'source', 'note', 'by',
                            'demand_ids', 'teacher_ids', 'group_ids', 'course_ids', 'unit', 'max',
                            'minutes', 'target', 'max_break_minutes', 'windows', 'slot_ids', 'across_weeks'}
        if set(rule) - supported_fields:
            raise InputError(f'规则含未支持参数 {sorted(set(rule)-supported_fields)}', f'rules[{i}]', 'UNSUPPORTED_RULE')
        for k in ['max', 'minutes', 'target', 'max_break_minutes']:
            if k in rule:
                integer(rule[k], f'rules[{i}].{k}')
        for gid in rule.get('group_ids', []):
            if gid not in groups:
                raise InputError(f'规则引用未知组 {gid}', f'rules[{i}]')
    for res in resources.values():
        integer(res.get('capacity', 1), 'resources.capacity', 1)
        integer(res.get('setup_minutes', 0), 'resources.setup_minutes')
        integer(res.get('cleanup_minutes', 0), 'resources.cleanup_minutes')
        if 'seats' in res:
            integer(res['seats'], 'resources.seats', 1)
    for obj in data['teachers'] + data['students'] + data['groups']:
        for key in ['rest_minutes', 'daily_sessions', 'daily_minutes', 'size']:
            if key in obj:
                integer(obj[key], key)
    for source, targets in data.get('travel_minutes', {}).items():
        for target, value in targets.items():
            integer(value, f'travel_minutes.{source}.{target}')
    for d in data['demands']:
        for key, value in d.get('resource_usage', {}).items():
            if key not in resources:
                raise InputError(f'未知资源用量引用 {key}')
            integer(value, f'{d["id"]}.resource_usage', 1)
    for o in data.get('external_occupancy', []):
        is_date(o['date'])
        if minute(o['end']) <= minute(o['start']):
            raise InputError('外部占用时间无效')
        for key in ['person_ids', 'resource_ids', 'group_ids']:
            registry = set(teachers) | set(students) if key == 'person_ids' else set(resources) if key == 'resource_ids' else set(groups)
            if not set(o.get(key, [])) <= registry:
                raise InputError(f'外部占用引用未知对象: {key}')
    # Validate every window before search, including windows never reached by candidates.
    for obj in data['teachers'] + data['students'] + data['groups'] + data['resources'] + data['demands'] + data['rules']:
        for field in ['availability', 'unavailability', 'windows']:
            for w in obj.get(field, []):
                if minute(w['start']) >= minute(w['end']):
                    raise InputError('可用/禁排窗口结束时间必须晚于开始时间')
                if any(type(x) is not int or x not in range(7) for x in w.get('weekdays', [])):
                    raise InputError('窗口星期必须为0至6')
                for value in w.get('dates', []):
                    is_date(value)
    data['expanded_calendar'] = expand_calendar(data)
    data.setdefault('fill_policy', 'demand_only')
    if data['fill_policy'] not in {'full', 'demand_only'}:
        raise InputError('fill_policy 必须为full/demand_only')
    if data['fill_policy'] == 'full' and any(len(d['duration_options']) != 1 for d in data['demands']):
        raise InputError('满排模式必须使用明确的学校课位和固定课长')
    return data
