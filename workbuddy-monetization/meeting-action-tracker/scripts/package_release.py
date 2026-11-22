"""Build a shallow WorkBuddy archive with bilingual metadata checks."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
target = Path(sys.argv[1]).resolve()
if target == root or root in target.parents:
    raise SystemExit('Output must be outside the skill folder')
content = (root / 'SKILL.md').read_text(encoding='utf-8')
fields = dict(line.split(':', 1) for line in content.split('---', 2)[1].strip().splitlines())
for key in ('name', 'version', 'display_name', 'display_name_en', 'description', 'description_zh', 'description_en'):
    if not fields.get(key, '').strip():
        raise SystemExit(f'Missing {key}')
paths = sorted(p for p in root.rglob('*') if p.is_file() and p.suffix in {'.md', '.py', '.json'} and '__pycache__' not in p.parts)
if any(len(p.relative_to(root).parts) > 2 for p in paths):
    raise SystemExit('Archive depth exceeds two components')
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in paths:
        archive.write(path, path.relative_to(root).as_posix())
with zipfile.ZipFile(target) as archive:
    assert 'SKILL.md' in archive.namelist()
    assert archive.testzip() is None
manifest = {'version': fields['version'].strip().strip('"'), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'files': [p.relative_to(root).as_posix() for p in paths]}
Path(str(target) + '.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(target)
