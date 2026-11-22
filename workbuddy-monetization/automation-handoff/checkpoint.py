"""Write a durable WorkBuddy stage checkpoint before external operations."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile


def checkpoint(root, stage, now=None):
    now = now or datetime.now(timezone(timedelta(hours=8)))
    folder = root / now.date().isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (stage + ".json")
    data = {
        "date": now.date().isoformat(),
        "stage": stage,
        "state": "partial",
        "items": [],
    }
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["generated_at"] = now.isoformat()
    data["execution_checkpoint"] = {
        "state": "started",
        "started_at": now.isoformat(),
        "note": "Stage started. Completion requires a subsequent verified handoff.",
    }
    descriptor, temporary = tempfile.mkstemp(dir=folder, suffix=".tmp")
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(temporary, path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=[
        "01-collect", "02-analysis", "03-build", "04-release",
        "05-review", "06-weekly",
    ])
    args = parser.parse_args()
    print(checkpoint(Path(__file__).resolve().parent, args.stage))
