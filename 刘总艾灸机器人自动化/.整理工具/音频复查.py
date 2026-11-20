from pathlib import Path
import json,subprocess
from faster_whisper import WhisperModel
root=Path(__file__).resolve().parent.parent
base=root/'整理成果/素材库/视频复核'
modelpath=Path.home()/'.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120'
model=WhisperModel(str(modelpath),device='cpu',compute_type='int8',cpu_threads=6,local_files_only=True)
for sid in ['S001','S002','S003']:
    f=base/sid
    wav=f/(sid+'_增强.wav')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(f/(sid+'.wav')),'-af','highpass=f=150,lowpass=f=7000,afftdn=nf=-35,loudnorm=I=-18:TP=-2:LRA=11','-ar','16000',str(wav)],check=True)
    segs,info=model.transcribe(str(wav),beam_size=5,language='zh',vad_filter=False,word_timestamps=True,condition_on_previous_text=False)
    items=[]
    for s in segs:
        items.append(dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob))
        print(sid,round(s.start,2),round(s.end,2),s.text,'logprob',round(s.avg_logprob,3),flush=True)
    (f/(sid+'_增强复查.json')).write_text(json.dumps(dict(engine='small multilingual, forced zh, no VAD, denoise+loudnorm',status='复查候选，非确认文本',duration=info.duration,segments=items),ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE',sid,len(items),flush=True)
