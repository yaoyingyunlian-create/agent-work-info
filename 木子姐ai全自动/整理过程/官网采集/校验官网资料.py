# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.parse import unquote,urlsplit
from lxml import html
import json,re,hashlib
from 采集官网 import ROOT,OUT,save

files=list((ROOT/'知识库').rglob('*.md'))+[ROOT/'README.md',ROOT/'素材库/官网素材入口.md',OUT/'官网资料预览.html',OUT/'采集报告.md']
failures=[];count=0
for p in files:
    content=p.read_text(encoding='utf-8')
    if p.suffix=='.html':
        d=html.fromstring(content)
        refs=d.xpath('//@href|//@src')
    else:refs=re.findall(r'\]\(([^)]+)\)',content)
    for ref in refs:
        if urlsplit(ref).scheme or ref.startswith('#'):continue
        count+=1
        if not (p.parent/unquote(ref)).exists():failures.append(str(p)+' -> '+ref)
assert not failures,failures
initial=json.loads((ROOT/'素材库/原件清单.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in initial)
products=json.loads((ROOT/'知识库/官网/产品目录.json').read_text(encoding='utf-8'))
assert len(products)==40
assert all(p['current_api_amount_if_frontend_priced'] is None for p in products if p['price_status'].startswith('询价'))
missing_categories=[p['url'] for p in products if not p['categories']]
assert not [p for p in files if '\ufffd' in p.read_text(encoding='utf-8')]
media=json.loads((OUT/'公开媒体清单.json').read_text(encoding='utf-8'))
assert len(media['items'])==180
audit=json.loads((OUT/'媒体分页核对.json').read_text(encoding='utf-8'))
assert audit['unique_returned_after_audit']==len(media['items'])
assert not audit['new_ids']
assert len(set(p['wp_id'] for p in products))==40
report=json.loads((OUT/'采集校验.json').read_text(encoding='utf-8'))
report['generated_local_link_checks']={'count':count,'failures':[]}
report['original_chat_sha256_unchanged']='63/63'
report['enquiry_price_check']='14个明确询价和5个未提供价格条目的规范化成交价格留空，未按API 0标为免费'
report['product_category_coverage']={'provided':len(products)-len(missing_categories),'missing':missing_categories,'note':'同时保留前台分类文本与公开API分类；缺失值留空，不推定分类'}
report['unique_original_source_urls']=len(set(m['source_url'] for m in media['items']))
report['unique_original_urls_downloaded']=len(set(m['url'] for m in json.loads((OUT/'媒体原件索引.json').read_text(encoding='utf-8')) if m['status']==200))
report['video_probe']='3/3 MP4均由ffprobe识别，720p H264/AAC，时长见视频文件校验.json'
report['media_api_total_discrepancy']={'header_reported_total':media['reported_total'],'unique_records_returned':len(media['items']),'not_returned_by_public_api':media['reported_total']-len(media['items']),'pagination_rechecked':'per_page=100与20均返回同一组180个ID；未猜测缺失记录内容或访问受限内容'}
save(OUT/'采集校验.json',report)
preview=json.loads((OUT/'本地预览浏览器验收.json').read_text(encoding='utf-8'))
report['local_preview_browser_check']={'filter_scenarios':len(preview['checks']),'images_decoded':preview['image_decode']['count'],'video_metadata_loaded':len(preview['videos']),'status':'通过；未完成截图布局验收，截图接口超时'}
save(OUT/'采集校验.json',report)
print(json.dumps({'local_links_checked':count,'chat_originals_unchanged':len(initial),'enquiry_price_check':'passed','categories_provided':len(products)-len(missing_categories),'unique_media_original_urls':report['unique_original_source_urls'],'unique_media_original_urls_downloaded':report['unique_original_urls_downloaded'],'browser_checks':report['local_preview_browser_check']},ensure_ascii=False,indent=2))
