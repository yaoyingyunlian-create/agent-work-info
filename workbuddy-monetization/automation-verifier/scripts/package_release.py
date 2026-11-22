"""Validate WorkBuddy archive shape and package only audited source files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'


def package(target):
    text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise ValueError('缺少frontmatter')
    fields = {}
    for line in match[1].splitlines():
        key, value = line.split(':', 1)
        if key in fields:
            raise ValueError('重复元数据')
        fields[key] = value.strip().strip('"')
    for key in ('name', 'version', 'display_name', 'display_name_en', 'description', 'description_zh', 'description_en'):
        if not fields.get(key):
            raise ValueError('缺少字段 ' + key)
    if fields['version'] != VERSION or fields['name'] != ROOT.name:
        raise ValueError('版本或名称不一致')
    files = [ROOT / 'SKILL.md']
    for folder, suffix in [('scripts', '.py'), ('tests', '.py'), ('references', '.md'), ('assets', '.json')]:
        files.extend(sorted((ROOT / folder).glob('*' + suffix)))
    if target.exists() or target == ROOT or ROOT in target.parents:
        raise ValueError('发布包必须为技能目录外的新文件')
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            name = file.relative_to(ROOT).as_posix()
            if len(Path(name).parts) > 2:
                raise ValueError('超过一层子目录')
            archive.writestr(name, file.read_bytes())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None and 'SKILL.md' in archive.namelist()
        names = archive.namelist()
    manifest = {'version': VERSION, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'contents': names}
    target.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    package(Path(parser.parse_args().output).resolve())
