"""Generate fictional fixtures in a new directory, never real user evidence."""
import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def generate(output):
    output.mkdir(parents=True, exist_ok=False)
    tasks = []
    for index, name in enumerate(['演示：竞品简报', '演示：数据同步', '演示：签到记录']):
        task = {'id': 'demo-' + str(index), 'name': name, 'runs': []}
        for day in range(7):
            start = datetime.fromisoformat('2026-10-31T09:00:00+08:00') + timedelta(days=day)
            due = start + timedelta(hours=1)
            path = output / '{}-{}.csv'.format(index, start.date())
            # One task always good, one silently empty, one has no readable evidence.
            if index < 2:
                body = 'id,updated_at\n'
                if index == 0:
                    body += 'demo-item,{}\n'.format((start + timedelta(minutes=20)).isoformat())
                path.write_text(body, encoding='utf-8')
                stamp = (start + timedelta(minutes=25)).timestamp()
                os.utime(path, (stamp, stamp))
            task['runs'].append({'id': str(start.date()), 'start': start.isoformat(), 'due': due.isoformat(),
                                  'claimed_status': 'success' if index < 2 else 'unknown',
                                  'claim_source': '虚构运行声明，仅供演示' if index < 2 else '',
                                  'artifact': path.name,
                                  'checks': {'mtime': True, 'format': 'csv', 'min_rows': 1,
                                             'required_fields': ['id', 'updated_at'], 'data_time_field': 'updated_at'}})
        tasks.append(task)
    data = {'as_of': '2026-11-06T18:00:00+08:00', 'days': 7, 'coverage_confirmed': True, 'tasks': tasks}
    (output / 'input.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    generate(Path(parser.parse_args().output).resolve())
