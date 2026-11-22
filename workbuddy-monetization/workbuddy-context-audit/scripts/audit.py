"""Count UTF-8 text and extract verbatim, source-linked checklist candidates."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import stat


RULE = re.compile(r"必须|不得|严禁|禁止|仅限|应当|至少|至多|不得超过|例外|\b(?:must|shall|required|never|only|at least|at most|except)\b", re.I)
ITEM = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)、]\s*)")
MAX_BYTES = 2_000_000
MAX_FILES = 500
MAX_CHECKLIST = 800


def linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def audit(root):
    root = Path(os.path.abspath(root))
    if root == Path(root.anchor) or not root.is_dir():
        raise ValueError("Provide an authorized text directory")
    if any(linked(path) for path in (root, *root.parents)):
        raise ValueError("Linked directories are unsupported")
    files, skipped, rules = [], [], {}
    for folder, dirs, names in os.walk(root, onerror=lambda err: skipped.append(str(err))):
        for name in sorted(dirs):
            path = Path(folder, name)
            try:
                if not linked(path):
                    continue
            except OSError:
                pass
            dirs.remove(name)
            skipped.append(path.relative_to(root).as_posix())
        dirs.sort()
        for name in sorted(names):
            path = Path(folder, name)
            if path.suffix.lower() not in {".md", ".txt"}:
                continue
            relative = path.relative_to(root).as_posix()
            if len(files) >= MAX_FILES:
                skipped.append("File limit reached")
                return report(files, rules, skipped)
            try:
                if linked(path) or not path.is_file():
                    skipped.append(relative)
                    continue
                with path.open("rb") as stream:
                    data = stream.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    skipped.append(relative)
                    continue
                content = data.decode("utf-8-sig")
            except (OSError, UnicodeError):
                skipped.append(relative)
                continue
            files.append({"path": relative, "characters": len(content)})
            for index, line in enumerate(content.splitlines(), 1):
                candidate = ITEM.sub("", line).strip()
                if candidate and (ITEM.match(line) or RULE.search(candidate)):
                    rules.setdefault(candidate, []).append({"path": relative, "line": index})
    return report(files, rules, skipped)


def report(files, rules, skipped):
    size = sum(len(line) + 3 for line in rules)
    return {
        "file_count": len(files),
        "characters": sum(file["characters"] for file in files),
        "files": files,
        "rules": [{"text": rule, "sources": sources} for rule, sources in rules.items()],
        "checklist": list(rules) if size <= MAX_CHECKLIST else None,
        "review_mode": "verify_anchors" if size <= MAX_CHECKLIST else "load_by_source_file",
        "skipped": skipped,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--token-factors", nargs=2, type=float, metavar=("LOW", "HIGH"))
    args = parser.parse_args()
    try:
        result = audit(args.directory)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    if args.token_factors:
        low, high = args.token_factors
        if not (0 < low <= high and math.isfinite(high * max(1, result["characters"]))):
            parser.error("Token factors must be positive, finite, and in ascending order")
        result["estimated_tokens"] = [
            math.floor(result["characters"] * low),
            math.ceil(result["characters"] * high),
        ]
    print(json.dumps(result, ensure_ascii=False, indent=2))
