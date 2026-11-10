"""Initialize or inspect an Ngel workspace. Standard library only, UTF-8."""
import argparse
import json
import sys
from pathlib import Path
from validation import knowledge_errors, validate_timezone


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def initialize(root, assets):
    defaults = {
        "config/agent-rules.json": read_json(assets / "config/agent-rules.json"),
        "config/schedules.json": read_json(assets / "config/schedules.json"),
        "config/business.json": read_json(assets / "config/business.example.json"),
        "knowledge/ngel-faq.json": read_json(assets / "knowledge/ngel-faq.draft.json"),
        "memory/business.json": {"version": 1, "facts": [], "hypotheses": []},
        "memory/tasks.json": {"version": 1, "tasks": []},
    }
    for relative, data in defaults.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            print(f"CREATED {relative}")
        except FileExistsError:
            print(f"KEPT {relative}")


def check(root, strict=False):
    rules = read_json(root / "config/agent-rules.json")
    schedules = read_json(root / "config/schedules.json")
    business = read_json(root / "config/business.json")
    knowledge = read_json(root / "knowledge/ngel-faq.json")
    read_json(root / "memory/business.json")
    read_json(root / "memory/tasks.json")
    errors, blockers = [], []
    try:
        validate_timezone(rules.get("timezone"))
    except ValueError as error:
        errors.append(str(error))
    if schedules.get("timezone") != rules.get("timezone"):
        blockers.append("schedule timezone differs from business timezone; synchronize before enabling")
    if not rules.get("timezone_confirmed"):
        blockers.append("business timezone not confirmed")
    for key in ("platform_accounts", "boss_recipient", "boss_channel", "appointment_system", "staff"):
        if not business.get(key):
            blockers.append(f"missing business.{key}")
    retention = rules.get("memory_policy", {}).get("retention_days")
    if type(retention) is not int or retention <= 0:
        blockers.append("customer data retention not configured")
    ids = set()
    verified = 0
    for entry in knowledge["entries"]:
        identity = entry["id"]
        if identity in ids:
            errors.append(f"duplicate knowledge id: {identity}")
        ids.add(identity)
        flag = entry.get("auto_reply_allowed")
        if type(flag) is not bool:
            errors.append(f"auto_reply_allowed must be boolean: {identity}")
        entry_errors = knowledge_errors(entry)
        errors.extend(f"{issue}: {identity}" for issue in entry_errors)
        if flag is True and not entry_errors:
            verified += 1
    if not verified:
        blockers.append("no knowledge entries approved for auto replies")
    for job in schedules["jobs"]:
        if job.get("enabled"):
            blockers.append(f"job {job['id']} enabled in file; actual scheduler receipt must be checked separately")
    print(json.dumps({"structural_check": "failed" if errors else "passed",
                      "errors": errors, "live_readiness_blockers": blockers,
                      "verified_auto_reply_entries": verified,
                      "configuration_ready": not errors and not blockers,
                      "live_ready": False,
                      "external_systems_tested": False}, ensure_ascii=False, indent=2))
    return 1 if errors else (2 if strict and blockers else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "check"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit 2 for incomplete configuration, 1 for invalid data")
    args = parser.parse_args()
    root = args.workspace.resolve()
    if args.action == "init":
        initialize(root, Path(__file__).resolve().parents[1] / "assets")
    return check(root, strict=args.strict)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
