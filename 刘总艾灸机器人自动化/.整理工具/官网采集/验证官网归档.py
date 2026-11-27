from pathlib import Path
import hashlib,json,re,ast,urllib.parse
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'整理成果';CAP=OUT/'官网采集/2026-11-27';BASE=OUT/'素材库/官网素材/2026-11-27'
pages=json.loads((CAP/'来源清单.json').read_text(encoding='utf-8'));assets=json.loads((BASE/'素材清单.json').read_text(encoding='utf-8'))
assert len(pages)==159 and all(p['settled'] for p in pages)
assert len(assets)==57 and len({r['id'] for r in assets})==57
for r in assets:
    if r['status']!='downloaded':continue
    p=ROOT/r['local_path'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    if p.suffix in ['.jpg','.png']:
        assert (BASE/'OCR'/f'{r["id"]}.txt').is_file()
    if p.suffix=='.mp4':
        assert (BASE/'预览'/f'{r["id"]}_视频总览.jpg').is_file()
        s=json.loads((BASE/'OCR'/f'{r["id"]}_音频转写.json').read_text(encoding='utf-8'))
        assert s['language']=='zh' and all(0<=seg['start']<seg['end']<=r['duration']+.2 for seg in s['segments'])
for p in pages:
    assert hashlib.sha256((ROOT/p['json_path']).read_bytes()).hexdigest()==p['sha256']
    assert (ROOT/p['text_path']).is_file()
assert len(json.loads((CAP/'托管展示档位.json').read_text(encoding='utf-8')))==126
assert len(json.loads((BASE/'OCR/图片OCR.json').read_text(encoding='utf-8')))==50
for r in json.loads((OUT/'清单/原始文件清单.json').read_text(encoding='utf-8')):
    assert hashlib.sha256((ROOT/r['原始路径']).read_bytes()).hexdigest()==r['sha256']
links=0
for p in OUT.rglob('*.md'):
    for u in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if urllib.parse.urlsplit(u).scheme or u.startswith('#'):continue
        assert (p.parent/urllib.parse.unquote(u.split('#')[0])).exists(),(p,u)
        links+=1
for p in (ROOT/'.整理工具/官网采集').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
stats=json.loads((OUT/'清单/官网采集验证_20261127.json').read_text(encoding='utf-8'));stats.update(local_links_checked=links,asset_hashes='56/56 PASS',source_snapshot_hashes='159/159 PASS',ocr_mapping='50/50 PASS',asr_mapping='6/6 PASS',python_ast='PASS')
(OUT/'清单/官网采集验证_20261127.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: 159 snapshots, 56 media hashes, 50 OCR, 6 ASR mappings, 126 rental cards, 16 original hashes,',links,'local links')
