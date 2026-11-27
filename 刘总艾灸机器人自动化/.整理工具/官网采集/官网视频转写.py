from pathlib import Path
import json
from faster_whisper import WhisperModel
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'整理成果/素材库/官网素材/2026-11-27'
modelpath=Path.home()/'.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120'
model=WhisperModel(str(modelpath),device='cpu',compute_type='int8',cpu_threads=6,local_files_only=True)
cache={}
for r in json.loads((BASE/'素材清单.json').read_text(encoding='utf-8')):
    if not r.get('has_audio'):continue
    sid=r['id']
    if r['sha256'] in cache:
        language,segs=cache[r['sha256']]
    else:
        segments,info=model.transcribe(str(BASE/'预览'/f'{sid}.wav'),beam_size=3,language=None,vad_filter=True,word_timestamps=False,condition_on_previous_text=False)
        segs=[dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob) for s in segments]
        language=info.language
        cache[r['sha256']]=(language,segs)
    (BASE/'OCR'/f'{sid}_音频转写.json').write_text(json.dumps(dict(id=sid,language=language,engine='faster-whisper small multilingual, auto language',status='机器初稿，未逐字听校，宣传语未独立核实',segments=segs),ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'OCR'/f'{sid}_音频转写.txt').write_text('机器初稿，未逐字听校；官网宣传不等于医学或商业核验。\n'+'\n'.join(f'[{s["start"]:.2f}—{s["end"]:.2f}] {s["text"]}' for s in segs),encoding='utf-8')
    print(sid,language,segs,flush=True)
