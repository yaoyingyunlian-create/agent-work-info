# -*- coding: utf-8 -*-
from pathlib import Path
from collections import defaultdict
import hashlib,json,shutil,zipfile,xml.etree.ElementTree as ET,re
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(r'C:\Users\ZIQINGBO\Desktop\新建文件夹\木子姐ai全自动\20261125')
RAW=ROOT/'原始资料/2026-11-25新增'
OUT=ROOT/'素材库/新增20261125'
WORK=Path(__file__).resolve().parent
OUT.mkdir(parents=True,exist_ok=True)
manifest=OUT/'原件清单.json'
assert not manifest.exists(),'批次已存在，停止以防覆盖'
old=defaultdict(list)
baseline=[]
for p in ROOT.rglob('*'):
 if not p.is_file() or WORK in p.parents:continue
 h=hashlib.sha256(p.read_bytes()).hexdigest();name=p.relative_to(ROOT).as_posix()
 old[h].append(name);baseline.append({'path':name,'sha256':h})
(WORK/'导入前基线.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[]
for i,p in enumerate(sorted(x for x in SOURCE.rglob('*') if x.is_file()),1):
 rel=p.relative_to(SOURCE);dest=RAW/rel
 assert not dest.exists(),'目标原件存在，不覆盖：'+str(dest)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 h=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==h
 r={'id':f'N1125-{i:03}','path':dest.relative_to(ROOT).as_posix(),'source_relative':rel.as_posix(),'sha256':h,'bytes':p.stat().st_size,'type':p.suffix.lower(),'batch':'20261125','imported_at':'2026-11-26','identical_existing_paths':old[h]}
 if p.suffix.lower() in ['.png','.jpg','.jpeg']:
  with Image.open(p) as im:r.update(width=im.width,height=im.height)
 rows.append(r)
manifest.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
images=[r for r in rows if 'width' in r]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
for start in range(0,len(images),6):
 sheet=Image.new('RGB',(1500,1800),'white');draw=ImageDraw.Draw(sheet)
 for j,r in enumerate(images[start:start+6]):
  x=j%3*500;y=j//3*900
  with Image.open(ROOT/r['path']) as im:
   im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((490,830));sheet.paste(im,(x+(500-im.width)//2,y+55))
  draw.text((x+7,y+3),r['id'],fill='black',font=font)
  draw.text((x+7,y+27),r['source_relative'][-27:],fill='black',font=font)
 sheet.save(WORK/f'图片联系表-{start//6+1:02}.jpg',quality=90)
ppt=next(RAW.glob('*.pptx'))
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','r':'http://schemas.openxmlformats.org/package/2006/relationships'}
slides=[]
with zipfile.ZipFile(ppt) as z:
 for name in sorted([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)],key=lambda n:int(re.search(r'slide(\d+)',n).group(1))):
  n=int(re.search(r'slide(\d+)',name).group(1));d=ET.fromstring(z.read(name));texts=[''.join(e.itertext()) for e in d.findall('.//a:t',ns)]
  relname=f'ppt/slides/_rels/slide{n}.xml.rels'
  relations=[]
  if relname in z.namelist():relations=[dict(e.attrib) for e in ET.fromstring(z.read(relname))]
  slides.append({'page':n,'text':'\n'.join(texts),'relationships':relations})
 mediadir=OUT/'PPT嵌入素材';mediadir.mkdir(exist_ok=True)
 embedded=[]
 for name in z.namelist():
  if not name.startswith('ppt/media/') or name.endswith('/'):continue
  p=mediadir/Path(name).name;p.write_bytes(z.read(name))
  embedded.append({'path':p.relative_to(ROOT).as_posix(),'ppt_member':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':ppt.relative_to(ROOT).as_posix()})
(OUT/'PPT逐页文字.json').write_text(json.dumps(slides,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'PPT嵌入素材清单.json').write_text(json.dumps(embedded,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'粉之密PPT逐页原文.txt').write_text('\n\n'.join(f'【第{s["page"]}页】\n{s["text"] or "本页无可提取文字，需看页面图"}' for s in slides),encoding='utf-8-sig')
print(json.dumps({'original_files':len(rows),'images':len(images),'ppt_slides':len(slides),'embedded_media':len(embedded),'old_exact_duplicates':sum(bool(r['identical_existing_paths']) for r in rows),'image_ids':[(r['id'],r['source_relative'],r['width'],r['height']) for r in images]},ensure_ascii=False,indent=2))
