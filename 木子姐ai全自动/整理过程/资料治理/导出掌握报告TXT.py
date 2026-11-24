# -*- coding: utf-8 -*-
"""把现有完整Markdown报告导出为便于记事本阅读的UTF-8纯文本，不改原报告。"""
from pathlib import Path
from urllib.parse import unquote
import re

root=Path(__file__).resolve().parents[2]
source=root/'知识库/知识与素材掌握情况报告-2026-11-24.md'
dest=source.with_suffix('.txt')
if dest.exists():
    raise SystemExit('TXT已存在，未覆盖：'+str(dest))
original=source.read_text(encoding='utf-8')

def readable_link(m):
    label,target=m.groups()
    if target.startswith(('https://','http://')):
        return label+'（'+target+'）'
    return label+'（项目相对路径：'+unquote(target)+'）'

text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',readable_link,original)
lines=[]
for line in text.splitlines():
    if re.match(r'^\|\s*:?-{3,}',line):
        continue
    line=re.sub(r'^#{1,6}\s+','',line)
    line=line.replace('**','').replace('`','')
    if line.startswith('|') and line.endswith('|'):
        line=' ｜ '.join(cell.strip() for cell in line[1:-1].split('|'))
    lines.append(line)
output='\r\n'.join(lines).rstrip()+'\r\n'
dest.write_bytes(output.encode('utf-8-sig'))
saved=dest.read_text(encoding='utf-8-sig')
assert '\ufffd' not in saved
products=__import__('json').loads((root/'知识库/官网/产品目录.json').read_text(encoding='utf-8'))
assert len(products)==40 and all(p['name'] in saved for p in products)
assert '附录 官网四十个条目全表' in saved
assert source.read_text(encoding='utf-8')==original
print(str(dest))
print('验证通过：UTF-8 BOM、Windows换行、40/40商品及完整附录保留，原报告未修改。')
