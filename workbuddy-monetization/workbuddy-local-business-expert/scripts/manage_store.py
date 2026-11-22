"""匿名门店档案管理。"""
from __future__ import annotations

import argparse
from datetime import datetime

from common import BUSINESS_TYPES, PROBLEMS, STAGES, get_store, load_json, save_json, validate_nickname


def main() -> None:
    parser = argparse.ArgumentParser(description="管理 WorkBuddy 匿名门店档案")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("--nickname", required=True)
    add.add_argument("--business-type", required=True, choices=sorted(BUSINESS_TYPES))
    add.add_argument("--stage", required=True, choices=sorted(STAGES))
    add.add_argument("--city-tier", required=True)
    add.add_argument("--district", required=True)
    add.add_argument("--average-ticket", required=True, type=float)
    add.add_argument("--daily-capacity", required=True, type=int)
    add.add_argument("--daily-visits", required=True, type=int)
    add.add_argument("--budget", required=True, type=float)
    add.add_argument("--channels", required=True)
    add.add_argument("--main-problem", required=True, choices=sorted(PROBLEMS))
    sub.add_parser("list")
    args = parser.parse_args()

    if args.command == "list":
        for store in load_json("stores.json", []):
            print(f"{store['nickname']} | {store['business_type']} | {store['stage']} | {store['main_problem']}")
        return

    error = validate_nickname(args.nickname)
    if error:
        parser.error(error)
    if get_store(args.nickname):
        parser.error("门店昵称已存在，请改用其他昵称。")
    if min(args.average_ticket, args.budget) < 0 or min(args.daily_capacity, args.daily_visits) < 0:
        parser.error("金额和数量不能为负数。")
    if args.daily_visits > args.daily_capacity:
        parser.error("当前日均到店量不能高于日接待上限。")
    channels = [item.strip() for item in args.channels.split(",") if item.strip()]
    if not channels:
        parser.error("至少填写一个可用渠道。")
    stores = load_json("stores.json", [])
    stores.append({
        "nickname": args.nickname.strip(), "business_type": args.business_type, "stage": args.stage,
        "city_tier": args.city_tier.strip(), "district": args.district.strip(),
        "average_ticket": args.average_ticket, "daily_capacity": args.daily_capacity,
        "daily_visits": args.daily_visits, "budget": args.budget, "channels": channels,
        "main_problem": args.main_problem, "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_json("stores.json", stores)
    print(f"已建立匿名门店档案：{args.nickname}")


if __name__ == "__main__":
    main()
