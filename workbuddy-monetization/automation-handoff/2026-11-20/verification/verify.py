"""Read-only verification of saved schedules and real handoffs. Python 3.12."""
import json
from datetime import datetime, timedelta
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def verify():
    original = json.loads((HERE / 'automation-config-before.json').read_text(encoding='utf-8'))
    errors, checks, documents = [], [], []
    for old in original['configs']:
        path = Path.home() / '.codex' / 'automations' / old['id'] / 'automation.toml'
        current = tomllib.loads(path.read_text(encoding='utf-8'))
        for key in ('id', 'name', 'kind', 'rrule', 'status', 'target_thread_id'):
            if current.get(key) != old.get(key):
                errors.append(f'{old["id"]}: changed {key}')
        if old['id'] != 'workbuddy' and '联调补充（2026-11-20）' not in current['prompt']:
            errors.append(f'{old["id"]}: linkage patch missing')
        checks.append({'automation_id': old['id'], 'status': current['status'],
                       'schedule_preserved': current['rrule'] == old['rrule'],
                       'thread_preserved': current['target_thread_id'] == old['target_thread_id']})
    for path in sorted((ROOT / 'automation-handoff').glob('????-??-??/0?-*.json')):
        doc = json.loads(path.read_text(encoding='utf-8-sig'))
        missing = {'date', 'stage', 'generated_at', 'state', 'items'} - doc.keys()
        if missing:
            errors.append(f'{path}: missing {sorted(missing)}')
        if doc['date'] != path.parent.name or doc['stage'] != path.stem:
            errors.append(f'{path}: date or stage mismatch')
        if datetime.fromisoformat(doc['generated_at']).utcoffset() != timedelta(hours=8):
            errors.append(f'{path}: timestamp is not +08:00')
        if doc['state'] not in ('complete', 'partial', 'blocked', 'no_input'):
            errors.append(f'{path}: invalid top-level state')
        for index, item in enumerate(doc['items']):
            missing = {'demand_id', 'type', 'state', 'evidence', 'next_action'} - item.keys()
            if missing or not isinstance(item.get('evidence'), list):
                errors.append(f'{path}: invalid item {index}')
        documents.append({'path': str(path), 'state': doc['state'], 'items': len(doc['items'])})
    build = json.loads((ROOT / 'automation-handoff/2026-11-19/03-build.json').read_text(encoding='utf-8'))
    release = json.loads((ROOT / 'automation-handoff/2026-11-19/04-release.json').read_text(encoding='utf-8'))
    if build.get('ready_to_release') or release.get('new_submissions') != 0:
        errors.append('Nov19 no-ready-package guard differs from expected historical evidence')
    return {'scope': 'saved configuration, historical handoff schema, historical no-ready guard',
            'automations': checks, 'documents': documents, 'errors': errors,
            'runtime_end_to_end_verified': False, 'production_submission_performed': False,
            'historical_no_ready_guard_verified': not build.get('ready_to_release') and release.get('new_submissions') == 0,
            'known_gaps': ['2026-11-19/05-review.json absent; this run records a later observation only',
                           'No formal 06-weekly.json found before this run',
                           'Revised weekly-target producer and daily consumers not yet scheduler-tested together',
                           'PPTX prototype has no release ZIP/cover and incomplete real-file/embed evidence']}


if __name__ == '__main__':
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['errors']))
