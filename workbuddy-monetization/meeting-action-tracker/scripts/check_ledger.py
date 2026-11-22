"""Dependency-free ledger checks; semantic interpretation remains the agent's job."""
import argparse
import json
from datetime import date
from pathlib import Path


def check(data, as_of):
    errors, rows = [], []
    if data.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    source = data.get('source', {})
    tasks = data.get('tasks', [])
    if not isinstance(source, dict) or not isinstance(tasks, list):
        return {'valid': False, 'errors': ['source/tasks type invalid'], 'tasks': []}
    ids = [t.get('id') for t in tasks]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        errors.append('task IDs must be nonempty unique strings')
    by_id = {t.get('id'): t for t in tasks}
    graph = {}
    for t in tasks:
        key = t.get('id')
        for field in ('id', 'action', 'deliverable', 'acceptance', 'owner', 'due',
                      'dependency_state', 'depends_on', 'status', 'evidence'):
            if field not in t:
                errors.append(f'{key}: missing {field}')
        if not isinstance(t.get('action'), str) or not t.get('action', '').strip():
            errors.append(f'{key}: action required')
        if t.get('status') not in {'proposed', 'open', 'in_progress', 'done', 'cancelled'}:
            errors.append(f'{key}: invalid status')
        supports = set()
        for e in t.get('evidence', []):
            quote = e.get('quote')
            if not isinstance(quote, str) or not quote or quote not in source.get(e.get('paragraph'), ''):
                errors.append(f'{key}: evidence not found in source')
            else:
                supports.update(e.get('supports', []))
        needed = {'action'}
        needed.update(f for f in ('owner', 'due', 'deliverable', 'acceptance') if t.get(f))
        state = t.get('dependency_state')
        deps = t.get('depends_on', [])
        if state not in {'unknown', 'none', 'explicit'}:
            errors.append(f'{key}: invalid dependency_state')
        if state != 'unknown':
            needed.add('dependency')
        if t.get('status') in {'done', 'cancelled'}:
            needed.add('status')
        if needed - supports:
            errors.append(f'{key}: missing evidence for {sorted(needed - supports)}')
        if not isinstance(deps, list):
            errors.append(f'{key}: depends_on must be a list')
            deps = []
        if deps and state != 'explicit':
            errors.append(f'{key}: dependency state contradicts links')
        if state == 'explicit' and not deps and not t.get('external_dependencies'):
            errors.append(f'{key}: explicit dependency needs a target')
        graph[key] = deps
        for dep in deps:
            if dep not in by_id:
                errors.append(f'{key}: missing dependency {dep}')
        deadline = None
        due = t.get('due')
        if due is not None:
            if not isinstance(due, dict) or not due.get('raw'):
                errors.append(f'{key}: due must contain raw text')
            elif due.get('date'):
                try:
                    deadline = date.fromisoformat(due['date'])
                    if not due.get('basis'):
                        errors.append(f'{key}: normalized date needs basis')
                except (TypeError, ValueError):
                    errors.append(f'{key}: invalid date')
        blocked = any(by_id.get(d, {}).get('status') != 'done' for d in deps) or bool(t.get('external_dependencies'))
        missing = [f for f in ('owner', 'deliverable', 'acceptance') if not t.get(f)]
        if deadline is None:
            missing.append('deadline')
        if state == 'unknown':
            missing.append('dependencies')
        terminal = t.get('status') in {'done', 'cancelled'}
        ready = not (missing or blocked or t.get('conflicts') or t.get('status') == 'proposed' or terminal)
        timing = 'closed' if terminal else ('deadline_pending' if deadline is None else
                 'overdue' if deadline < as_of else 'due_today' if deadline == as_of else 'upcoming')
        rows.append({'id': key, 'ready': ready, 'blocked': bool(blocked), 'missing': missing, 'timing': timing})
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            errors.append(f'{key}: dependency cycle')
            return
        if key in visited:
            return
        visiting.add(key)
        for dep in graph.get(key, []):
            if dep in graph:
                visit(dep)
        visiting.remove(key)
        visited.add(key)

    for key in graph:
        visit(key)
    if errors:
        for row in rows:
            row['ready'] = False
    return {'valid': not errors, 'errors': errors, 'tasks': rows,
            'limitation': 'Checks evidence presence, not semantic support; human review required.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--as-of', required=True, type=date.fromisoformat)
    args = parser.parse_args()
    try:
        result = check(json.loads(args.ledger.read_text(encoding='utf-8')), args.as_of)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        result = {'valid': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['valid'] else 1)
