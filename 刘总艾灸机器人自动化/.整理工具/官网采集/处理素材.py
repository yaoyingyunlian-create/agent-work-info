from pathlib import Path
import json,subprocess,hashlib
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'整理成果/素材库/官网素材/2026-11-27'
rows=json.loads((BASE/'素材清单.json').read_text(encoding='utf-8'))
for d in ['预览','OCR输入','OCR']: (BASE/d).mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
thumbs=[]
for r in rows:
    if r['status']!='downloaded':continue
    p=ROOT/r['local_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    sid=r['id']
    if p.suffix.lower() in ['.jpg','.png']:
        im=ImageOps.exif_transpose(Image.open(p)).convert('RGB');r['width'],r['height']=im.size
        im.thumbnail((2400,2400));im.save(BASE/'OCR输入'/f'{sid}.png')
        im.thumbnail((600,650));im.save(BASE/'预览'/f'{sid}.jpg',quality=90);thumbs.append((sid,BASE/'预览'/f'{sid}.jpg'))
    elif p.suffix.lower()=='.mp4':
        meta=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-show_streams','-of','json',str(p)],encoding='utf-8'))
        v=next(s for s in meta['streams'] if s['codec_type']=='video');duration=float(meta['format']['duration'])
        r.update(duration=duration,width=v['width'],height=v['height'],has_audio=any(s['codec_type']=='audio' for s in meta['streams']))
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(p),'-f','null','-'],check=True,capture_output=True)
        shots=[]
        for i,t in enumerate([0,3,6,9,12,duration-.1]):
            dst=BASE/'预览'/f'{sid}_{i}.jpg';subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(p),'-frames:v','1','-vf','scale=600:-1',str(dst)],check=True,capture_output=True);shots.append((f'{sid} {t:.1f}s',dst))
        canvas=Image.new('RGB',(1200,1140),'#eee');draw=ImageDraw.Draw(canvas)
        for i,(label,path) in enumerate(shots):
            im=Image.open(path);im.thumbnail((580,340));x=i%2*600;y=i//2*380;canvas.paste(im,(x+(600-im.width)//2,y+30));draw.text((x+8,y+3),label,font=font,fill='black')
        canvas.save(BASE/'预览'/f'{sid}_视频总览.jpg',quality=90)
        if r['has_audio']:subprocess.run(['ffmpeg','-v','error','-y','-i',str(p),'-vn','-ar','16000','-ac','1',str(BASE/'预览'/f'{sid}.wav')],check=True,capture_output=True)
for start in range(0,len(thumbs),9):
    canvas=Image.new('RGB',(1200,1200),'#eee');draw=ImageDraw.Draw(canvas)
    for j,(label,path) in enumerate(thumbs[start:start+9]):
        im=Image.open(path);im.thumbnail((380,360));x=j%3*400;y=j//3*400;canvas.paste(im,(x+(400-im.width)//2,y+30));draw.text((x+8,y+3),label,font=font,fill='black')
    canvas.save(BASE/'预览'/f'图片总览_{start//9+1}.jpg',quality=90)
(BASE/'素材清单.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS',len(thumbs),'images',sum('duration'in r for r in rows),'videos')
