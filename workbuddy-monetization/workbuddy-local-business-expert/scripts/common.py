"""WorkBuddy 本地商家获客专家的 UTF-8 数据读写与校验。"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("WORKBUDDY_LOCAL_BUSINESS_DATA_DIR", PACKAGE_DIR / "data")).expanduser()
BUSINESS_TYPES = {"美甲", "美睫", "皮肤管理", "美发"}
STAGES = {"筹备", "新店", "稳定经营", "客流下滑"}
PROBLEMS = {"缺曝光", "缺咨询", "到店低", "成交低", "复购低"}
PHONE_RE = re.compile(r"1[3-9]\d{9}")


def data_path(name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / name


def load_json(name: str, default: Any) -> Any:
    path = data_path(name)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(name: str, value: Any) -> Path:
    path = data_path(name)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    temporary.replace(path)
    return path


def get_store(nickname: str) -> dict[str, Any] | None:
    return next((item for item in load_json("stores.json", []) if item["nickname"] == nickname), None)


def validate_nickname(value: str) -> str | None:
    if len(value.strip()) < 2:
        return "门店昵称至少需要 2 个字符。"
    if PHONE_RE.search(value):
        return "门店昵称不得包含手机号。"
    return None


def next_plan_id() -> str:
    plans = load_json("plans.json", [])
    return f"WBA-{date.today():%Y%m%d}-{len(plans) + 1:03d}"
