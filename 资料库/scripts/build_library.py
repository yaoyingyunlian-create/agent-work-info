from pathlib import Path
import hashlib, json, csv, shutil, subprocess, html, argparse, os
from collections import Counter
from PIL import Image, ImageOps, ImageDraw, ImageFont
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='导入资料并重建预览，默认使用项目内原始资料')
parser.add_argument('--source', type=Path, default=ROOT/'原始资料')
SOURCE=parser.parse_args().source.resolve()
if not SOURCE.is_dir(): raise SystemExit('来源目录不存在')
if SOURCE != (ROOT/'原始资料').resolve() and (ROOT.resolve().is_relative_to(SOURCE) or SOURCE.is_relative_to(ROOT.resolve())):
    raise SystemExit('外部来源不可包含项目目录或位于资料库内部')
poppler=os.environ.get('PDFTOPPM') or shutil.which('pdftoppm')
for tool in ['ffmpeg','ffprobe']:
    if not shutil.which(tool): raise SystemExit(f'缺少 {tool}，请安装并加入 PATH')
if not poppler: raise SystemExit('缺少 pdftoppm，请安装 Poppler 并加入 PATH，或设置 PDFTOPPM')
for name in ['原始资料','素材库/缩略图','素材库/总览','知识库/PDF逐页','索引']:
    (ROOT/name).mkdir(parents=True,exist_ok=True)
try: font=ImageFont.truetype(os.environ.get('LIBRARY_FONT','DejaVuSans.ttf'),16)
except OSError: font=ImageFont.load_default()
manifest=ROOT/'索引/文件清单.json'
previous=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
ids={r['name']:r['id'] for r in previous}
next_id=max((int(r['id'][1:]) for r in previous),default=0)+1
for candidate in SOURCE.rglob('*'):
    if not candidate.is_file(): continue
    target=ROOT/'原始资料'/candidate.relative_to(SOURCE)
    if target.exists() and hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(candidate.read_bytes()).digest():
        raise SystemExit(f'同名文件内容不同，已停止导入: {candidate.name}')
for candidate in SOURCE.rglob('*'):
    if candidate.is_file():
        target=ROOT/'原始资料'/candidate.relative_to(SOURCE)
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists(): shutil.copy2(candidate,target)
SOURCE=(ROOT/'原始资料').resolve()
rows=[]; seen={}; errors=[]
for i,p in enumerate(sorted(SOURCE.rglob('*')),1):
    if not p.is_file(): continue
    rel=p.relative_to(SOURCE); dest=ROOT/'原始资料'/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if not dest.exists(): shutil.copy2(p,dest)
    if hashlib.sha256(dest.read_bytes()).hexdigest()!=digest: raise RuntimeError(str(dest))
    kind={'.jpg':'图片','.mp4':'视频','.pdf':'文档','.txt':'文字'}.get(p.suffix.lower(),'其他')
    if rel.as_posix() in ids: rid=ids[rel.as_posix()]
    else: rid=f'A{next_id:04d}'; next_id+=1
    duplicate=seen.get(digest,''); seen.setdefault(digest,rid)
    row=dict(id=rid,name=rel.as_posix(),kind=kind,bytes=p.stat().st_size,sha256=digest,duplicate_of=duplicate,path=dest.relative_to(ROOT).as_posix(),width='',height='',duration='',preview='',status='已归档，待语义标注')
    try:
        if kind=='图片':
            with Image.open(p) as im:
                im=ImageOps.exif_transpose(im).convert('RGB'); row.update(width=im.width,height=im.height)
                im.thumbnail((400,300)); thumb=ROOT/'素材库/缩略图'/f'{rid}.jpg'; im.save(thumb,quality=85);row['preview']=thumb.relative_to(ROOT).as_posix()
        elif kind=='视频':
            probe=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)],capture_output=True,encoding='utf-8',check=True)
            meta=json.loads(probe.stdout); meta['format']['filename']=dest.relative_to(ROOT).as_posix(); v=next(x for x in meta['streams'] if x['codec_type']=='video'); duration=float(meta['format']['duration'])
            row.update(width=v['width'],height=v['height'],duration=round(duration,2))
            (ROOT/'索引'/f'{rid}-视频信息.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
            frames=[]
            for n,t in enumerate([duration*.15,duration*.5,duration*.85]):
                out=ROOT/'素材库/缩略图'/f'{rid}-{n}.jpg'
                subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(p),'-frames:v','1','-vf','scale=400:-2',str(out)],capture_output=True,check=True)
                frames.append(out)
            row['preview']=frames[0].relative_to(ROOT).as_posix()
    except Exception as exc: errors.append({'id':rid,'error':str(exc)});row['status']='检查异常'
    rows.append(row)

pdf=PdfReader(str(SOURCE/'8种不同产品介绍.pdf'))
texts=[]
for n,page in enumerate(pdf.pages,1):
    text=page.extract_text() or ''
    if n==1: text='字体编码异常，本页不纳入文本检索；请查看 PDF逐页/page-01.png。'
    texts.append(f'## 第 {n} 页\n\n{text}')
(ROOT/'知识库/产品资料原文.md').write_text('# 8种不同产品介绍：PDF文本提取\n\n来源：原始资料/8种不同产品介绍.pdf；按页提取。第1页编码异常，第7、8页主要在图片内，请对照逐页图。以下为客户旧版资料，不代表已核实事实或批准发布文案。\n\n'+'\n\n'.join(texts),encoding='utf-8')
subprocess.run([poppler,'-scale-to','1200','-png',str(SOURCE/'8种不同产品介绍.pdf'),str(ROOT/'知识库/PDF逐页/page')],capture_output=True,check=True)

def sheet(items,name,cols=5,w=220,h=200):
    canvas=Image.new('RGB',(cols*w,((len(items)+cols-1)//cols)*h),'#eeeeee');d=ImageDraw.Draw(canvas)
    for n,(label,path) in enumerate(items):
        with Image.open(path) as im:
            im=im.convert('RGB');im.thumbnail((w-10,h-32));x=(n%cols)*w;y=(n//cols)*h
            canvas.paste(im,(x+(w-im.width)//2,y));d.text((x+6,y+h-27),label,font=font,fill='black')
    canvas.save(ROOT/'素材库/总览'/name,quality=90)
pics=[r for r in rows if r['kind']=='图片' and not r['duplicate_of'] and r['preview']]
for start in range(0,len(pics),40): sheet([(r['id'],ROOT/r['preview']) for r in pics[start:start+40]],f'图片-{start//40+1:02d}.jpg')
vids=[r for r in rows if r['kind']=='视频']
for r in vids: sheet([(f"{r['id']} {t}",ROOT/'素材库/缩略图'/f"{r['id']}-{n}.jpg") for n,t in enumerate(['15%','50%','85%'])],f"视频-{r['id']}.jpg",cols=3,w=350,h=320)
sheet([(f'PDF {n+1}',p) for n,p in enumerate(sorted((ROOT/'知识库/PDF逐页').glob('*.png')))],'PDF总览.jpg',cols=4,w=360,h=300)
(ROOT/'索引/文件清单.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'索引/文件清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
summary={'files':len(rows),'types':dict(Counter(r['kind'] for r in rows)),'bytes':sum(r['bytes'] for r in rows),'unique':len(seen),'duplicate_copies':sum(bool(r['duplicate_of']) for r in rows),'pdf_pages':len(pdf.pages),'errors':errors,'copy_hash_verified':True}
(ROOT/'索引/验证结果.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
from library import render
render()
print(json.dumps(summary,ensure_ascii=False))
if errors: raise SystemExit('部分媒体处理失败，请检查索引/验证结果.json')
