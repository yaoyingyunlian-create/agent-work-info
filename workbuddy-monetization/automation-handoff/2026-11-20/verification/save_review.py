"""Persist this read-only platform check; does not submit or alter assets."""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = Path.home() / 'ego/workbuddy-new-flow-20261120'
now = datetime.now(timezone(timedelta(hours=8))).isoformat()


def save(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


names = ['定时任务上下文体检', '工作空间膨胀体检', '报销底稿-单据预审版', '会议待办拆解追踪',
         '任务产物验收-标准版', '学校与培训机构排课', '对照校审（基准唯一版）', '智能学习陪练',
         '自动化任务验真巡检', '自动化质量巡检', '本地美业获客专家']
assets = []
for file, kind, url in [('skills.txt', 'skill', 'https://open.workbuddy.cn/skill/all'),
                         ('experts.txt', 'expert', 'https://open.workbuddy.cn/expert/all')]:
    text = (SOURCE / file).read_text(encoding='utf-8')
    (HERE / file).write_text(text, encoding='utf-8')
    for match in re.finditer(r'已发布\s+公开 · v([\d.]+) · ((?:os|oe)_[a-z0-9]+)(?: · ¥([\d.]+))?', text):
        preceding = text[:match.start()]
        name = max(names, key=lambda name: preceding.rfind(name))
        assets.append({'title': name, 'type': kind, 'asset_id': match[2], 'version': match[1],
                       'state': 'published', 'price_cny': match[3], 'source': url,
                       'first_published_at': None})
assert len(assets) == 11, f'Unexpected parsed asset count: {len(assets)}'
save(HERE / 'platform-status.json', {'observed_at': now, 'assets': assets})
ops = json.loads((SOURCE / 'operations.json').read_text(encoding='utf-8'))
rows = []
by_name = {asset['title']: asset for asset in assets}
for page in ops['pages']:
    for row in page[1:]:
        columns = [column.strip() for column in row.split('\t')]
        asset = by_name[columns[0]]
        rows.append({'asset_id': asset['asset_id'], 'title': columns[0],
                     'installs': int(columns[1]), 'calls': int(columns[2]),
                     'active_users': int(columns[3]), 'frequency_label': columns[4],
                     'next_week_retention_label': columns[5], 'impressions': None, 'detail_views': None})
assert len(rows) == 11 and len({row['asset_id'] for row in rows}) == 11
save(HERE / 'operations.json', {**{key: value for key, value in ops.items() if key != 'pages'},
                              'source': 'https://open.workbuddy.cn/operations', 'rows': rows})
orders = [
    {'asset_id': 'os_52efb5f1213b6d5a', 'time': '2026-11-19T21:02:37+08:00', 'bill_amount_cny': '7.92', 'status': 'pending_settlement'},
    {'asset_id': 'os_0c287fd18e58b0ff', 'time': '2026-11-18T11:43:51+08:00', 'bill_amount_cny': '8.91', 'status': 'pending_settlement'},
    {'asset_id': 'os_52efb5f1213b6d5a', 'time': '2026-11-16T13:15:26+08:00', 'bill_amount_cny': '7.92', 'status': 'pending_settlement'},
]
billing = {'observed_at': now, 'source': 'https://open.workbuddy.cn/monetization',
           'platform_cumulative_income_cny': '24.75', 'account_balance_cny': '24.87',
           'withdrawable_cny': '0', 'payer_count': 3, 'bills_observed': 3, 'orders': orders,
           'order_key_limitation': 'No visible order ID; asset + timestamp + amount + status used for this snapshot.',
           'refunds': None, 'net_income': None, 'refresh_lag': None,
           'previous_day_observed_bills': 1, 'today_observed_bills': 0}
save(HERE / 'billing.json', billing)

# Preserve latest historical demand records; current observations replace only matching asset status.
pending = {}
inputs = []
for path in sorted((ROOT / 'automation-handoff').glob('2026-11-*/0?-*.json')):
    if path.parent.name >= '2026-11-20':
        continue
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    inputs.append(str(path))
    for item in document['items']:
        pending[item['demand_id']] = item.copy()
for asset in assets:
    matching = [item for item in pending.values()
                if item.get('asset_id') == asset['asset_id'] and item.get('type') == asset['type']]
    if not matching:
        matching = [{'demand_id': 'asset-' + asset['asset_id'], 'type': asset['type']}]
    for item in matching:
        item.update({key: asset[key] for key in ('asset_id', 'version', 'state', 'title')})
        item['evidence'] = [asset['source'], str(HERE / 'platform-status.json')]
        item['status_verified_at'] = now
        item['next_action'] = '继续观测真实使用和经营数据；首次运行未在本轮验证。'
        pending[item['demand_id']] = item
for asset_id in ['os_52efb5f1213b6d5a', 'os_0c287fd18e58b0ff']:
    item = pending.get('billing-' + asset_id, {'demand_id': 'billing-' + asset_id, 'type': 'business_metrics'})
    observed = [order for order in orders if order['asset_id'] == asset_id]
    item.update({'asset_id': asset_id, 'state': 'confirmed', 'paid_orders_observed': len(observed),
                 'order_events': observed, 'evidence': [billing['source'], str(HERE / 'billing.json')],
                 'next_action': '将成交及近7天使用指标交分析阶段；保持价格，优先验证学习陪练的场景与首次交付文案。'})
    pending[item['demand_id']] = item
pending['FLOW-20261120-01'] = {
    'demand_id': 'FLOW-20261120-01', 'type': 'automation_verification', 'state': 'partial',
    'evidence': [str(HERE / 'validation.json'), str(HERE / 'report.md')],
    'next_action': '观察修正后的完整定时运行；记录周目标生产消费、补跑以及真实发布证据。',
    'known_gaps': ['2026-11-19缺05交接，未补造历史记录', '尚无正式06周复盘文件',
                   '周目标共享协议已保存，尚无实际调度运行证据', 'PPTX仍缺真实样本、嵌入字体用例和ZIP封面']}
save(HERE.parent / '05-review.json', {
    'date': '2026-11-20', 'stage': '05-review', 'generated_at': now, 'state': 'partial',
    'items': list(pending.values()), 'inputs': inputs,
    'today_upstream': {'state': 'no_input', 'reason': '检查发生在今日13:00收集前，01至04尚未到时；继续回查历史。'},
    'business_summary': billing,
    'operations': {'window_label': '7天', 'date_boundaries': None, 'rows': rows,
                   'single_day_metrics': None, 'conversion_rate': None,
                   'limitation': '滚动运营数据和累计/单日账单不同口径，不计算转化率；平台更新时间未显示。'},
    'listing_optimization': {'asset_id': 'os_52efb5f1213b6d5a', 'state': 'queued',
                             'baseline_observed_at': now, 'observation_window': '7天（后台原标签）',
                             'changes_applied': False, 'next_validation': '交付有现有能力支撑的适用场景、首次交付示例草稿；无曝光数据，不判断漏斗掉点。'},
    'new_submissions': 0, 'online_changes': 0,
    'runtime_end_to_end_verified': False})
print(json.dumps({'assets_verified': len(assets), 'operations_rows': len(rows),
                  'bills_verified': len(orders), 'review': str(HERE.parent / '05-review.json')}, ensure_ascii=False))
