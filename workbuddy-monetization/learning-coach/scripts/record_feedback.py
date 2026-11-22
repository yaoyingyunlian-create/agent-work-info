from __future__ import annotations

import argparse
import json
from datetime import datetime

from common import load_json, save_json


def main() -> int:
    parser = argparse.ArgumentParser(description="录入练习作答反馈")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--practice", required=True)
    parser.add_argument("--results", required=True, help='JSON数组，如 ["对","错","不会","对","对"]')
    parser.add_argument("--total-minutes", required=True, type=int)
    parser.add_argument("--blocker", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    try:
        results = json.loads(args.results)
    except json.JSONDecodeError as error:
        parser.error(f"--results 不是有效JSON：{error.msg}")
    if len(results) != 5 or any(item not in {"对", "错", "不会"} for item in results):
        parser.error("--results 必须恰好包含5项，且每项为 对/错/不会")
    practice = next((item for item in load_json("practices.json", []) if item["practice_no"] == args.practice and item.get("profile") == args.profile), None)
    if not practice:
        parser.error("未找到该档案对应练习")
    answers = [{"number": index, "status": status, "ability": practice["abilities"][index - 1]} for index, status in enumerate(results, 1)]
    feedback = load_json("feedback.json", [])
    feedback = [row for row in feedback if not (row["profile"] == args.profile and row["practice_no"] == args.practice)]
    feedback.append({"profile": args.profile, "practice_no": args.practice, "date": practice["date"], "answers": answers, "total_minutes": args.total_minutes, "blocker": args.blocker, "note": args.note, "recorded_at": datetime.now().isoformat(timespec="seconds")})
    path = save_json("feedback.json", feedback)
    correct = sum(item == "对" for item in results)
    print(f"反馈已保存：{path}｜{args.practice}｜正确 {correct}/5｜总耗时 {args.total_minutes} 分钟")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
