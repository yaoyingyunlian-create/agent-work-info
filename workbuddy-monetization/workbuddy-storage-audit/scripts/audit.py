import argparse
import json
import os
from pathlib import Path
import stat


PROTECTED = {"binaries", "skills", "memory", "memories"}
SENSITIVE = ("key-fallback", "apikey", "api-key", "api_key", "token", "令牌")
MAX_ENTRIES = 100_000
MAX_TRACE_BYTES = 1_048_576


def is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def sensitive(path):
    return any(word in path.name.casefold() for word in SENSITIVE)


def audit(root):
    root = Path(os.path.abspath(root))
    if root == Path(root.anchor) or not root.is_dir():
        raise ValueError("Provide an existing workspace directory, not a drive root")
    for item in (root, *root.parents):
        if is_link(item.lstat()):
            raise ValueError("Workspace path crosses a symlink or reparse point")
        if sensitive(item) or item.name.casefold() in {"windows", "winsxs", "system volume information"}:
            raise ValueError("Workspace path is protected or sensitive")
    totals = {}
    protected = []
    warnings = []
    failed = []
    skipped = []
    count = 0
    pending = [root]
    while pending and count < MAX_ENTRIES:
        folder = pending.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if count >= MAX_ENTRIES:
                        break
                    count += 1
                    path = Path(entry.path)
                    relative = path.relative_to(root)
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if is_link(info):
                            skipped.append([str(relative), "link"])
                            continue
                        if sensitive(path):
                            warnings.append(str(relative))
                            if "key-fallback" in path.name.casefold():
                                protected.append(str(relative))
                            skipped.append([str(relative), "sensitive"])
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            if path.name.casefold() in PROTECTED:
                                protected.append(str(relative))
                            pending.append(path)
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            continue
                        group = relative.parts[0] if len(relative.parts) > 1 else "."
                        totals[group] = totals.get(group, 0) + info.st_size
                        if "traces" in {part.casefold() for part in relative.parts[:-1]} and path.suffix.lower() == ".json":
                            if info.st_size > MAX_TRACE_BYTES:
                                skipped.append([str(relative), "trace exceeds size limit"])
                                continue
                            try:
                                with path.open("rb") as stream:
                                    data = stream.read(MAX_TRACE_BYTES + 1)
                                if len(data) > MAX_TRACE_BYTES:
                                    skipped.append([str(relative), "trace exceeds size limit"])
                                    continue
                                trace = json.loads(data)
                                if isinstance(trace, dict) and trace.get("status") == "error":
                                    failed.append(str(relative))
                            except (UnicodeError, ValueError):
                                skipped.append([str(relative), "unreadable JSON trace"])
                    except OSError as error:
                        skipped.append([str(relative), error.strerror])
        except OSError as error:
            skipped.append([str(folder.relative_to(root)), error.strerror])
    return {
        "root": str(root),
        "logical_bytes": sum(totals.values()),
        "bytes_by_top_level": dict(sorted(totals.items(), key=lambda entry: (-entry[1], entry[0]))),
        "protected": sorted(protected),
        "sensitive_names": sorted(warnings),
        "failed_trace_count": len(failed),
        "failed_traces": sorted(failed)[:50],
        "skipped": skipped,
        "entry_limit_reached": count >= MAX_ENTRIES,
        "requires_manual_review": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.workspace), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
