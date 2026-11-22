"""learning-coach 的标准库数据读写与校验工具。"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("LEARNING_COACH_DATA_DIR", PACKAGE_DIR / "data")).expanduser()
REQUIRED_FIELDS = ("id", "grade", "ability", "difficulty", "knowledge", "method", "stem", "answer", "solution", "pitfall", "keywords", "fingerprint")


def data_path(name: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / name


def load_json(name: str, default: Any) -> Any:
    path = data_path(name)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_question_bank() -> list[dict[str, Any]]:
    """题库随技能包发布，不随家庭运行数据目录切换。"""
    path = PACKAGE_DIR / "data" / "question_bank.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(name: str, value: Any) -> Path:
    path = data_path(name)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    temporary.replace(path)
    return path


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def validate_question(question: dict[str, Any]) -> list[str]:
    missing = [field for field in REQUIRED_FIELDS if question.get(field) in (None, "", [])]
    if question.get("difficulty") not in {"基础", "进阶", "挑战"}:
        missing.append("difficulty必须为基础/进阶/挑战")
    return missing


def get_profile(nickname: str) -> dict[str, Any] | None:
    return next((item for item in load_json("profiles.json", []) if item["nickname"] == nickname), None)
