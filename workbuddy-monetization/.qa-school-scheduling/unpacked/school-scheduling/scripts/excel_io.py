from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.workbook.properties import CalcProperties
from common import ROOT, InputError, digest, clock, write_json, minute
from normalize_input import normalize
from validate_schedule import validate

TABLES = {'groups': '教学组', 'teachers': '教师', 'students': '学生', 'resources': '场地资源',
          'slots': '作息窗口', 'demands': '教学需求', 'rules': '排课规则',
          'external_occupancy': '外部占用', 'locks': '锁定安排'}
LIST_FIELDS = {'student_ids', 'exclusive_with', 'group_ids', 'teacher_ids', 'eligible_teacher_ids',
               'resource_ids', 'eligible_resource_ids', 'duration_options', 'slot_ids', 'weekdays',
               'week_types', 'demand_ids', 'course_ids', 'qualifications', 'features', 'required_features',
               'person_ids', 'availability', 'unavailability', 'fixed', 'windows', 'memberships'}
DICT_FIELDS = {'quota', 'rotation', 'resource_usage'}
BOOL_FIELDS = {'membership_complete', 'conflicts_confirmed', 'flexible', 'enabled', 'across_weeks', 'required'}
INT_FIELDS = {'size', 'seats', 'capacity', 'setup_minutes', 'cleanup_minutes', 'step_minutes',
              'session_count', 'daily_minutes', 'daily_sessions', 'rest_minutes', 'tier', 'weight',
              'max', 'minutes', 'target', 'max_break_minutes', 'duration_minutes'}


def append(ws, row):
    ws.append(row)
    for cell in ws[ws.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = 's'


def finish(wb, path):
    for ws in wb:
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        ws.sheet_view.showGridLines = False
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='24476B')
        for column in ws.columns:
            letter = column[0].column_letter
            width = min(70, max(14, max(len(str(c.value or '')) for c in list(column)[:50]) + 2))
            ws.column_dimensions[letter].width = width
        ws.print_options.horizontalCentered = True
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.print_title_rows = '1:1'
    wb.calculation = CalcProperties(calcId=191029, fullCalcOnLoad=True)
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.xlsx')
    os.close(fd)
    try:
        wb.save(tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def template(data, path):
    wb = Workbook()
    ws = wb.active
    ws.title = '填写说明'
    for row in [['项目', '说明'], ['适用场景', data['profile']],
                ['基础', '本模板含脱敏示例；配置与日历的值使用JSON语法，保留schema_version。'],
                ['列表', '教师ID、组ID、窗口等列表填写JSON，例如 ["T1"]；布尔用 true/false。'],
                ['时间', 'HH:MM；星期0至6；日期YYYY-MM-DD；课堂时间与课时单位必须明确。'],
                ['修改', '替换示例数据，保持ID引用对应；空白单元格表示该字段不提供。'],
                ['安全', '不支持Excel输入公式，请提供常量；学生使用匿名ID。'],
                ['规则', '见 references/rule-catalog.md；未知启用规则会阻断。']]:
        append(ws, row)
    settings = {k: v for k, v in data.items() if k not in set(TABLES) | {'calendar', 'expanded_calendar'}}
    for name, values in [('配置', settings), ('日历', data['calendar'])]:
        ws = wb.create_sheet(name)
        append(ws, ['key', 'value_json'])
        for k, v in values.items():
            append(ws, [k, json.dumps(v, ensure_ascii=False)])
    for key, title in TABLES.items():
        ws = wb.create_sheet(title)
        items = data.get(key, [])
        keys = list(dict.fromkeys(k for item in items for k in item)) or ['id']
        append(ws, keys)
        for item in items:
            append(ws, [json.dumps(item[k], ensure_ascii=False) if isinstance(item.get(k), (dict, list, bool)) else item.get(k) for k in keys])
    finish(wb, path)


def import_excel(path):
    wb = load_workbook(path, data_only=False)
    data, errors, locations = {}, [], {}
    def error(ws, row, col, message):
        errors.append({'sheet': ws, 'row': row, 'column': col, 'error_code': 'IMPORT_ERROR', 'message': message})
    for ws in wb:
        for row in ws:
            for cell in row:
                if cell.data_type == 'f':
                    error(ws.title, cell.row, cell.column_letter, '输入不接受公式，请替换为常量')
    for name, target in [('配置', data), ('日历', {})]:
        if name not in wb:
            errors.append({'sheet': name, 'row': 1, 'column': 'A', 'error_code': 'MISSING_SHEET', 'message': '缺少必填工作表'})
            continue
        if name == '日历':
            data['calendar'] = target
        for number, row in enumerate(wb[name].iter_rows(min_row=2, values_only=True), 2):
            if not any(v is not None for v in row):
                continue
            try:
                k, v = row[:2]
                if k in target:
                    raise ValueError('重复配置键')
                target[k] = json.loads(str(v))
            except (ValueError, TypeError) as exc:
                error(name, number, 'B', str(exc))
    for key, title in TABLES.items():
        if title not in wb:
            continue
        ws = wb[title]
        headers = [c.value for c in ws[1]]
        if len(headers) != len(set(headers)):
            error(title, 1, 'A', '列名重复')
        items = []
        seen = set()
        for number, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not any(v is not None for v in row):
                continue
            item = {}
            for col, value in enumerate(row):
                if value is None:
                    continue
                field = headers[col]
                try:
                    if field in LIST_FIELDS | DICT_FIELDS | BOOL_FIELDS:
                        parsed = json.loads(value) if isinstance(value, str) else value
                        typ = list if field in LIST_FIELDS else dict if field in DICT_FIELDS else bool
                        if not isinstance(parsed, typ):
                            raise ValueError(f'{field} 要求 {typ.__name__}')
                        item[field] = parsed
                    elif field in INT_FIELDS:
                        if isinstance(value, bool) or float(value) != int(value):
                            raise ValueError('要求整数')
                        item[field] = int(value)
                    else:
                        item[field] = str(value)
                except (ValueError, TypeError) as exc:
                    error(title, number, col + 1, str(exc))
            if item.get('id') in seen:
                error(title, number, 'A', '重复ID')
            seen.add(item.get('id'))
            locations[f'{key}[{len(items)}]'] = (title, number)
            items.append(item)
        data[key] = items
    if not errors:
        try:
            data = normalize(data)
        except (InputError, KeyError, TypeError, ValueError) as exc:
            path = getattr(exc, 'path', 'input')
            sheet, row = next((where for prefix, where in locations.items() if path.startswith(prefix)), ('配置', 2))
            errors.append({'sheet': sheet, 'row': row, 'column': path.rsplit('.', 1)[-1],
                           'error_code': getattr(exc, 'code', 'INVALID_INPUT'), 'message': str(exc)})
    return data, errors


def export(data, solution, supplied_report, path, draft=False):
    report = validate(data, solution)
    for key in ['input_hash', 'rule_hash', 'calendar_hash', 'solution_hash']:
        if supplied_report.get(key) != report[key]:
            raise InputError('校验报告与当前方案不匹配，拒绝导出', key, 'STALE_REPORT')
    if not report['ready_for_acceptance'] and not draft:
        raise InputError('未满足完整验收条件；仅可使用 --draft 导出带标记草稿', code='NOT_READY')
    path = Path(path)
    if draft and not report['ready_for_acceptance'] and '未通过校验' not in path.stem:
        path = path.with_name(path.stem + '_未通过校验' + path.suffix)
    wb = Workbook()
    ws = wb.active
    ws.title = '版本说明'
    for row in [['项目', '值'], ['状态', report['delivery_status']], ['排课范围', report['calendar_scope']],
                ['时区', data['timezone']], ['任务', data['task_id']], ['输入哈希', report['input_hash']],
                ['课表哈希', report['solution_hash']], ['求解状态', solution.get('status')],
                ['检查日期', ','.join(report['checked_dates'])], ['提示', '排课通过不代表正式发布；公式需在Excel/WPS打开后重算。']]:
        append(ws, row)
    ws = wb.create_sheet('活动明细')
    append(ws, ['session_id', 'date', 'start', 'end', 'demand_id', 'scope', 'course_id', 'group_ids',
                'teacher_ids', 'resource_ids', 'status', '教学分钟', 'week_type', 'campus_id'])
    rows = solution.get('assignments', []) + solution.get('canceled_history', [])
    for c in rows:
        append(ws, [c['session_id'], c['date'], clock(c['start']), clock(c['end']), c['demand_id'], c['scope'],
                    c['course_id'], ','.join(c['group_ids']), ','.join(c['teacher_ids']), ','.join(c['resource_ids']),
                    c.get('status', 'scheduled'), c['end']-c['start'], c['week_type'], c['campus_id']])
    end = max(2, len(rows) + 1)
    qs = wb.create_sheet('教学需求')
    append(qs, ['demand_id', 'scope', '单位', '应排次数', '实排次数公式', '次数差额', '应排分钟', '实排分钟公式', '独立校验次数', '独立校验分钟'])
    for i, q in enumerate(report['quota_deltas'], 2):
        append(qs, [q['demand_id'], q['scope'], q['unit'], q['expected_sessions'], None, None,
                    q['expected_minutes'], None, q['actual_sessions'], q['actual_minutes']])
        qs.cell(i, 5, f'=COUNTIFS(活动明细!E$2:E${end},A{i},活动明细!F$2:F${end},B{i},活动明细!K$2:K${end},"scheduled")')
        qs.cell(i, 6, f'=E{i}-D{i}')
        qs.cell(i, 8, f'=SUMIFS(活动明细!L$2:L${end},活动明细!E$2:E${end},A{i},活动明细!F$2:F${end},B{i},活动明细!K$2:K${end},"scheduled")')
    for title, field, objects in [('组课表', 'group_ids', data['groups']), ('教师课表', 'teacher_ids', data['teachers']),
                                  ('场地课表', 'resource_ids', data['resources'])]:
        ws = wb.create_sheet(title)
        append(ws, ['对象ID', '名称', '日期', '周型', '开始', '结束', '课程', '教学组', '教师', '场地', '活动ID'])
        for obj in objects:
            for c in solution.get('assignments', []):
                if obj['id'] in c[field]:
                    append(ws, [obj['id'], obj.get('name', obj['id']), c['date'], c['week_type'], clock(c['start']),
                                clock(c['end']), c['course_id'], ','.join(c['group_ids']), ','.join(c['teacher_ids']),
                                ','.join(c['resource_ids']), c['session_id']])
    if data['students']:
        from model_data import participants
        ws = wb.create_sheet('学生课表')
        append(ws, ['匿名学生ID', '日期', '开始', '结束', '课程', '活动ID'])
        for c in solution.get('assignments', []):
            for sid in sorted(participants(data, c['group_ids'], c['date'])):
                append(ws, [sid, c['date'], clock(c['start']), clock(c['end']), c['course_id'], c['session_id']])
    if data['mode'] == 'weekly_template':
        from expand_calendar import window_applies
        for group in data['groups']:
            for wt in data['calendar'].get('week_types', ['all']):
                title = re.sub(r'[\\/*?:\[\]]', '_', f'{group["id"]}_{wt}')[:31]
                base_title, n = title, 1
                while title in wb.sheetnames:
                    n += 1
                    title = base_title[:26] + '_' + str(n)
                ws = wb.create_sheet(title)
                days = [day for day in data['expanded_calendar'] if day['week_type'] == wt]
                append(ws, ['节次与实际时间（示意周）'] + [day['date'] + '\n周' + '一二三四五六日'[day['weekday']] for day in days])
                for slot in data['slots']:
                    if slot.get('flexible') or (slot.get('group_ids') and group['id'] not in slot['group_ids']):
                        continue
                    row = [f'{slot["id"]}\n{slot["start"]}–{slot["end"]}']
                    for day in days:
                        if not window_applies(slot, day):
                            row.append('不可排')
                            continue
                        matches = [c for c in solution.get('assignments', []) if group['id'] in c['group_ids'] and c['date'] == day['date'] and
                                   c['start'] < minute(slot['end']) and minute(slot['start']) < c['end']]
                        row.append('\n'.join(f'{c["course_id"]} | {",".join(c["teacher_ids"])}\n{",".join(c["resource_ids"])} | {clock(c["start"])}–{clock(c["end"])}' for c in matches) or '空闲')
                    append(ws, row)
                    ws.row_dimensions[ws.max_row].height = 54
                    for cell in ws[ws.max_row]:
                        cell.alignment = Alignment(wrap_text=True, vertical='center')
    ws = wb.create_sheet('课程时段约束')
    append(ws, ['需求ID', '完整时间与分配约束JSON'])
    for d in data['demands']:
        append(ws, [d['id'], json.dumps(d, ensure_ascii=False)])
    ws = wb.create_sheet('排课规则')
    append(ws, ['规则ID', '规则定义JSON', '检查JSON'])
    rr = {r['rule_id']: r for r in report['rule_results']}
    for r in data['rules']:
        append(ws, [r['id'], json.dumps(r, ensure_ascii=False), json.dumps(rr[r['id']], ensure_ascii=False)])
    ws = wb.create_sheet('校验结果')
    append(ws, ['类别', '结果JSON'])
    append(ws, ['覆盖率', json.dumps(report['coverage'], ensure_ascii=False)])
    for item in report['hard_violations']:
        append(ws, ['硬冲突', json.dumps(item, ensure_ascii=False)])
    for item in report['soft_violations']:
        append(ws, ['未满足偏好', json.dumps(item, ensure_ascii=False)])
    for sid in report['pending_makeup_sessions']:
        append(ws, ['待补课', sid])
    finish(wb, path)
    return str(path.resolve())
