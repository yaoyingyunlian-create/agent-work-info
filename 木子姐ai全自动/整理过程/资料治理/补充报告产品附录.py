# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.parse import quote
import json

ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'知识库/知识与素材掌握情况报告-2026-11-24.md'
text=p.read_text(encoding='utf-8')
assert '| 序号 | 官网产品原名 |' not in text,'附录已存在，不重复写入'
products=json.loads((ROOT/'知识库/官网/产品目录.json').read_text(encoding='utf-8'))
assert len(products)==40
lines=['| 序号 | 官网产品原名 | 价格记录 | 资料深度 |','| --- | --- | --- | --- |']
for i,r in enumerate(products,1):
    price=r['price_display'].replace('（疑似模板）','')
    depth='详细产品说明与独立成分字段' if r['inci_source_text'] else '历史分类；原说明为示例式文字' if r['is_template_candidate'] else '套装概述，未列完整内含SKU' if r['slug']=='hydration-skin-care-kit' else '产品图/归属与询价介绍，详细参数未提供'
    if not r['images']:depth+='；无商品主图'
    lines.append('| '+str(i)+' | ['+r['name'].replace('|','\\|')+']('+quote('官网/'+r['knowledge_path'],safe='/')+') | '+price+' | '+depth+' |')
p.write_text(text+'\n'.join(lines)+'\n',encoding='utf-8')
print('已补充40条商品全表及资料深度；未修改产品或素材原件。')
