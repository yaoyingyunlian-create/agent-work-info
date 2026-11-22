"""Build a short, context-aware intake. No global user tracking or interactive stdin."""
from common import InputError

PROFILES = {'primary': '小学', 'junior': '初中', 'senior': '高中', 'training': '培训机构'}
GOALS = {'new': '排新课表', 'check': '检查已有课表', 'adjust': '调课或补课', 'template': '先准备资料模板'}


def guide(context=None):
    c = {} if context is None else context
    if not isinstance(c, dict):
        raise InputError('引导上下文必须是JSON对象')
    for key, choices in [('profile', PROFILES), ('goal', GOALS),
                         ('mode', {'weekly_template': 1, 'date_range': 1})]:
        if c.get(key) is not None and c[key] not in choices:
            raise InputError(f'引导字段{key}取值无效', key)
    questions = []

    def ask(key, title, options=None):
        q = {'key': key, 'title': title}
        if options:
            q['options'] = [{'value': value, 'label': label} for value, label in options.items()]
        questions.append(q)

    if not c.get('profile'):
        ask('profile', '您要为哪类学校或机构排课？', PROFILES)
    if not c.get('goal'):
        ask('goal', '这次主要想完成什么？', GOALS)
    have_data = bool(c.get('demands') or c.get('assignments') or c.get('solution_path') or c.get('source_files'))
    if not c.get('materials') and not have_data and c.get('goal') != 'template':
        ask('materials', '您手头已有哪类资料？可以直接提供现有文件。',
            {'teacher_excel': '任课教师或课程Excel', 'schedule': '已有课表', 'text': '文字规则', 'none': '还没有，先用模板'})
    missing, reminders = [], []
    if not questions:
        goal = c.get('goal')
        if goal != 'template':
            if not c.get('mode'):
                ask('mode', '要排固定周课表，还是指定日期内的课程？',
                    {'weekly_template': '固定周课表', 'date_range': '指定日期，包括周末或短期班'})
            cal = c.get('calendar') or {}
            if c.get('mode') == 'date_range' and not (cal.get('start_date') and cal.get('end_date')):
                ask('calendar', '请提供排课起止日期，是否包含周末、停课或调休？')
            if c.get('mode') == 'weekly_template' and not cal.get('weekdays'):
                ask('calendar', '每周哪几天上课？是否有单双周或停课例外？')
            if not c.get('slots'):
                ask('slots', '每天有哪些可上课时段、每节多长？请说明午休和不同年级作息。')
            if not c.get('demands'):
                ask('demands', '请提供班级或教学组、课程课时及任课教师；现有表格可以直接读取。')
            if goal in {'check', 'adjust'} and not (c.get('assignments') or c.get('solution_path')):
                ask('solution_path', '请提供要检查或调整的现有课表。')
            if goal == 'adjust' and not c.get('change_request'):
                ask('change_request', '需要调整哪些课？哪些时间、教师或课位必须保持不变？')
            if not c.get('rules') and not c.get('preferences_confirmed'):
                ask('preferences_confirmed',
                    '有固定课、禁排、集备、连堂或教师特殊要求吗？没有特殊要求也可以说明。')
        missing = [q['key'] for q in questions]
    else:
        missing = [q['key'] for q in questions]
    if c.get('profile') == 'senior' and c.get('quality_policy', 'senior-standard') == 'senior-standard':
        reminders.append('高中默认同科每日最多2节，同日重复课需同半天相邻连堂；特殊安排可明确说明后单独配置。')
    if c.get('profile') == 'training':
        reminders.append('请区分课次数、教学分钟和课程包课时单位；兼职可用时间、跨校区和转场时间会影响结果。')
    if c.get('profile') in {'primary', 'junior'}:
        reminders.append('不同年级可有不同作息；包班教师、共享教师、实验室和体育场地需要一起检查。')
    if c.get('materials') == 'none' or c.get('goal') == 'template':
        reminders.append('模板内含演示数据，正式排课前请替换；不需要一次填完所有可选项。')
    if c.get('goal') != 'template' and (missing or not c.get('resources') or not c.get('external_scope_confirmed')):
        reminders.append('缺少资料仍可先整理或试排，但只报告已检查范围，不会将草稿称为正式可用课表。')
    action = ('ask_questions' if questions else 'create_template' if c.get('goal') == 'template'
              else 'review_existing' if c.get('goal') == 'check'
              else 'prepare_adjustment' if c.get('goal') == 'adjust' else 'precheck')
    return {'intro': '我可以帮您排新课表、检查冲突或调课。已有资料先读取，只补问缺少的信息。',
            'known': {k: c[k] for k in ['profile', 'goal', 'mode', 'materials'] if c.get(k) is not None},
            'questions': questions[:3], 'remaining_question_keys': [q['key'] for q in questions[3:]],
            'reminders': reminders, 'next_action': action,
            'question_policy': '每轮最多3问；先读取已提供资料，已知字段不重复问；用户明确允许试排时可先交付有限范围结果。'}
