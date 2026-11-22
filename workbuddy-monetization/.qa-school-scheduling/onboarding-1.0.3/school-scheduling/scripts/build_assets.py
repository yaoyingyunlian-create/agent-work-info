"""Rebuild distributable, anonymous examples and editable templates."""
from copy import deepcopy
from common import ROOT, write_json


def base(profile, mode='weekly_template'):
    window = [{'start': '07:00', 'end': '23:00'}]
    return {'schema_version': '1.0', 'task_id': profile + '-demo', 'profile': profile,
            'mode': mode, 'timezone': 'Asia/Shanghai', 'fill_policy': 'demand_only',
            'external_scope_confirmed': True, 'external_scope_note': '仅本示例任务，已确认无其他占用',
            'calendar': {'weekdays': [0, 1, 2, 3, 4], 'week_types': ['all']},
            'groups': [{'id': 'G1', 'name': '示例一组', 'size': 20, 'conflicts_confirmed': True},
                       {'id': 'G2', 'name': '示例二组', 'size': 20, 'conflicts_confirmed': True}],
            'teachers': [{'id': f'T{i}', 'name': f'示例教师{i}', 'availability': deepcopy(window),
                          'qualifications': ['general']} for i in [1, 2]],
            'students': [], 'resources': [{'id': 'R1', 'name': '示例教室', 'capacity': 1, 'seats': 40,
                                         'availability': deepcopy(window), 'campus_id': 'A'}],
            'slots': [{'id': f'P{i+1}', 'start': start, 'end': end, 'half_day': half}
                      for i, (start, end, half) in enumerate([('08:00', '08:40', 'am'), ('08:50', '09:30', 'am'),
                                                             ('10:00', '10:40', 'am'), ('14:00', '14:40', 'pm')])],
            'demands': [], 'rules': [], 'external_occupancy': [], 'locks': []}


def demand(identity, group, teacher, course='数学', count=2, duration=40):
    return {'id': identity, 'course_id': course, 'group_ids': [group], 'teacher_ids': [teacher],
            'resource_ids': ['R1'], 'duration_options': [duration],
            'quota': {'unit': 'sessions', 'value': count, 'scope': 'week'}}


def examples():
    primary = base('primary')
    primary['demands'] = [demand('D1', 'G1', 'T1', count=3), demand('D2', 'G2', 'T1', '语文', 2),
                          demand('D3', 'G1', 'T2', '课后活动', 1)]
    primary['slots'][0]['group_ids'] = ['G1']
    primary['slots'].append({'id': 'G2-P1', 'start': '08:20', 'end': '09:00', 'half_day': 'am', 'group_ids': ['G2']})
    primary['rules'] = [{'id': '分布', 'type': 'daily_distribution', 'level': 'soft', 'demand_ids': ['D1'], 'target': 3, 'tier': 2}]
    junior = base('junior')
    junior['calendar']['week_types'] = ['odd', 'even']
    junior['slots'].append({'id': 'LAB', 'start': '15:00', 'end': '16:20', 'half_day': 'pm'})
    junior['resources'][0]['features'] = ['lab']
    lab = demand('LAB1', 'G1', 'T1', '实验', 1, 80)
    lab['required_features'] = ['lab']
    lab['rotation'] = {'odd': {'teacher_ids': ['T1'], 'course_id': '物理实验'},
                       'even': {'teacher_ids': ['T2'], 'course_id': '化学实验'}}
    junior['demands'] = [lab, demand('D2', 'G2', 'T2', '数学', 2)]
    junior['rules'] = [{'id': '轮换同位', 'type': 'synchronize', 'demand_ids': ['LAB1'], 'across_weeks': True, 'level': 'hard'}]
    senior = base('senior')
    senior['students'] = [{'id': f'S{i}', 'name': f'匿名学生{i}', 'availability': [{'start': '07:00', 'end': '23:00'}]} for i in [1, 2, 3]]
    senior['groups'] = [{'id': 'G1', 'name': '选科组甲', 'student_ids': ['S1', 'S2'], 'membership_complete': True},
                        {'id': 'G2', 'name': '选科组乙', 'student_ids': ['S2', 'S3'], 'membership_complete': True},
                        {'id': 'G3', 'name': '拆班子组', 'student_ids': ['S3'], 'membership_complete': True}]
    senior['resources'][0]['capacity'] = 2
    senior['rules'] = [
        {'id': '同科每日上限', 'type': 'daily_limit', 'max': 2, 'level': 'hard'},
        {'id': '同科同日同半天', 'type': 'same_half_day', 'level': 'hard'},
        {'id': '同科同日连堂', 'type': 'consecutive', 'max_break_minutes': 15, 'level': 'hard'}]
    senior['demands'] = [demand('D1', 'G1', 'T1', '选修物理', 2), demand('D2', 'G2', 'T2', '选修化学', 2),
                         dict(demand('D3', 'G1', 'T1', '合班活动', 1), group_ids=['G1', 'G3'])]
    training = base('training', 'date_range')
    training['calendar'] = {'start_date': '2026-11-07', 'end_date': '2026-11-15', 'week_anchor': '2026-11-02',
                            'weekdays': [5, 6], 'week_types': ['all']}
    training['slots'] = [{'id': '周末上午', 'weekdays': [5, 6], 'start': '09:00', 'end': '12:00', 'flexible': True, 'step_minutes': 30, 'half_day': 'am'},
                         {'id': '周末晚间', 'weekdays': [5, 6], 'start': '18:00', 'end': '21:00', 'flexible': True, 'step_minutes': 30, 'half_day': 'pm'}]
    training['resources'].append(dict(deepcopy(training['resources'][0]), id='R2', campus_id='B'))
    training['travel_minutes'] = {'A': {'B': 30}, 'B': {'A': 30}}
    training['groups'][0]['size'] = 1
    training['groups'][1]['size'] = 6
    training['demands'] = [dict(demand('PACK', 'G1', 'T1', '一对一课程包', 3, 60),
                                duration_options=[60, 90], session_count=3,
                                quota={'unit': 'units', 'value': 4, 'minutes_per_unit': 60, 'scope': 'range'},
                                teacher_ids=[], eligible_teacher_ids=['T1', 'T2'], resource_ids=[], eligible_resource_ids=['R1', 'R2']),
                           dict(demand('SMALL', 'G2', 'T1', '小班课程', 2, 45),
                                quota={'unit': 'sessions', 'value': 2, 'scope': 'range'})]
    training['rules'] = [{'id': '连续到场', 'type': 'minimize_gaps', 'by': 'teacher', 'level': 'soft', 'tier': 2}]
    return {'primary': primary, 'junior': junior, 'senior': senior, 'training': training}


def grade22():
    # Anonymous capacity fixture, NOT a reconstruction of the real school or its teacher map.
    d = base('senior')
    d['task_id'] = 'senior-22classes-synthetic'
    d['benchmark_note'] = '22班990活动合成容量测试；不代表真实教师映射和学校规则通过'
    d['quality_policy'] = 'custom'
    d['quality_policy_reason'] = '固定时间容量基准，非教学质量样例'
    d['groups'] = [{'id': f'C{i}', 'name': f'合成{i}班', 'size': 40, 'conflicts_confirmed': True} for i in range(1, 23)]
    d['teachers'] = [{'id': f'T{i}', 'name': f'合成教师{i}', 'availability': [{'start': '07:00', 'end': '20:00'}]} for i in range(1, 89)]
    d['resources'] = [{'id': f'R{i}', 'capacity': 1, 'seats': 40, 'campus_id': 'A', 'availability': [{'start': '07:00', 'end': '20:00'}]} for i in range(1, 23)]
    times = [('08:00', '08:40'), ('08:50', '09:30'), ('09:40', '10:20'), ('10:40', '11:20'), ('11:30', '12:10'),
             ('14:00', '14:40'), ('14:50', '15:30'), ('15:40', '16:20'), ('16:30', '17:10')]
    d['slots'] = [{'id': f'P{i+1}', 'start': a, 'end': b, 'half_day': 'am' if i < 5 else 'pm'} for i, (a, b) in enumerate(times)]
    quotas = [('语文', 6), ('数学', 7), ('英语', 6), ('物理', 5), ('化学', 4), ('生物', 3), ('历史', 2), ('政治', 2), ('地理', 2),
              ('体育', 2), ('信息心理', 1), ('写书', 1), ('艺术', 1), ('劳动', 1), ('班团', 1), ('研修', 1)]
    d['demands'] = []
    for g in range(1, 23):
        offset = 0
        for k, (course, n) in enumerate(quotas):
            obj = demand(f'C{g}-K{k}', f'C{g}', f'T{(g-1 + (k % 4)*22)%88+1}', course, n)
            obj['resource_ids'] = [f'R{g}']
            # Fixed full-week activity positions bound a reproducible capacity smoke test.
            obj['fixed'] = [{'session_index': j+1, 'weekday': (offset+j)//9, 'slot_id': f'P{(offset+j)%9+1}'} for j in range(n)]
            d['demands'].append(obj)
            offset += n
    d['fill_policy'] = 'full'
    return d


def main():
    from excel_io import template
    for name, data in examples().items():
        write_json(ROOT / 'assets' / 'profiles' / (name + '.json'), data)
        template(data, ROOT / 'assets' / 'templates' / (name + '.xlsx'))
    write_json(ROOT / 'assets' / 'profiles' / 'senior-22classes-synthetic.json', grade22())


if __name__ == '__main__':
    main()
