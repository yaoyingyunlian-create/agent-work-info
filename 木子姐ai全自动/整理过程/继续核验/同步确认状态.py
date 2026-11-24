# -*- coding: utf-8 -*-
from pathlib import Path
import json,hashlib,shutil,csv,io

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
products_path=ROOT/'知识库/官网/产品目录.json'
products=json.loads(products_path.read_text(encoding='utf-8'))
replacements={'LA REINE品牌命名商品，未确认实际可售范围':'用户已确认材料 · LA REINE品牌命名商品','疑似主题模板商品，待业务确认':'用户已确认材料 · 保留原模板候选标记'}
changes={}
for p in products:
    p['classification_before_user_confirmation']=p['classification']
    p['classification']=replacements.get(p['classification'],p['classification'])
    p['material_confirmation']={'status':'用户已确认材料','confirmed_at':'2026-11-24','record':'知识库/资料确认记录.md'}
changes['知识库/官网/产品目录.json']=json.dumps(products,ensure_ascii=False,indent=2)
for p in products:
    name='知识库/官网/'+p['knowledge_path']
    s=(ROOT/name).read_text(encoding='utf-8')
    s=s.replace('- 资料状态：'+p['classification_before_user_confirmation'],'- 资料状态：'+p['classification'])
    s=s.replace('- 真实性边界：以下成分、特色及效果均为官网表述，未独立验证。','- 资料确认：用户已确认这批材料；以下原文保留来源及采集日期，技术核验不改写业务表述。')
    changes[name]=s
name='知识库/官网/产品索引.md';s=(ROOT/name).read_text(encoding='utf-8')
s=s.replace('所有条目保留来源，疑似模板不删除也不自动视作实际经营商品。','所有条目保留来源，材料已获用户确认；旧模板候选标记仅为整理历史。')
s=s.replace('15个因命名含主题示例特征标记待确认','15个保留此前的模板候选标记')
for old,new in replacements.items():s=s.replace(old,new)
changes[name]=s
name='官网资料/2026-11-24/官网资料预览.html';s=(ROOT/name).read_text(encoding='utf-8')
for old,new in replacements.items():s=s.replace(old,new).replace(old.lower(),new.lower())
s=s.replace('待确认模板','原模板候选')
s=s.replace('官网公开媒体库包含历史素材、模板和字体，并非全部代表当前在售商品；疑似模板已单独标记。官网宣传不等于已核验功效。','这批材料已经用户确认；官网公开媒体库的历史、模板候选及字体分类保留用于检索。具体未提供字段与版本差异如实记录。')
changes[name]=s
name='知识库/官网/产品价格快照.csv';reader=csv.DictReader(io.StringIO((ROOT/name).read_text(encoding='utf-8-sig')));fields=reader.fieldnames;rows=list(reader)
by_id={p['id']:p for p in products}
for r in rows:r['classification']=by_id[r['id']]['classification']
f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows);changes[name]='\ufeff'+f.getvalue()
plan=[]
for name,value in changes.items():
    before=(ROOT/name).read_bytes();after=value.encode('utf-8')
    if before==after:continue
    backup=OUT/'确认状态更新前'/name
    if backup.exists():raise RuntimeError('备份存在，拒绝覆盖：'+name)
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,backup)
    (ROOT/name).write_bytes(after)
    plan.append({'path':name,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),'reason':'记录用户确认；价格、原文来源与原件内容不变'})
(OUT/'确认状态变更.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'updated_files':len(plan),'original_sources_changed':False},ensure_ascii=False))
