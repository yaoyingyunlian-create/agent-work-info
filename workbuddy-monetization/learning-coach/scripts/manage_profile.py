from __future__ import annotations

import argparse
from datetime import datetime

from common import get_profile, load_json, save_json


def main() -> int:
    parser = argparse.ArgumentParser(description="管理匿名孩子学习档案")
    sub = parser.add_subparsers(dest="action", required=True)
    add = sub.add_parser("add", help="新增或更新档案")
    add.add_argument("--nickname", required=True)
    add.add_argument("--grade", required=True, type=int, choices=(1, 2, 3, 4, 5, 6))
    add.add_argument("--term", default="上学期")
    add.add_argument("--frequency", default="daily")
    add.add_argument("--goal", default="逻辑思维与解决问题")
    add.add_argument("--guardian-consent", required=True, choices=("yes", "no"))
    sub.add_parser("list", help="列出档案")
    args = parser.parse_args()
    profiles = load_json("profiles.json", [])
    if args.action == "list":
        for item in profiles:
            print(f"{item['nickname']}｜{item['grade']}年级｜{item['term']}｜监护人同意：{item['guardian_consent']}")
        return 0
    item = get_profile(args.nickname)
    record = {"nickname": args.nickname, "grade": args.grade, "term": args.term, "frequency": args.frequency,
              "goal": args.goal, "guardian_consent": args.guardian_consent == "yes", "updated_at": datetime.now().isoformat(timespec="seconds")}
    if item:
        profiles[profiles.index(item)] = record
    else:
        record["created_at"] = record["updated_at"]
        profiles.append(record)
    path = save_json("profiles.json", profiles)
    print(f"档案已保存：{path}｜{args.nickname}｜{args.grade}年级")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
