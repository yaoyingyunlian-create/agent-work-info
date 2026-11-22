"""生成 7 天到店获客计划和活动毛利测算。"""
from __future__ import annotations

import argparse
import math
from datetime import date

from common import DATA_DIR, get_store, load_json, next_plan_id, save_json


def material(channel: str, offer: str, day: int) -> str:
    samples = {
        "抖音": f"15 秒短视频：展示 {offer} 前后对比与服务过程，结尾口播“本周体验名额有限，评论区领取”。",
        "小红书": f"笔记标题：我在附近发现了 {offer} 的省心方案；正文写服务细节、适合人群和预约方式。",
        "朋友圈": f"今日 {offer} 体验位开放：适合首次到店顾客，回复“体验”了解可约时段。",
        "社群": f"群内提醒：第 {day} 天限量体验位，发送项目亮点和有效期，不刷屏。",
        "团购平台": f"上架 {offer} 体验套餐，明确服务时长、适用门店、预约规则与不可叠加优惠。",
    }
    return samples.get(channel, f"发布 {offer} 的到店邀约，说明服务内容、有效期和预约方式。")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 7 天到店获客计划")
    parser.add_argument("--store", required=True)
    parser.add_argument("--offer", required=True)
    parser.add_argument("--list-price", required=True, type=float)
    parser.add_argument("--offer-price", required=True, type=float)
    parser.add_argument("--variable-cost", required=True, type=float)
    parser.add_argument("--channel-cost", required=True, type=float)
    parser.add_argument("--fixed-cost", required=True, type=float)
    args = parser.parse_args()
    store = get_store(args.store)
    if not store:
        parser.error("未找到门店档案，请先运行 manage_store.py add。")
    if min(args.list_price, args.offer_price, args.variable_cost, args.channel_cost, args.fixed_cost) < 0:
        parser.error("价格与成本不能为负数。")
    unit_profit = args.offer_price - args.variable_cost - args.channel_cost
    if unit_profit <= 0:
        parser.error("单次活动毛利不大于零，不能生成保本方案；请调整活动价、服务组合或成本。")
    break_even = math.ceil(args.fixed_cost / unit_profit) if args.fixed_cost else 0
    plan_id = next_plan_id()
    primary_channels = store["channels"][:2]
    days = []
    focuses = ["确认卖点与预约规则", "发布首轮引流内容", "集中回复咨询", "强化到店承接", "展示服务案例", "老客转介绍", "汇总复盘与下周调整"]
    for day in range(1, 8):
        channel = primary_channels[(day - 1) % len(primary_channels)]
        days.append({
            "day": day, "goal": focuses[day - 1], "channel": channel,
            "material": material(channel, args.offer, day),
            "conversion": "统一使用预约话术：确认需求、可约时段和到店权益；到店后说明升级选项但不强推。",
            "metrics": "曝光、咨询、预约、到店、成交、加微信",
        })
    lines = [f"# {store['nickname']}：7 天到店获客计划", "", f"计划编号：{plan_id}", f"生成日期：{date.today():%Y-%m-%d}", "", "## 门店诊断", f"当前优先问题：{store['main_problem']}。先在可用渠道（{'、'.join(store['channels'])}）建立稳定邀约，再用预约和到店数据判断问题环节。", "", "## 活动测算", f"- 主推服务：{args.offer}", f"- 原价 / 活动价：{args.list_price:.2f} / {args.offer_price:.2f} 元", f"- 单次活动毛利：{unit_profit:.2f} 元", f"- 固定成本：{args.fixed_cost:.2f} 元", f"- 最低成交数：{break_even} 单", "", "## 每日执行"]
    for item in days:
        lines.extend([f"### 第 {item['day']} 天：{item['goal']}", f"- 渠道：{item['channel']}", f"- 素材：{item['material']}", f"- 承接：{item['conversion']}", f"- 记录：{item['metrics']}", ""])
    lines.extend(["## 风险提示", "活动名额、有效期、服务内容和不可叠加规则应在发布前写清；门店接待能力不足时，不要扩大预约名额。", "", "## 每日复盘", "每日仅录入汇总数据；样本不足时不对渠道或员工表现下结论。"])
    output_dir = DATA_DIR / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{plan_id}.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    plans = load_json("plans.json", [])
    plans.append({"id": plan_id, "store": store["nickname"], "offer": args.offer, "unit_profit": unit_profit, "break_even": break_even, "output": str(output)})
    save_json("plans.json", plans)
    print(f"已生成计划：{output}")


if __name__ == "__main__":
    main()
