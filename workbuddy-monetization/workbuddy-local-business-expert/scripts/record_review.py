"""记录每日汇总漏斗数据并输出不超过三项复盘建议。"""
from __future__ import annotations

import argparse

from common import DATA_DIR, get_store, load_json, save_json


def rate(numerator: int, denominator: int) -> str:
    return "样本不足" if denominator <= 0 else f"{numerator / denominator:.1%}"


def advice(values: dict[str, int]) -> list[str]:
    if values["views"] <= 0 or values["inquiries"] <= 0:
        return ["关键漏斗数据不足，先连续记录曝光和咨询，再判断渠道问题。"]
    result: list[str] = []
    if values["inquiries"] / values["views"] < 0.02:
        result.append("曝光到咨询偏低：把服务结果、适合人群和限时权益放在内容前半段。")
    if values["bookings"] / values["inquiries"] < 0.3:
        result.append("咨询到预约偏低：统一回复可约时段、服务时长和到店权益，减少来回确认。")
    if values["visits"] / max(values["bookings"], 1) < 0.6:
        result.append("预约到店偏低：在预约前一天和当天各提醒一次，并再次确认位置与到店时间。")
    if values["deals"] / max(values["visits"], 1) < 0.5:
        result.append("到店成交偏低：先完成体验和需求确认，再提供一个与需求匹配的升级选项。")
    return result[:3] or ["当前漏斗未出现明显短板，继续记录 3 天后再比较趋势。"]


def main() -> None:
    parser = argparse.ArgumentParser(description="录入门店每日汇总复盘")
    parser.add_argument("--store", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--day", required=True, type=int, choices=range(1, 8))
    for name in ("views", "inquiries", "bookings", "visits", "deals", "adds"):
        parser.add_argument(f"--{name}", required=True, type=int)
    parser.add_argument("--cost", required=True, type=float)
    parser.add_argument("--blocker", default="")
    args = parser.parse_args()
    if not get_store(args.store):
        parser.error("未找到门店档案。")
    plans = load_json("plans.json", [])
    if not any(plan["id"] == args.plan and plan["store"] == args.store for plan in plans):
        parser.error("计划编号与门店不匹配。")
    values = {name: getattr(args, name) for name in ("views", "inquiries", "bookings", "visits", "deals", "adds")}
    if min(*values.values(), args.cost) < 0:
        parser.error("汇总数据和成本不能为负数。")
    suggestions = advice(values)
    reviews = load_json("reviews.json", [])
    reviews.append({"store": args.store, "plan": args.plan, "day": args.day, **values, "cost": args.cost, "blocker": args.blocker, "suggestions": suggestions})
    save_json("reviews.json", reviews)
    lines = [f"# 第 {args.day} 天复盘", "", f"- 曝光到咨询：{rate(values['inquiries'], values['views'])}", f"- 咨询到预约：{rate(values['bookings'], values['inquiries'])}", f"- 预约到店：{rate(values['visits'], values['bookings'])}", f"- 到店成交：{rate(values['deals'], values['visits'])}", "", "## 下一步"]
    lines.extend(f"- {item}" for item in suggestions)
    if args.blocker:
        lines.extend(["", f"执行障碍：{args.blocker}"])
    output_dir = DATA_DIR / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{args.plan}-day{args.day}-review.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成复盘：{output}")


if __name__ == "__main__":
    main()
