"""Automatic dialogue alignment; never claims actual listening."""
import argparse, ctypes, hashlib, json, re, subprocess
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.vad import get_speech_timestamps, VadOptions

def norm(text):
    buf=ctypes.create_unicode_buffer(len(text)*2+8)
    ctypes.windll.kernel32.LCMapStringEx('zh-CN',0x02000000,text,len(text),buf,len(buf),None,None,0)
    return ''.join(c for c in buf.value if c.isalnum())

def sec(s):
    h,m,rest=s.replace(',', '.').split(':');return int(h)*3600+int(m)*60+float(rest)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('video',type=Path);ap.add_argument('srt',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    raw=subprocess.run(['ffmpeg','-v','error','-i',str(a.video),'-f','s16le','-ar','16000','-ac','1','pipe:1'],capture_output=True,check=True).stdout
    samples=np.frombuffer(raw,np.int16).astype(np.float32)/32768
    islands=get_speech_timestamps(samples,VadOptions(min_silence_duration_ms=500,speech_pad_ms=200))
    model=WhisperModel('small',device='cpu',compute_type='int8');observed=[]
    segs,_=model.transcribe(samples,language='zh',word_timestamps=True,vad_filter=True)
    for s in segs:
        if norm(s.text): observed.append({'start':s.start,'end':s.end,'text':s.text,'words':[{'start':w.start,'end':w.end,'text':w.word} for w in s.words or []]})
    speech_groups=[]
    for island in islands:
        start=float(island['start']/16000);end=float(island['end']/16000)
        if speech_groups and start-speech_groups[-1]['end']<1.3:speech_groups[-1]['end']=end
        else:speech_groups.append({'start':start,'end':end})
    expected=[]
    for block in re.split(r'\n\s*\n',a.srt.read_text(encoding='utf-8-sig').strip()):
        lines=block.splitlines();i=next(i for i,l in enumerate(lines) if '-->' in l);x,y=lines[i].split('-->');expected.append({'start':sec(x.strip()),'end':sec(y.strip()),'text':''.join(lines[i+1:])})
    transcript=norm(''.join(s['text'] for s in observed));expected_text=norm(''.join(s['text'] for s in expected));exact_text=transcript==expected_text
    checks=[]
    for i,cue in enumerate(expected):
        group=speech_groups[i] if i<len(speech_groups) else None
        checks.append({'expected':cue,'speech_group':group,'text_match':exact_text,'timing_match':bool(group) and abs(group['start']-cue['start'])<=.5 and abs(group['end']-cue['end'])<=.5})
    result={'video_sha256':hashlib.sha256(a.video.read_bytes()).hexdigest(),'method':'Independent full Whisper transcript exact comparison; ordered VAD utterance boundary alignment (0.5s tolerance), requires one subtitle cue per speech group','actual_listening':False,'note':'未实际核听；ASR长静音首词时间码不作为对齐依据','observed':observed,'speech_groups':speech_groups,'checks':checks,'dialogue_alignment_pass':len(speech_groups)==len(expected) and all(c['text_match'] and c['timing_match'] for c in checks)}
    encoded=json.dumps(result,ensure_ascii=False,indent=2,default=lambda v:v.item())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(encoded,encoding='utf-8');print(encoded)
    return 0 if result['dialogue_alignment_pass'] else 2
if __name__=='__main__':raise SystemExit(main())
