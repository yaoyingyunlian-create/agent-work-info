"""Count consecutive tool call repeats in a sanitized JSONL export."""
import argparse
import hashlib
import json
from pathlib import Path


def audit(lines):
    previous = {}
    repeats, exempt = [], 0
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError()
            session, tool = event["session"], event["tool"]
            if not all(isinstance(value, str) and value.strip() for value in (session, tool)):
                raise ValueError()
            kind = event.get("kind", "call")
            if kind not in ("call", "poll", "retry"):
                raise ValueError()
            payload = json.dumps([tool, event["arguments"]], sort_keys=True,
                                 ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError, KeyError):
            raise ValueError(f"Invalid sanitized event at line {line_number}") from None
        key = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if kind != "call":
            exempt += 1
            previous.pop(session, None)
            continue
        if previous.get(session) == key:
            repeats.append({"line": line_number, "fingerprint": key})
        previous[session] = key
    return {"repeat_count": len(repeats), "explicitly_exempt_count": exempt, "repeats": repeats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("export", type=Path)
    args = parser.parse_args()
    try:
        with args.export.open(encoding="utf-8-sig") as stream:
            result = audit(stream)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2))
