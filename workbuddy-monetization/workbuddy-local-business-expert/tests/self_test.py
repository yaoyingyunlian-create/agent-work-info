"""独立运行的关键路径自测。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "tests" / ".runtime_data"


def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "WORKBUDDY_LOCAL_BUSINESS_DATA_DIR": str(RUNTIME)}
    result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True)
    assert result.returncode == expected, result.stderr or result.stdout
    return result


def main() -> None:
    shutil.rmtree(RUNTIME, ignore_errors=True)
    run("scripts/manage_store.py", "add", "--nickname", "小鹿美甲", "--business-type", "美甲", "--stage", "新店", "--city-tier", "二线", "--district", "商圈", "--average-ticket", "168", "--daily-capacity", "8", "--daily-visits", "2", "--budget", "1200", "--channels", "抖音,小红书,朋友圈", "--main-problem", "缺咨询")
    generated = run("scripts/generate_plan.py", "--store", "小鹿美甲", "--offer", "新客单色美甲", "--list-price", "198", "--offer-price", "99", "--variable-cost", "28", "--channel-cost", "8", "--fixed-cost", "300")
    assert "WBA-" in generated.stdout
    run("scripts/record_review.py", "--store", "小鹿美甲", "--plan", "WBA-20261027-001", "--day", "1", "--views", "800", "--inquiries", "36", "--bookings", "12", "--visits", "8", "--deals", "6", "--adds", "5", "--cost", "120")
    rejected = run("scripts/generate_plan.py", "--store", "小鹿美甲", "--offer", "亏损套餐", "--list-price", "198", "--offer-price", "20", "--variable-cost", "28", "--channel-cost", "8", "--fixed-cost", "300", expected=2)
    assert "单次活动毛利不大于零" in rejected.stderr
    assert (RUNTIME / "outputs" / "WBA-20261027-001.md").exists()
    print("自测通过：档案、计划、复盘与负毛利拦截均已验证。")


if __name__ == "__main__":
    main()
