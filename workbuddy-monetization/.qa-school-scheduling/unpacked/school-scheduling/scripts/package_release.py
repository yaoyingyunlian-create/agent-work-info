import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path
from common import ROOT, VERSION, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    args = p.parse_args()
    target = Path(args.output).resolve()
    if ROOT in target.parents:
        raise ValueError('发布包必须存放在技能目录之外')
    files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py', '.md', '.json', '.xlsx', '.txt', '.ps1'}
             and not set(p.relative_to(ROOT).parts) & {'__pycache__', '.venv', 'data', '.runtime', '.pytest_cache'}]
    allowed_top = {'SKILL.md', 'requirements.txt', 'references', 'assets', 'scripts', 'tests'}
    if any(p.relative_to(ROOT).parts[0] not in allowed_top for p in files):
        raise ValueError('包中存在非预期文件，请检查后重新打包')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix='.zip')
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(files):
                archive.write(path, 'school-scheduling/' + path.relative_to(ROOT).as_posix())
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
