"""Check declared expectations against a sanitized scheduler snapshot."""
import argparse
from datetime import datetime
import json
from pathlib import Path


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("An explicit offset is required")
    return result


CHECKS = (
    ("encoding", "expected_encoding", "observed_encoding",
     lambda expected, observed: expected.casefold() == observed.casefold()),
    ("working_directory", "expected_cwd", "observed_cwd",
     lambda expected, observed: expected == observed),
    ("timezone", "expected_local_time", "observed_local_time",
     lambda expected, observed: timestamp(expected).utcoffset() == timestamp(observed).utcoffset()),
    ("data_readiness", "data_ready_at", "run_at",
     lambda expected, observed: timestamp(observed) >= timestamp(expected)),
    ("missing_value", "expected_missing_policy", "observed_missing_policy",
     lambda expected, observed: expected == observed),
)


def audit(snapshot):
    results = []
    for category, expected, observed, matches in CHECKS:
        fields = (expected, observed)
        values = {key: snapshot.get(key) for key in fields}
        missing = [key for key, value in values.items() if not isinstance(value, str) or not value.strip()]
        if missing:
            results.append({"category": category, "status": "unknown", "missing_fields": missing})
            continue
        try:
            status = "match" if matches(values[expected], values[observed]) else "mismatch"
        except ValueError:
            status = "unknown"
        results.append({"category": category, "status": status, "evidence": values,
                        **({"reason": "invalid timestamp or missing offset"} if status == "unknown" else {})})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        if not isinstance(snapshot, dict):
            raise ValueError("Expected a JSON object")
        print(json.dumps(audit(snapshot), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
