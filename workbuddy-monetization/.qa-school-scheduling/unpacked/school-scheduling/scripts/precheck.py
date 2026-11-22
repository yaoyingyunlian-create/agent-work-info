from collections import defaultdict
from common import digest
from model_data import build_candidates, amount


def precheck(data):
    prepared, empty = build_candidates(data)
    errors = [{'code': 'NO_CANDIDATES', 'session_id': sid,
               'message': '无可用候选：核对课长、固定、禁排、可用性、资源资格、外部占用与锁定'} for sid in empty]
    totals = defaultdict(lambda: {'sessions': 0, 'candidates': 0})
    for s, opts in prepared:
        totals[s['demand_id']]['sessions'] += 1
        totals[s['demand_id']]['candidates'] += len(opts)
    return {'valid': not errors, 'input_hash': digest(data), 'errors': errors,
            'session_count': len(prepared), 'candidate_count': sum(len(c) for _, c in prepared),
            'demands': dict(totals), 'note': '预检通过不保证存在可行解；完整硬约束由求解与独立校验判断'}
