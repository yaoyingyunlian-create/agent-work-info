from pathlib import Path
import subprocess,json,math
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent.parent
out=root/'整理成果/素材库/视频复核'
out.mkdir(parents=True,exist_ok=True)
rows=json.loads((root/'整理成果/清单/原始文件清单.json').read_text(encoding='utf-8'))
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
for r in rows:
    if r['类型']!='mp4':continue
    sid=r['id']; folder=out/sid; folder.mkdir(exist_ok=True)
    src=root/r['原始路径']
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-vf','fps=1:start_time=0,scale=400:-1','-q:v','3',str(folder/'frame_%03d.jpg')],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-vn','-ar','16000','-ac','1',str(folder/f'{sid}.wav')],check=True)
    frames=sorted(folder.glob('frame_*.jpg'))
    for a in range(0,len(frames),16):
        sheet=Image.new('RGB',(1600,1280),'#eeeeee'); d=ImageDraw.Draw(sheet)
        for j,p in enumerate(frames[a:a+16]):
            im=Image.open(p);im.thumbnail((390,285));x=(j%4)*400;y=(j//4)*320
            sheet.paste(im,(x+(400-im.width)//2,y+28));d.text((x+8,y+3),f'{sid} {a+j:03d}s',font=font,fill='black')
        sheet.save(folder/f'时间线_{a//16+1:02d}.jpg',quality=90)
    print(sid,len(frames),'seconds',flush=True)
