# -*- coding: utf-8 -*-
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone,timedelta

ROOT=Path(__file__).resolve().parents[2]
DEST=Path(__file__).parent/'整理前基线.json'
if DEST.exists():raise SystemExit('基线已存在，不覆盖。')
rows=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file():continue
    rows.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
DEST.write_text(json.dumps({'captured_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),'root':str(ROOT),'git':'当前目录不是Git仓库；使用逐文件SHA-256基线追踪本轮改动','files':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'baseline_files':len(rows),'bytes':sum(r['bytes'] for r in rows)},ensure_ascii=False))
