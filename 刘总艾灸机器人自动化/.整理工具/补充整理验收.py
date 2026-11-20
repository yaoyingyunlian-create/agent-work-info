from pathlib import Path
import json,subprocess,hashlib,csv,re,wave
root=Path(__file__).resolve().parent.parent
out=root/'整理成果';base=out/'素材库/视频复核'
rows=json.loads((out/'清单/原始文件清单.json').read_text(encoding='utf-8'))
metrics=[]
for r in rows:
    src=root/r['原始路径']
    assert hashlib.sha256(src.read_bytes()).hexdigest()==r['sha256']
    if r['类型']!='mp4':continue
    sid=r['id'];folder=base/sid
    check=subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(src),'-f','null','-'],capture_output=True)
    assert check.returncode==0,check.stderr
    subprocess.run(['ffmpeg','-v','error','-y','-sseof','-0.05','-i',str(src),'-frames:v','1','-vf','scale=600:-1',str(folder/'末帧.jpg')],check=True)
    with wave.open(str(folder/(sid+'.wav')),'rb') as w: dur=w.getnframes()/w.getframerate()
    first=json.loads((folder/(sid+'_转写.json')).read_text(encoding='utf-8'))
    second=json.loads((folder/(sid+'_增强复查.json')).read_text(encoding='utf-8'))
    for data in [first,second]:
        assert all(0<=s['start']<s['end']<=dur+.2 for s in data['segments'])
    # 原始机器候选保持可追溯；不当作可发布字幕。
    first['status']='低可靠度机器候选，非确认转写；见音频转写说明'
    (folder/(sid+'_转写.json')).write_text(json.dumps(first,ensure_ascii=False,indent=2),encoding='utf-8')
    note='低可靠度机器候选，非确认转写；未逐句人工听校，不可直接发布为字幕。\n'
    p=folder/(sid+'_转写.txt');txt=p.read_text(encoding='utf-8')
    if not txt.startswith('低可靠度'):p.write_text(note+txt,encoding='utf-8')
    metrics.append(dict(id=sid,audio_seconds=round(dur,3),timeline_frames=len(list(folder.glob('frame_*.jpg'))),decode='PASS',first_pass_segments=len(first['segments']),second_pass_segments=len(second['segments']),confirmed_segments=0))
    r['内容状态']='全时段解码通过；逐秒采样画面已审；两轮ASR无可靠确认语句；未原速连续播放/人工听校'
pages=json.loads((out/'知识库/公司OCR/逐页OCR.json').read_text(encoding='utf-8'))
assert [p['page'] for p in pages]==list(range(1,51)) and all(p['text'].strip() for p in pages)
for p in pages: assert (out/'知识库/公司OCR/页面'/p['image']).is_file()
next(r for r in rows if r['id']=='S005')['内容状态']='50/50页OCR完成；关键页目视抽检；非逐字校对全文'
(out/'清单/原始文件清单.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
with (out/'清单/原始文件清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
(out/'清单/补充整理验证.json').write_text(json.dumps(dict(date='2026-11-20',originals_sha256='16/16 PASS',ocr_pages=len(pages),ocr_characters=sum(len(p['text']) for p in pages),videos=metrics),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(metrics,ensure_ascii=False,indent=2))
