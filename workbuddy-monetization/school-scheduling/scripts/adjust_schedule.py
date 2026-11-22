import copy
from common import InputError, digest, stamp
from model_data import build_candidates, fits_spec
from normalize_input import normalize
from validate_schedule import validate
from cp_sat_scheduler import solve


def adjust(data, solution, changes):
    if changes.get('baseline_solution_hash') != solution.get('solution_hash'):
        raise InputError('调整必须指定当前 baseline_solution_hash，拒绝过期基线', 'changes.baseline_solution_hash')
    if changes.get('baseline_version') != solution.get('version_hash') or not solution.get('version_hash'):
        raise InputError('调整必须指定当前 baseline_version；内容相同的不同版本也不能混用', 'changes.baseline_version')
    report = validate(data, solution)
    if not report['valid']:
        raise InputError('基线方案未通过校验，先修复输入或重新排课')
    effective = copy.deepcopy(data)
    rows = {c['session_id']: copy.deepcopy(c) for c in solution['assignments'] if c.get('status') != 'canceled'}
    history = copy.deepcopy(solution.get('canceled_history', []))
    constraints = {}
    replan = False
    for change in changes['operations']:
        action = change['action']
        if action == 'swap':
            a, b = change['session_ids']
            if a not in rows or b not in rows:
                raise InputError('交换实例不存在')
            for source, target in [(a, b), (b, a)]:
                constraints[source] = {k: rows[target][k] for k in ['date', 'slot_id', 'start']}
        elif action in {'move', 'makeup'}:
            sid = change['session_id']
            if sid not in rows and sid not in effective.get('canceled_sessions', []):
                raise InputError('待调整实例不存在')
            spec = {k: v for k, v in change.items() if k in {'date', 'slot_id', 'start', 'teacher_ids', 'resource_ids'}}
            constraints[sid] = spec
            if action == 'makeup' or change.get('replace_fixed') or change.get('replace_calendar'):
                if 'date' not in spec:
                    raise InputError('改期或补课必须给定具体date')
                effective.setdefault('session_overrides', {})[sid] = {'date': spec['date'], 'replace_fixed': True}
            if action == 'makeup':
                if sid not in effective.get('canceled_sessions', []):
                    raise InputError('补课必须关联已取消且尚未补回的实例')
                effective['canceled_sessions'].remove(sid)
                effective.setdefault('canceled_minutes', {}).pop(sid, None)
        elif action == 'cancel':
            sid = change['session_id']
            if sid not in rows:
                raise InputError('待取消实例不存在')
            effective.setdefault('canceled_sessions', []).append(sid)
            effective.setdefault('canceled_minutes', {})[sid] = rows[sid]['end'] - rows[sid]['start']
            history.append(dict(rows.pop(sid), status='canceled', reason=change.get('reason', '')))
            constraints.pop(sid, None)
        elif action == 'lock':
            sid = change['session_id']
            if sid not in rows:
                raise InputError('锁定实例不存在')
            spec = {k: rows[sid][k] for k in change.get('fields', ['date', 'slot_id', 'start', 'teacher_ids', 'resource_ids'])}
            effective['locks'] = [x for x in effective.get('locks', []) if x['session_id'] != sid] + [dict(spec, session_id=sid)]
        elif action == 'replan':
            replan = True
        else:
            raise InputError(f'不支持调整动作 {action}')
    effective = normalize(effective)
    candidates, empty = build_candidates(effective)
    for sid, spec in constraints.items():
        options = next((opts for s, opts in candidates if s['id'] == sid), [])
        old = rows.get(sid)
        eligible = [c for c in options if fits_spec(c, spec)]
        if not eligible:
            raise InputError(f'{sid} 调整位置不满足时间、资格、固定或可用性限制')
        eligible.sort(key=lambda c: sum(c[k] != old[k] for k in ['teacher_ids', 'resource_ids']) if old else 0)
        rows[sid] = eligible[0]
    if replan:
        effective['baseline_assignments'] = list(rows.values())
        for sid, spec in constraints.items():
            effective.setdefault('locks', []).append(dict(spec, session_id=sid))
        result = solve(effective, changes.get('time_limit', 120))
    else:
        result = dict(solution, input_hash=digest(effective), rule_hash=digest(effective['rules']),
                      calendar_hash=digest(effective['expanded_calendar']), status='MANUAL',
                      assignments=sorted(rows.values(), key=lambda c: (c['date'], c['start'], c['session_id'])),
                      layers=[], generated_at=stamp())
        result['solution_hash'] = digest(result['assignments'])
    result['parent_solution_hash'] = solution['solution_hash']
    result['revision'] = solution.get('revision', 1) + 1
    result['version_hash'] = digest({'input': digest(effective), 'solution_hash': result['solution_hash'],
                                   'revision': result['revision'], 'parent': solution['version_hash']})
    result['canceled_history'] = history
    result['changes'] = changes
    result['validation'] = validate(effective, result)
    result['delivery_status'] = result['validation']['delivery_status']
    return effective, result
