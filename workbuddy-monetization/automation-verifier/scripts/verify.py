"""Read-only outcome verification; Python standard library only."""
import argparse
import csv
import html
import io
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

VERSION = '1.0.0'
LABELS = {'verified': '真成功', 'false_success': '假成功', 'manual': '需人工'}


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('时间必须包含时区')
    return dt


def resolve(base, value):
    if not isinstance(value, str) or not value.strip() or '://' in value:
        raise ValueError('产出须为非空本地路径')
    path = Path(value)
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def validate(data, base):
    now = timestamp(data['as_of'])
    days = data.get('days', 7)
    if type(days) is not int or not 1 <= days <= 31:
        raise ValueError('days须为1至31整数')
    if type(data.get('coverage_confirmed', False)) is not bool:
        raise ValueError('coverage_confirmed须为布尔值')
    if not isinstance(data['tasks'], list):
        raise ValueError('tasks须为数组')
    tasks = set()
    paths = []
    for task in data['tasks']:
        if not isinstance(task['id'], str) or not task['id'] or task['id'] in tasks:
            raise ValueError('任务id必须为唯一非空字符串')
        tasks.add(task['id'])
        if not isinstance(task['name'], str) or not task['name'].strip():
            raise ValueError('任务名须为非空字符串')
        if not isinstance(task['runs'], list):
            raise ValueError('runs须为数组')
        ids = set()
        for run in task['runs']:
            if not isinstance(run['id'], str) or not run['id'] or run['id'] in ids:
                raise ValueError('运行id必须为任务内唯一非空字符串')
            ids.add(run['id'])
            if timestamp(run['start']) > timestamp(run['due']):
                raise ValueError('start不能晚于due')
            if run.get('claimed_status', 'unknown') not in ('success', 'failed', 'unknown'):
                raise ValueError('claimed_status不合法')
            if run.get('claimed_status') == 'success' and not str(run.get('claim_source', '')).strip():
                raise ValueError('成功声明必须有claim_source出处')
            if run.get('artifact'):
                paths.append(resolve(base, run['artifact']))
    return now, days, Counter(paths)


def check_run(run, base, reused):
    checks = []

    def add(state, item, advice):
        checks.append({'state': state, 'item': item, 'advice': advice})

    path = resolve(base, run['artifact']) if run.get('artifact') else None
    if path is None:
        add('unknown', '未提供产出路径', '提供本次产出快照或人工核查凭据')
    elif reused[path] > 1:
        add('unknown', '多个时段共用同一路径，历史不可还原', '提供按次保存的独立快照')
    else:
        rule = run.get('checks')
        valid = (isinstance(rule, dict) and rule.get('mtime') is True
                 and rule.get('format') in ('csv', 'json', 'text')
                 and type(rule.get('min_rows')) is int and rule['min_rows'] >= 0
                 and isinstance(rule.get('required_fields'), list)
                 and all(isinstance(x, str) and x.strip() for x in rule['required_fields'])
                 and (rule['format'] != 'text' or not rule['required_fields'])
                 and ('data_time_field' not in rule or
                      (rule['format'] != 'text' and isinstance(rule['data_time_field'], str)
                       and bool(rule['data_time_field'].strip()))))
        if not valid:
            add('unknown', '验收口径缺失或不支持', '确认时间、格式、最小行数和必填字段')
        else:
            try:
                before = path.stat()
                if not path.is_file():
                    raise OSError('not a regular file')
                raw = path.read_text(encoding='utf-8-sig')
                after = path.stat()
                if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                    add('unknown', '检查期间文件变化', '提供稳定快照后重新巡检')
                    return finish(run, path, checks)
                start, due = timestamp(run['start']), timestamp(run['due'])
                mt = datetime.fromtimestamp(before.st_mtime, tz=start.tzinfo)
                add('pass' if start <= mt <= due else 'fail', '文件修改时间：' + mt.isoformat(),
                    '核对是否过期、迟到或时间口径不适用；不能仅修改时间戳来通过验收')
                fmt = rule['format']
                if fmt == 'csv':
                    reader = csv.DictReader(io.StringIO(raw), strict=True)
                    rows = list(reader)
                    columns = set(reader.fieldnames or [])
                    if any(None in row or any(v is None for v in row.values()) for row in rows):
                        raise ValueError('CSV列数不一致')
                elif fmt == 'json':
                    rows = json.loads(raw)
                    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                        raise ValueError('JSON须为对象数组')
                    columns = set(rows[0]) if rows else set()
                else:
                    rows = [x for x in raw.splitlines() if x.strip()]
                    columns = set()
                add('pass' if len(rows) >= rule['min_rows'] else 'fail',
                    '行数：{}，要求至少{}'.format(len(rows), rule['min_rows']), '核对上游数据与导出范围')
                fields = rule['required_fields']
                missing = [f for f in fields if f not in columns or any(
                    f not in r or r[f] is None or (isinstance(r[f], str) and not r[f].strip())
                    or r[f] == [] or r[f] == {} for r in rows)]
                if fields:
                    add('fail' if missing else 'pass', '必填字段不达标数：{}'.format(len(missing)),
                        '核对字段映射、空值与源数据；参照输入中的required_fields')
                if rule.get('data_time_field'):
                    key = rule['data_time_field']
                    try:
                        good = bool(rows) and all(start <= timestamp(r[key]) <= due for r in rows)
                    except (KeyError, TypeError, ValueError, AttributeError):
                        good = False
                    add('pass' if good else 'fail', '业务时间字段：' + ('达标' if good else '缺失或超出时段'),
                        '核对数据实际更新时间、时区及适用范围')
            except FileNotFoundError:
                add('fail', '本次产出文件不存在', '核对路径、连接器登录和上游数据；如需补跑由用户人工决定')
            except (OSError, UnicodeError, ValueError, csv.Error):
                add('unknown', '无法读取或解析产出', '核对权限、UTF-8编码和格式；提供可读快照')
    return finish(run, path, checks)


def finish(run, path, checks):
    states = {c['state'] for c in checks}
    claimed = run.get('claimed_status', 'unknown')
    if 'fail' in states and claimed == 'success':
        status = 'false_success'
    elif states == {'pass'}:
        status = 'verified'
    else:
        status = 'manual'
    return {'run_id': run['id'], 'start': run['start'], 'due': run['due'],
            'claimed_status': claimed, 'claim_source': run.get('claim_source', ''),
            'artifact': str(path) if path else None, 'status': status,
            'label': LABELS[status], 'checks': checks}


def audit(data, base):
    now, days, paths = validate(data, base)
    lower = now - timedelta(days=days)
    entries, excluded, empty = [], [], []
    for task in data['tasks']:
        included = 0
        for run in task['runs']:
            due = timestamp(run['due'])
            if not lower < due <= now:
                excluded.append({'task_id': task['id'], 'run_id': run['id'],
                                 'reason': '未到期' if due > now else '窗口外'})
                continue
            included += 1
            entry = check_run(run, base, paths)
            entry.update(task_id=task['id'], task_name=task['name'])
            entries.append(entry)
        if not included:
            empty.append(task['id'])
    return {'version': VERSION, 'as_of': data['as_of'], 'window_start_exclusive': lower.isoformat(),
            'coverage_confirmed_by_user': data.get('coverage_confirmed', False),
            'counts': {key: sum(r['status'] == key for r in entries) for key in LABELS},
            'entries': entries, 'excluded': excluded, 'tasks_without_due_runs': empty,
            'limitations': ['仅核验输入清单和配置口径，不能独立证明应执行清单完整',
                            '无日志不推断成功声明；无按次快照不还原历史',
                            '只读手动快照，不提供后台监控、重跑或通知']}


def render(report, output):
    # Exclusive directory creation prevents overwriting sources and prior reports.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    counts = ' / '.join('{} {}'.format(LABELS[k], v) for k, v in report['counts'].items())
    coverage = '用户已确认清单完整' if report['coverage_confirmed_by_user'] else '覆盖未确认'
    lines = ['# 自动化任务验真巡检', '', counts, '',
             '截止：{}；{}。'.format(report['as_of'], coverage),
             '窗口：({}, {}]'.format(report['window_start_exclusive'], report['as_of']), '',
             '无到期实例任务：{}；排除实例：{}。'.format(len(report['tasks_without_due_runs']), len(report['excluded'])), '']
    cards = []
    esc = lambda v: html.escape(str(v), quote=True)
    for row in report['entries']:
        title = '{} / {}：{}'.format(row['task_name'], row['run_id'], row['label'])
        evidence = '产出：{}；运行声明：{}；出处：{}'.format(row['artifact'], row['claimed_status'], row['claim_source'])
        details = ['{}：{}。{}'.format(c['state'], c['item'], c['advice'] if c['state'] != 'pass' else '') for c in row['checks']]
        lines.extend(['## ' + title, '', evidence, ''] + ['- ' + d for d in details] + [''])
        cards.append('<article class="{}"><h2>{}</h2><p>{}</p><ul>{}</ul></article>'.format(
            row['status'], esc(title), esc(evidence), ''.join('<li>' + esc(d) + '</li>' for d in details)))
    lines += ['## 限制', ''] + ['- ' + x for x in report['limitations']]
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>自动化任务验真巡检</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;background:#f5f7fb;color:#172033}h1{font-size:28px}article{background:white;border-left:6px solid #a16207;border-radius:8px;padding:12px 20px;margin:16px 0;overflow-wrap:anywhere}.verified{border-color:#15803d}.false_success{border-color:#dc2626}h2{font-size:18px}header{background:#142b47;color:white;padding:24px;border-radius:12px}small{display:block}</style>
<header><h1>自动化任务验真巡检</h1><p>COUNTS</p><small>META</small></header>CARDS<footer>LIMITS</footer></html>'''
    page = page.replace('COUNTS', esc(counts)).replace('META', esc('截止：' + report['as_of'] + '；' + coverage))
    page = page.replace('CARDS', ''.join(cards) or '<p>没有可核验的到期实例，请核对清单。</p>')
    page = page.replace('LIMITS', esc('；'.join(report['limitations'])))
    (output / 'report.html').write_text(page, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='只读核验自动化产出；退出0不代表所有任务成功')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        source, output = Path(args.input).resolve(), Path(args.output).resolve()
        data = json.loads(source.read_text(encoding='utf-8-sig'))
        _, _, paths = validate(data, source.parent)
        if any(p == output or output in p.parents for p in [source] + list(paths)):
            raise ValueError('报告目录不能包含输入或产出文件')
        report = audit(data, source.parent)
        render(report, output)
        print(json.dumps({'report': str(output), 'counts': report['counts']}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(2, '巡检未完成：{}\n'.format(type(exc).__name__))


if __name__ == '__main__':
    main()
