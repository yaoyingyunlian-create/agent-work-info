from pathlib import Path
import hashlib, json, csv, subprocess
from PIL import Image, ImageOps, ImageDraw, ImageFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '知识库和素材库'
OUT = ROOT / '整理成果'
for folder in ['知识库/来源全文', '素材库/预览', '清单']:
    (OUT / folder).mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
rows = []
thumbs = []
for n, p in enumerate(sorted(SRC.iterdir()), 1):
    if not p.is_file(): continue
    sid = f'S{n:03}'
    row = dict(id=sid, 文件名=p.name, 原始路径=str(p.relative_to(ROOT)), 字节=p.stat().st_size,
               sha256=hashlib.sha256(p.read_bytes()).hexdigest(), 类型=p.suffix[1:], 信息='', 内容状态='待核对', 授权状态='待确认')
    if p.suffix.lower() == '.pdf':
        reader = PdfReader(p)
        texts = [page.extract_text() or '' for page in reader.pages]
        (OUT / '知识库/来源全文' / f'{sid}_{p.stem}.txt').write_text('\n\n'.join(f'【第{i+1}页】\n{t}' for i,t in enumerate(texts)), encoding='utf-8')
        row['信息'] = f'{len(texts)}页；提取{sum(map(len,texts))}字符'
        row['内容状态'] = '已提取文本，页面内容待核对' if any(t.strip() for t in texts) else '图片型PDF，无可提取文本；关键内容见目视摘录'
        subprocess.run(['pdftoppm','-f','1','-singlefile','-scale-to','1000','-png',str(p),str(OUT / '素材库/预览' / sid)],check=True,capture_output=True)
        thumbs.append((sid, OUT / '素材库/预览' / f'{sid}.png'))
    elif p.suffix.lower() == '.txt':
        (OUT / '知识库/来源全文' / f'{sid}_{p.name}').write_text(p.read_text(encoding='utf-8-sig'), encoding='utf-8')
        row['内容状态'] = '已读取，二次总结材料'
    elif p.suffix.lower() == '.jpg':
        im = ImageOps.exif_transpose(Image.open(p))
        row['信息'] = f'{im.width}×{im.height}'
        im.thumbnail((700,900))
        dst = OUT / '素材库/预览' / f'{sid}.jpg'
        im.save(dst, quality=85)
        thumbs.append((sid,dst))
    elif p.suffix.lower() == '.mp4':
        meta = json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-show_streams','-of','json',str(p)],encoding='utf-8'))
        v = next(s for s in meta['streams'] if s['codec_type']=='video')
        duration = float(meta['format']['duration'])
        row['信息'] = f"{v['width']}×{v['height']}；{duration:.2f}秒；音轨{'有' if any(s['codec_type']=='audio' for s in meta['streams']) else '无'}"
        for i,frac in enumerate([0.15,0.5,0.85],1):
            dst = OUT / '素材库/预览' / f'{sid}_{i}.jpg'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(duration*frac),'-i',str(p),'-frames:v','1','-vf','scale=600:-1',str(dst)],check=True)
            thumbs.append((f'{sid}-{i}',dst))
        row['内容状态'] = '已提取元数据与三帧预览，未逐帧审看或转写音频'
    rows.append(row)
for k in range(0,len(thumbs),9):
    batch = thumbs[k:k+9]
    sheet = Image.new('RGB',(1050,1140),'#eeeeee')
    draw = ImageDraw.Draw(sheet)
    for j,(label,path) in enumerate(batch):
        im = Image.open(path).convert('RGB'); im.thumbnail((330,330))
        x,y=(j%3)*350,(j//3)*380
        sheet.paste(im,(x+(350-im.width)//2,y+30))
        draw.text((x+10,y+5),label,font=font,fill='black')
    sheet.save(OUT / '素材库' / f'总览_{k//9+1}.jpg',quality=90)
(OUT / '清单/原始文件清单.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT / '清单/原始文件清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
print(json.dumps(rows,ensure_ascii=False,indent=2))
