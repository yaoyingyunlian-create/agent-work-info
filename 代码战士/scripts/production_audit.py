"""Read-only production supervision. Never generates, publishes or creates a.txt."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ['标题.txt', '发布文案.txt', '标签.txt', '封面.jpg', '视频.mp4', '视觉质检.json']
STORY_REVIEW_START = '2026-11-11'
STORY_CHECKS = ('ancient_modern_causality', 'yangxin_location_causality', 'character_choice_payoff')

def release_check(folder):
    issues = []
    for name in CORE + ['验收材料/对白.lrc', '验收材料/分镜.md']:
        p = folder / name
        if not p.is_file() or not p.stat().st_size:
            issues.append('missing_or_empty:' + name)
    tags = folder / '标签.txt'
    if tags.is_file():
        lines = tags.read_text(encoding='utf-8-sig').strip().splitlines()
        if len(lines) != 1 or len(lines[0].split()) > 5:
            issues.append('tags_must_be_one_line_at_most_5')
    try:
        qa = json.loads((folder / '视觉质检.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        qa = {}
        issues.append('unreadable_review')
    # Legacy reports require explicit review rather than guessing their schema.
    if qa.get('publish_review_passed') is not True:
        issues.append('review_not_explicitly_passed')
    if qa.get('technical', {}).get('FAIL') or qa.get('technical', {}).get('WARN'):
        issues.append('technical_FAIL_or_WARN')
    checks = qa.get('checks', {})
    if not checks or any(not isinstance(c, dict) or c.get('status') != 'PASS' for c in checks.values()):
        issues.append('review_checks_incomplete')
    creation_date = qa.get('creation_date')
    if isinstance(creation_date, str) and creation_date >= STORY_REVIEW_START:
        for name in STORY_CHECKS:
            check = checks.get(name, {})
            if not isinstance(check, dict) or check.get('status') != 'PASS' or not str(check.get('evidence') or '').strip():
                issues.append('story_evidence_missing_or_failed:' + name)
    frames = qa.get('real_frame_paths', [])
    if not frames or any(not Path(p).is_file() for p in frames):
        issues.append('frame_evidence_missing')
    video = folder / '视频.mp4'
    if video.is_file():
        with video.open('rb') as source:
            actual = hashlib.file_digest(source, 'sha256').hexdigest()
        if actual != str(qa.get('video_sha256', '')).lower():
            issues.append('video_hash_unverified_or_changed')
    for name in CORE[:-1]:
        p = folder / name
        expected = qa.get('release_file_hashes', {}).get(name)
        if not expected:
            issues.append('release_hash_missing:' + name)
        elif p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            issues.append('release_changed:' + name)
    marker = folder / 'a.txt'
    marked = marker.is_file() and marker.stat().st_size == 0
    if marker.exists() and marker.stat().st_size != 0:
        issues.append('marker_not_empty')
    if not marked:
        issues.append('no_empty_marker')
    legacy = 'publish_review_passed' not in qa
    return {'path': str(folder), 'date': qa.get('creation_date'),
            'qualified': None if legacy else not issues, 'issues': issues,
            'assessment': 'legacy_schema_needs_mapping_not_revoked' if legacy else 'checked',
            'legacy_schema': legacy}

def task_check(task, now):
    stamp = task.get('last_transition_at') or task.get('created_at')
    try:
        elapsed = (now - datetime.fromisoformat(stamp).astimezone(timezone.utc)).total_seconds() / 60
    except (ValueError, TypeError):
        return {**task, 'action': 'record_real_transition_time'}
    state = task.get('status')
    if state == 'succeeded':
        action = 'download_review_then_continue'
    elif state in ['failed', 'canceled']:
        action = 'reconcile_charge_then_review_budget'
    elif state == 'submission_unknown':
        action = 'recover_same_request_id_only'
    elif elapsed >= 15 and task.get('phase') == 'persisting':
        action = 'technical_escalation_same_task_no_new_generation'
    elif state in ['pending', 'processing']:
        action = 'query_existing_task_continue_no_duplicate'
    else:
        action = 'inspect_record'
    return {**task, 'minutes_age': round(elapsed, 1),
            'age_basis': 'transition' if task.get('last_transition_at') else 'creation_fallback', 'action': action}

def analytics_review_queue(attempts, samples, now):
    """List actual publication receipts whose analytics checkpoints are still open."""
    recorded = {(s.get('work_id'), s.get('window_hours')) for s in samples
                if s.get('status') in {'measured', 'missed'}}
    queue = []
    for attempt in attempts:
        work_id = attempt.get('platform_work_id')
        if attempt.get('status') != 'published' or not work_id:
            continue
        try:
            published = datetime.fromisoformat(attempt['platform_published_at'])
            if published.utcoffset() is None:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        for hours in (24, 72):
            if (work_id, hours) in recorded:
                continue
            due = published + timedelta(hours=hours)
            queue.append({'work_id': work_id, 'url': attempt.get('url'), 'window_hours': hours,
                          'due_at': due.isoformat(), 'due': now >= due})
    return sorted(queue, key=lambda item: item['due_at'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True)
    parser.add_argument('--ledger', type=Path, default=ROOT/'策划/创作状态.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    month = ROOT/'成片'/args.date[:7]
    releases = [release_check(p) for p in month.iterdir() if p.is_dir()] if month.exists() else []
    try:
        ledger = json.loads(args.ledger.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        ledger = {}
    tasks = [task_check(t, datetime.now(timezone.utc)) for t in ledger.get('tasks', [])]
    try:
        publication = json.loads((ROOT/'运营/发布记录.json').read_text(encoding='utf-8-sig'))
        analytics = json.loads((ROOT/'运营/数据采样.json').read_text(encoding='utf-8-sig'))
        review_queue = analytics_review_queue(publication.get('attempts', []), analytics.get('samples', []), datetime.now(timezone.utc))
    except (OSError, ValueError):
        review_queue = None
    result = {'date': args.date, 'read_only': True,
              'qualified_today': [r['path'] for r in releases if r['qualified'] and r['date'] == args.date],
              'releases': releases, 'tasks': tasks,
              'analytics_review_queue': review_queue,
              'ledger_missing': not ledger,
              'boundary': '结构/证据一致性检查，不能替代实际播放、核听和剧情判断；旧格式报告不会被自动改写或删除标记。'}
    data = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding='utf-8')
    print(data)

if __name__ == '__main__':
    main()
