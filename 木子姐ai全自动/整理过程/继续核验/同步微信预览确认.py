# -*- coding: utf-8 -*-
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
name='素材库/素材预览.html';p=ROOT/name;before=p.read_bytes();s=before.decode('utf-8')
old='资料宣传、价格、案例与授权尚待核实。'
assert old in s
s=s.replace(old,'这批材料已经用户确认。下方备注保留确认前的整理线索，具体缺项和版本差异以知识库记录为准。')
backup=OUT/'确认状态更新前'/name
assert not backup.exists()
backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
p.write_bytes(s.encode('utf-8'))
plan_path=OUT/'确认状态变更.json';plan=json.loads(plan_path.read_text(encoding='utf-8'))
plan.append({'path':name,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reason':'微信素材预览说明同步用户确认，原卡片备注保留为历史线索'})
plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('已同步微信预览的用户确认说明；原件和卡片来源备注保持不变。')
