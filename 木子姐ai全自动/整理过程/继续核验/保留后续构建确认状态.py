# -*- coding: utf-8 -*-
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
name='整理过程/官网采集/生成官网资料库.py';p=ROOT/name;before=p.read_bytes();s=before.decode('utf-8')
old='        products.append(item)'
assert s.count(old)==1
replacement="""        confirmation_path=ROOT/'素材库/业务确认.json'
        if confirmation_path.exists():
            confirmation=json.loads(confirmation_path.read_text(encoding='utf-8'))
            item['classification_before_user_confirmation']=item['classification']
            item['classification']='用户已确认材料 · 保留原模板候选标记' if candidate else '用户已确认材料 · LA REINE品牌命名商品'
            item['material_confirmation']={'status':confirmation['status'],'confirmed_at':confirmation['confirmation_date'],'record':confirmation['record']}
        products.append(item)"""
s=s.replace(old,replacement)
s=s.replace("'待确认模板' if p['is_template_candidate']", "'原模板候选' if p['is_template_candidate']")
s=s.replace('<option>待确认模板</option>','<option>原模板候选</option>')
# 保留模板标记的原始字段，但在当前构建中不再把它当成材料未确认。
needle="    (OUT/'官网资料预览.html').write_text(template.replace('STATS',counts).replace('CARDS','\\n'.join(cards)),encoding='utf-8')"
assert needle in s
addition="""    if (ROOT/'素材库/业务确认.json').exists():
        template=template.replace('官网公开媒体库包含历史素材、模板和字体，并非全部代表当前在售商品；疑似模板已单独标记。官网宣传不等于已核验功效。','这批材料已经用户确认；官网公开媒体库的历史、模板候选及字体分类保留用于检索。具体未提供字段与版本差异如实记录。')
"""
s=s.replace(needle,addition+needle)
compile(s,str(p),'exec')
backup=OUT/'确认状态更新前'/name;assert not backup.exists();backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
p.write_bytes(s.encode('utf-8'))
plan_path=OUT/'确认状态变更.json';plan=json.loads(plan_path.read_text(encoding='utf-8'))
plan.append({'path':name,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reason':'后续构建读取用户确认记录，不恢复整批待确认状态；仅编译字符串检查，未运行重建'})
plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('已补充后续构建的用户确认状态读取；未运行批量重建。')
