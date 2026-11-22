"""Compare two user-authorized directory trees without modifying them."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


def linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def inventory(directory):
    root = Path(os.path.abspath(directory))
    if root == Path(root.anchor) or not root.is_dir():
        raise ValueError("Expected an accessible directory below the drive root")
    if any(linked(path) for path in (root, *root.parents)):
        raise ValueError("Linked directory paths are unsupported")
    files, skipped = {}, []

    def record_error(error):
        skipped.append({"path": str(error.filename), "reason": error.strerror})

    for folder, directories, names in os.walk(root, onerror=record_error):
        for name in sorted(directories + names):
            path = Path(folder, name)
            relative = path.relative_to(root).as_posix()
            try:
                if linked(path):
                    skipped.append({"path": relative, "reason": "link"})
                elif name in directories:
                    continue
                elif path.is_file():
                    digest = hashlib.sha256()
                    with path.open("rb") as stream:
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(block)
                    files[relative] = digest.hexdigest()
                else:
                    skipped.append({"path": relative, "reason": "not a regular file"})
            except OSError as error:
                record_error(error)
            if name in directories:
                directories.remove(name)
    return files, skipped


def compare(source, target):
    before, source_skipped = inventory(source)
    after, target_skipped = inventory(target)
    missing = sorted(before.keys() - after.keys())
    extra = sorted(after.keys() - before.keys())
    changed = sorted(path for path in before.keys() & after.keys() if before[path] != after[path])
    return {
        "status": "incomplete" if source_skipped or target_skipped else
                  "different" if missing or extra or changed else "match",
        "missing_from_readable_target": missing,
        "extra_in_readable_target": extra,
        "changed": changed,
        "source_skipped": source_skipped,
        "target_skipped": target_skipped,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.source, args.target)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "incomplete", "reason": str(error)}, ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
