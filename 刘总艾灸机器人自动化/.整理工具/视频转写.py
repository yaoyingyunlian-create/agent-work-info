from pathlib import Path
import json
from faster_whisper import WhisperModel

root=Path(__file__).resolve().parent.parent
base=root/'整理成果/素材库/视频复核'
modelpath=Path.home()/'.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120'
model=WhisperModel(str(modelpath),device='cpu',compute_type='int8',cpu_threads=6,local_files_only=True)
def ts(t):
    m=round(t*1000); return f'{m//3600000:02}:{m//60000%60:02}:{m//1000%60:02},{m%1000:03}'
for sid in ['S001','S002','S003']:
    folder=base/sid
    segs,info=model.transcribe(str(folder/(sid+'.wav')),beam_size=5,language=None,vad_filter=True,word_timestamps=True,condition_on_previous_text=False)
    items=[]
    for s in segs:
        items.append(dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob,words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in (s.words or [])]))
        print(sid,ts(s.start),s.text,flush=True)
    data=dict(source_id=sid,engine='faster-whisper 1.1.0 small multilingual CPU int8',language=info.language,language_probability=info.language_probability,duration=info.duration,status='机器转写初稿，未人工逐句听校',segments=items)
    (folder/(sid+'_转写.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/(sid+'_转写.txt')).write_text('机器转写初稿，未人工逐句听校；静音/未识别区间不补写。\n\n'+'\n'.join(f'[{ts(s["start"])} --> {ts(s["end"])}] {s["text"]}' for s in items),encoding='utf-8')
    (folder/(sid+'_转写.srt')).write_text('\n\n'.join(f'{i}\n{ts(s["start"])} --> {ts(s["end"])}\n{s["text"].strip()}' for i,s in enumerate(items,1)),encoding='utf-8')
    print('DONE',sid,len(items),'segments',flush=True)
