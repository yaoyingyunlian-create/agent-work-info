from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date

from common import DATA_DIR, load_json


def main() -> int:
    parser = argparse.ArgumentParser(description="生成学习周报Markdown")
    parser.add_argument("--profile", required=True)
    current_iso = date.today().isocalendar()
    parser.add_argument("--week", default=f"{current_iso[0]}-W{current_iso[1]:02d}")
    args = parser.parse_args()
    rows = [row for row in load_json("feedback.json", []) if row["profile"] == args.profile and f"{date.fromisoformat(row['date']).isocalendar()[0]}-W{date.fromisoformat(row['date']).isocalendar()[1]:02d}" == args.week]
    if not rows:
        print(f"{args.week} 暂无{args.profile}的反馈数据，无法生成周报。")
        return 1
    answers = [answer for row in rows for answer in row["answers"]]
    accuracy = sum(answer["status"] == "对" for answer in answers) / len(answers)
    average_minutes = sum(row["total_minutes"] for row in rows) / len(rows)
    ability = defaultdict(list)
    for answer in answers:
        ability[answer["ability"]].append(answer["status"] == "对")
    weak_name, weak_values = min(ability.items(), key=lambda item: sum(item[1]) / len(item[1]))
    weak_rate = sum(weak_values) / len(weak_values)
    advice = f"下周增加 2 道{weak_name}训练题，并在读题后先列出已知条件再作答。" if weak_rate < 0.8 else "下周保持能力轮换，并保留 1 道挑战题练习迁移。"
    content = f"# {args.profile} 学习周报 {args.week}\n\n- 完成练习：{len(rows)} 次\n- 作答正确率：{accuracy:.0%}\n- 平均完成耗时：{average_minutes:.1f} 分钟\n- 当前薄弱能力：{weak_name}（正确率 {weak_rate:.0%}）\n\n## 下周训练重点\n\n{advice}\n"
    output = DATA_DIR / "outputs" / f"{args.profile}_{args.week}_周报.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"文件路径：{output}\n\n{content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
