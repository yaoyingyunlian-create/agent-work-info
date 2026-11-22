import argparse
import hashlib
import os
import re
import tempfile
import zipfile
from pathlib import Path
from common import ROOT, VERSION, write_json


def validate_frontmatter(content):
    """Validate our flat, single-line WorkBuddy publishing metadata without dependencies."""
    match = re.match(r'\A---\n(.*?)\n---(?:\n|$)', content, re.S)
    if not match:
        raise ValueError('SKILL.md缺少有效frontmatter')
    fields = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        item = re.fullmatch(r'([a-z_][a-z_0-9-]*):[ \t]*(.+)', line)
        if not item or item[1] in fields:
            raise ValueError('发布元数据必须是无重复键的顶层单行文本字段')
        fields[item[1]] = item[2].strip().strip('"\'')
    for key in ['name', 'description', 'version', 'display_name', 'display_name_en',
                'description_zh', 'description_en']:
        if not fields.get(key) or fields[key] in {'null', '~', '|', '>'}:
            raise ValueError(f'SKILL.md缺少有效顶层字段：{key}')
    if fields['version'] != VERSION:
        raise ValueError('frontmatter版本与运行脚本版本不一致')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', fields['name']):
        raise ValueError('技能name必须使用小写英文、数字及连字符')
    return fields


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    args = p.parse_args()
    target = Path(args.output).resolve()
    if ROOT in target.parents:
        raise ValueError('发布包必须存放在技能目录之外')
    validate_frontmatter((ROOT / 'SKILL.md').read_text(encoding='utf-8'))
    files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py', '.md', '.json', '.xlsx', '.txt', '.ps1'}
             and not set(p.relative_to(ROOT).parts) & {'__pycache__', '.venv', 'data', '.runtime', '.pytest_cache'}]
    allowed_top = {'SKILL.md', 'requirements.txt', 'references', 'assets', 'scripts', 'tests'}
    if any(p.relative_to(ROOT).parts[0] not in allowed_top for p in files):
        raise ValueError('包中存在非预期文件，请检查后重新打包')
    if any(len(p.relative_to(ROOT).parts) > 2 for p in files):
        raise ValueError('WorkBuddy仅支持根目录及一级子目录中的文件，请移除嵌套')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix='.zip')
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(files):
                archive.write(path, path.relative_to(ROOT).as_posix())
        with zipfile.ZipFile(tmp) as archive:
            if archive.testzip():
                raise ValueError('ZIP完整性检查失败')
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    write_json(str(target) + '.manifest.json', {'version': VERSION, 'files': len(files),
               'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
               'contents': [p.relative_to(ROOT).as_posix() for p in sorted(files)]})
    print(str(target))


if __name__ == '__main__':
    main()
