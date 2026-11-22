from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "learning-coach" / "scripts"
DATA = ROOT / "tests" / ".runtime_data"


def run(*args: str) -> str:
    env = os.environ.copy()
    env["LEARNING_COACH_DATA_DIR"] = str(DATA)
    result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True, check=True)
    return result.stdout


def main() -> int:
    if DATA.exists():
        shutil.rmtree(DATA)
    run(str(SCRIPTS / "manage_profile.py"), "add", "--nickname", "测试孩子", "--grade", "4", "--guardian-consent", "yes")
    first_day = date(2026, 10, 1)
    numbers = []
    for offset in range(7):
        output = run(str(SCRIPTS / "generate_practice.py"), "--profile", "测试孩子", "--date", (first_day + timedelta(days=offset)).isoformat(), "--adaptive")
        filename = next(line.split("：", 1)[1] for line in output.splitlines() if line.startswith("文件路径：")).rsplit("\\", 1)[-1]
        number = filename[:-5] if filename.endswith(".html") else filename
        numbers.append(number)
        statuses = '["错", "错", "错", "不会", "错"]' if offset < 2 else '["对", "对", "对", "错", "对"]'
        run(str(SCRIPTS / "record_feedback.py"), "--profile", "测试孩子", "--practice", number, "--results", statuses, "--total-minutes", str(25 + offset), "--blocker", "条件整理")
    ledger = json.loads((DATA / "ledger.json").read_text(encoding="utf-8"))
    assert len(ledger) == 7
    all_fingerprints = [fingerprint for row in ledger for fingerprint in row["fingerprints"]]
    assert len(all_fingerprints) == len(set(all_fingerprints)), "7天内出现题目指纹重复"
    adaptive = run(str(SCRIPTS / "adaptive.py"), "--profile", "测试孩子")
    assert '"adaptive": true' in adaptive
    report = run(str(SCRIPTS / "weekly_report.py"), "--profile", "测试孩子", "--week", "2026-W40")
    assert "下周训练重点" in report
    print("PASS: 连续7天去重、反馈、自适应与周报校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
