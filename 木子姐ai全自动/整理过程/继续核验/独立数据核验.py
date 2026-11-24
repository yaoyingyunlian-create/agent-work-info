# -*- coding: utf-8 -*-
from pathlib import Path
from collections import Counter
import json,csv,hashlib,subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
errors=[];checks={}
for name,manifest,base in [('微信原件','素材库/原件清单.json',ROOT),('官网资源','官网资料/2026-11-24/资源清单.json',ROOT/'官网资料/2026-11-24')]:
    n=0
    for r in load(manifest):
        if not r.get('path') or (name=='官网资源' and r.get('status')!=200):continue
        n+=1;p=base/r['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:errors.append({'check':name,'path':r['path']})
    checks[name]=n
products=load('知识库/官网/产品目录.json');rows=load('官网资料/2026-11-24/页面清单.json')
with (ROOT/'知识库/官网/产品价格快照.csv').open(encoding='utf-8-sig',newline='') as f:prices={r['id']:r for r in csv.DictReader(f)}
counts=Counter()
for p in products:
    source=next(r for r in rows if r['url']==p['url'])
    state='有价' if source['product']['price_text'] else '明确询价' if 'Enquire about this product' in source['text_en'] else '未提供价格'
    counts[state]+=1
    if prices[p['id']]['price_display']!=p['price_display']:errors.append({'check':'价格CSV','id':p['id']})
    if not source['product']['price_text'] and p['current_api_amount_if_frontend_priced'] is not None:errors.append({'check':'缺价被赋值','id':p['id']})
    if p.get('material_confirmation',{}).get('status')!='用户已确认材料':errors.append({'check':'确认状态','id':p['id']})
checks['价格来源独立重算']=dict(counts)
registry=load('素材库/全项目素材清单.json')
seen=set();video_probes=[]
for r in registry:
    if r['type']!='视频' or r['sha256'] in seen:continue
    seen.add(r['sha256'])
    result=subprocess.run(['ffmpeg','-hide_banner','-v','error','-xerror','-i',str(ROOT/r['path']),'-f','null','-'],capture_output=True,text=True,encoding='utf-8',timeout=90)
    video_probes.append({'path':r['path'],'whole_video_decode':'通过' if result.returncode==0 else '失败','exit_code':result.returncode})
    if result.returncode:errors.append({'check':'完整视频解码','path':r['path'],'error':result.stderr[:500]})
checks['完整视频解码']=video_probes
# 所有文档/素材登记当前哈希匹配，避免“文件尚在、索引已旧”的假通过。
for manifest in ['知识库/文档登记.json','素材库/全项目素材清单.json']:
    stale=[];n=0
    for r in load(manifest):
        p=ROOT/r['path'];n+=1
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:stale.append(r['path'])
    checks[manifest]={'rows':n,'stale':stale}
    errors.extend({'check':'登记哈希过期','path':p} for p in stale)
result={'review_date':'2026-11-24','checks':checks,'errors':errors,'scope':'独立重算来源价格、文件哈希和全片音视频解码；未更改原件，未转写或评价音频内容'}
(OUT/'独立数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)
