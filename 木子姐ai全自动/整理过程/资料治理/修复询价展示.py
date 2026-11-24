# -*- coding: utf-8 -*-
"""只修复已有price_status明确为询价且price_display为空的派生结果，逐文件备份并核对基线。"""
from pathlib import Path
import json,re,csv,io,hashlib,shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).parent
BASE=json.loads((HERE/'整理前基线.json').read_text(encoding='utf-8'))
baseline={x['path']:x for x in BASE['files']}
changes={}
def read(rel):return (ROOT/rel).read_text(encoding='utf-8-sig')
def put(rel,new):
    if read(rel)!=new:changes[rel]=new

path='知识库/官网/产品目录.json'
products=json.loads(read(path))
enquiry=[p for p in products if p['price_status'].startswith('询价')]
assert len(enquiry)==19
page_rows=json.loads(read('官网资料/2026-11-24/页面清单.json'))
explicit_count=0
for p in enquiry:
    assert p['current_api_amount_if_frontend_priced'] is None
    source=next(x for x in page_rows if x['url']==p['url'])
    assert not source['product']['price_text']
    explicit='Enquire about this product' in source['text_en']
    explicit_count+=explicit
    assert p['price_display'] in ('','询价 / Enquire about this product')
    p['price_display']='询价 / Enquire about this product' if explicit else '未提供价格（疑似模板）'
    if not explicit:p['price_status']='未提供价格；疑似模板；API 0不表示免费'
assert explicit_count==14
put(path,json.dumps(products,ensure_ascii=False,indent=2))
for p in enquiry:
    rel='知识库/官网/'+p['knowledge_path'];old=read(rel)
    new=old.replace('- 页面价格：；页面币种SGD。','- 页面价格：'+p['price_display']+'；页面币种SGD。')
    new=new.replace('前台显示：。接口价格字段','前台显示：'+p['price_display']+'。接口价格字段')
    put(rel,new)
rel='知识库/官网/产品索引.md';old=read(rel)
new=old.replace('前台有价格40个，询价0个','前台有价格21个，明确询价14个，未提供价格5个')
for p in enquiry:
    new=re.sub(r'(?m)^(\| '+re.escape(p['id'])+r' \|[^\n]*?\|[^\n]*?\|)\s*\|',lambda m:m.group(1)+' '+p['price_display']+' |',new)
put(rel,new)
rel='知识库/官网/产品价格快照.csv'
reader=csv.DictReader(io.StringIO(read(rel)));fields=reader.fieldnames;rows=list(reader)
ids={p['id'] for p in enquiry}
for row in rows:
    if row['id'] in ids:
        product=next(p for p in enquiry if p['id']==row['id'])
        row['price_display']=product['price_display'];row['price_status']=product['price_status']
s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows(rows)
put(rel,'\ufeff'+s.getvalue())
rel='官网资料/2026-11-24/官网资料预览.html';old=read(rel)
repaired=[]
def fix(m):
    block=m.group(0)
    if 'data-kind="商品"' not in block:return block
    match=next((p for p in enquiry if p['id']+' · ' in block),None)
    if match:
        block=block.replace('<p> · SGD ·','<p>'+match['price_display']+' · SGD ·')
        block=block.replace(' · sgd ·',match['price_display'].lower()+' · sgd ·')
        repaired.append(match['id'])
    return block
new=re.sub(r'<article\b[^>]*>[\s\S]*?</article>',fix,old)
assert len(repaired)==19
put(rel,new)
rel='官网资料/2026-11-24/采集校验.json';report=json.loads(read(rel))
report['products_with_frontend_price']=21;report['products_enquiry_only']=14;report['products_price_unprovided']=5
report['enquiry_price_check']='14个明确询价和5个未提供价格条目的规范化成交价格留空；API 0不作为免费'
report['price_display_correction']='本轮资料治理依据price_status及保存的官网正文修正空白显示；不改变原始网页/接口价格'
put(rel,json.dumps(report,ensure_ascii=False,indent=2))
rel='整理过程/官网采集/生成官网资料库.py';old=read(rel)
new=old.replace("else compact(clean)\n","else (compact(clean) or item['price_display'])\n")
new=new.replace("sum(r['price_display']!='询价 / Enquire about this product' for r in products)","sum(bool(r['frontend_price_raw']) for r in products)")
new=new.replace("sum(r['price_display']=='询价 / Enquire about this product' for r in products)","sum(r['price_status'].startswith('询价') for r in products)")
new=new.replace('sum(p["price_display"]!="询价 / Enquire about this product" for p in products)','sum(bool(p["frontend_price_raw"]) for p in products)')
new=new.replace('sum(p["price_display"]=="询价 / Enquire about this product" for p in products)','sum(p["price_status"].startswith("询价") for p in products)')
anchor="        item['frontend_category_text']=p['categories']"
new=new.replace(anchor,"        if no_price and 'Enquire about this product' not in p['text_en']:\n            item['price_display']='未提供价格（疑似模板）' if candidate else '未提供价格'\n            item['price_status']='未提供价格；API 0不表示免费'\n"+anchor)
put(rel,new)
rel='整理过程/官网采集/校验官网资料.py';old=read(rel)
put(rel,old.replace('19个询价商品的规范化成交价格均留空，未按API 0标为免费','14个明确询价和5个未提供价格条目的规范化成交价格留空，未按API 0标为免费'))

plan=[]
for rel,new in changes.items():
    current=(ROOT/rel).read_bytes()
    assert hashlib.sha256(current).hexdigest()==baseline[rel]['sha256'],f'检测到基线后改动，不覆盖：{rel}'
    plan.append({'path':rel,'before_sha256':hashlib.sha256(current).hexdigest(),'after_sha256':hashlib.sha256(new.encode('utf-8')).hexdigest(),'reason':'修复询价空白/派生统计；原始价格及来源不变'})
(HERE/'询价修复清单.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for rel,new in changes.items():
    backup=HERE/'修复前备份'/rel
    if backup.exists():raise RuntimeError('备份已存在，不覆盖：'+str(backup))
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,backup)
    (ROOT/rel).write_bytes(new.encode('utf-8'))
print(json.dumps({'explicit_enquiry':explicit_count,'price_unprovided':19-explicit_count,'changed_files':len(plan),'backup':'整理过程/资料治理/修复前备份'},ensure_ascii=False))
