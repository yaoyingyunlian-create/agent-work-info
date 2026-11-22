"""Build a shallow WorkBuddy archive with bilingual metadata checks."""
import hashlib
import json
from pathlib import Path
import re
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
name = fields['name'].strip()
version = fields['version'].strip().strip('"')
if name != root.name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
    raise SystemExit('Invalid skill name')
if not re.fullmatch(r'\d+\.\d+\.\d+', version) or target.name != f'{name}-{version}.zip':
    raise SystemExit('Archive filename must match the skill name and version')
paths = [root / 'SKILL.md']
for folder, suffix in (('assets', '.json'), ('references', '.md'), ('scripts', '.py'), ('tests', '.py')):
    paths.extend(sorted((root / folder).rglob('*' + suffix)))
if any(len(p.relative_to(root).parts) > 2 for p in paths):
    raise SystemExit('Archive depth exceeds two components')
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in paths:
        archive.write(path, path.relative_to(root).as_posix())
with zipfile.ZipFile(target) as archive:
    if 'SKILL.md' not in archive.namelist() or archive.testzip() is not None:
        raise SystemExit('Invalid ZIP')
manifest = {'version': version, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'files': [p.relative_to(root).as_posix() for p in paths]}
Path(str(target) + '.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(target)
