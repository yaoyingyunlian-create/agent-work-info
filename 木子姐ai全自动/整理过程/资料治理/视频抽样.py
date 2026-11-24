# -*- coding: utf-8 -*-
from pathlib import Path
import subprocess,json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'视频抽样'
OUT.mkdir(exist_ok=True)
web=ROOT/'官网资料/2026-11-24'
videos=json.loads((web/'视频文件校验.json').read_text(encoding='utf-8'))
assets=json.loads((web/'资源清单.json').read_text(encoding='utf-8'))
sheet=Image.new('RGB',(1500,1000),'white');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
record=[]
for row,v in enumerate(videos):
    a=next(x for x in assets if x['url']==v['url'])
    duration=float(v['probe']['format']['duration'])
    images=[]
    for col,frac in enumerate([.1,.5,.9]):
        p=OUT/f'视频{row+1}-{col+1}.jpg'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(duration*frac),'-i',str(web/a['path']),'-frames:v','1','-q:v','3','-y',str(p)],check=True,capture_output=True)
        with Image.open(p) as im:
            im.thumbnail((490,280));sheet.paste(im,(col*500+5,row*330+40))
        draw.text((col*500+5,row*330+5),f'视频{row+1} · {duration*frac:.1f}秒',font=font,fill='black')
        images.append({'path':p.relative_to(ROOT).as_posix(),'time_seconds':round(duration*frac,2)})
    record.append({'url':v['url'],'path':'官网资料/2026-11-24/'+a['path'],'duration':duration,'frames':images,'scope':'10%、50%、90%抽帧视觉采样；非全片审看，未转写音频'})
sheet.save(OUT/'视频联系表.jpg',quality=90)
(OUT/'抽样来源.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('已生成3段视频共9帧的抽样联系表，未修改视频原件。')
