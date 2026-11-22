from __future__ import annotations

import argparse
import html
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from adaptive import recommendation
from common import DATA_DIR, get_profile, load_json, load_question_bank, parse_date, save_json, validate_question


def recent_fingerprints(profile: str, day: date) -> set[str]:
    ledger = load_json("ledger.json", [])
    boundary = day - timedelta(days=60)
    return {fingerprint for row in ledger if row.get("profile") == profile and parse_date(row["date"]) >= boundary for fingerprint in row["fingerprints"]}


def choose(questions: list[dict], profile: str, day: date, adaptive: bool) -> tuple[list[dict], dict]:
    excluded = recent_fingerprints(profile, day) if profile else set()
    eligible = [q for q in questions if q["fingerprint"] not in excluded]
    plan = recommendation(profile) if adaptive and profile else {"adaptive": False, "priority_abilities": [], "reason": "未使用档案自适应，采用均衡轮换。"}
    selected: list[dict] = []
    used_abilities: set[str] = set()
    priority = plan.get("priority_abilities", [])
    by_id = {q["id"]: q for q in questions}
    difficulty_usage = Counter()
    for item in load_json("practices.json", []):
        if item.get("profile") == profile and parse_date(item["date"]) >= day - timedelta(days=60):
            for question_id in item["question_ids"]:
                past = by_id.get(question_id)
                if past:
                    difficulty_usage[(past["difficulty"], past["ability"])] += 1
    for difficulty in ("基础", "基础", "进阶", "进阶", "挑战"):
        candidates = [q for q in eligible if q["difficulty"] == difficulty and q["fingerprint"] not in {x["fingerprint"] for x in selected}]
        if difficulty == "挑战" and priority and len(used_abilities) >= 4:
            alternatives = [q for q in candidates if q["ability"] == priority[0]]
            if alternatives:
                candidates = alternatives
        # 先保证能力覆盖，再在同等覆盖价值下优先薄弱能力。
        candidates.sort(key=lambda q: (0 if q["ability"] not in used_abilities else 1, difficulty_usage[(q["difficulty"], q["ability"])], 0 if q["ability"] in priority else 1, q["id"]))
        if not candidates:
            raise ValueError(f"题库不足：找不到可用的{difficulty}题，或60天去重后无题可选。")
        picked = candidates[0]
        selected.append(picked)
        used_abilities.add(picked["ability"])
        difficulty_usage[(picked["difficulty"], picked["ability"])] += 1
    return selected, plan


def validate_before(selected: list[dict], profile: str, day: date) -> None:
    errors = []
    if len(selected) != 5:
        errors.append("题量不是5")
    if Counter(q["difficulty"] for q in selected) != Counter({"基础": 2, "进阶": 2, "挑战": 1}):
        errors.append("难度配比不是基础2/进阶2/挑战1")
    if len({q["ability"] for q in selected}) < 4:
        errors.append("能力类别少于4")
    fingerprints = [q["fingerprint"] for q in selected]
    if len(fingerprints) != len(set(fingerprints)):
        errors.append("本次存在重复指纹")
    recent = recent_fingerprints(profile, day) if profile else set()
    if set(fingerprints) & recent:
        errors.append("命中60天内历史指纹")
    for question in selected:
        missing = validate_question(question)
        if missing:
            errors.append(f"{question.get('id', '未知题目')}字段无效：{','.join(missing)}")
    if errors:
        raise ValueError("生成前校验失败：" + "；".join(errors))


def render(selected: list[dict], child: str, practice_no: str, day: date, focus: str) -> str:
    template = (Path(__file__).resolve().parents[1] / "assets" / "practice_template.html").read_text(encoding="utf-8")
    questions = "".join(f'<div class="q"><strong>{index}. {html.escape(q["stem"])}</strong><div class="tag">{q["ability"]}｜{q["difficulty"]}</div><div class="answer-space"></div></div>' for index, q in enumerate(selected, 1))
    answers = "".join(f'<div class="a"><strong>{index}. 答案：{html.escape(q["answer"])}</strong><br>思路：{html.escape(q["solution"])}<br>考查能力：{html.escape(q["ability"])}<br>常见误区：{html.escape(q["pitfall"])}</div>' for index, q in enumerate(selected, 1))
    values = {"child": child, "practice_no": practice_no, "date": day.isoformat(), "focus": focus, "questions": questions, "answers": answers}
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def validate_after(content: str, practice_no: str) -> None:
    checks = {"双页": content.count('class="page"') == 2, "题目数": content.count('class="q"') == 5, "答案数": content.count('class="a"') == 5,
              "编号": content.count(practice_no) == 2, "A4": "@page { size: A4;" in content, "分页": "page-break-after: always" in content}
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("生成后校验失败：" + "、".join(failed))


def main() -> int:
    parser = argparse.ArgumentParser(description="生成双页数学逻辑练习HTML")
    parser.add_argument("--profile", help="已建档的孩子昵称")
    parser.add_argument("--grade", type=int, choices=(1, 2, 3, 4, 5, 6), help="无档案预览的年级")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--adaptive", action="store_true")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    if args.history:
        if not args.profile:
            parser.error("--history 需要 --profile")
        for item in load_json("practices.json", []):
            if item.get("profile") == args.profile:
                print(f"{item['practice_no']}｜{item['date']}｜{item['path']}")
        return 0
    profile = get_profile(args.profile) if args.profile else None
    if args.profile and not profile:
        parser.error("未找到档案，请先运行 manage_profile.py add")
    if profile and not profile["guardian_consent"]:
        parser.error("监护人未同意，不能生成练习")
    grade = profile["grade"] if profile else args.grade
    if grade is None:
        parser.error("必须提供 --profile 或 --grade")
    day = parse_date(args.date)
    bank = [q for q in load_question_bank() if q["grade"] == grade]
    selected, plan = choose(bank, args.profile or "", day, args.adaptive)
    validate_before(selected, args.profile or "", day)
    practices = load_json("practices.json", [])
    suffix = sum(1 for item in practices if item["date"] == day.isoformat()) + 1
    number = f"PB-{day.strftime('%Y%m%d')}-{suffix:02d}"
    focus = plan["reason"]
    content = render(selected, args.profile or f"{grade}年级体验用户", number, day, focus)
    validate_after(content, number)
    output_dir = DATA_DIR / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{number}.html"
    output.write_text(content, encoding="utf-8")
    record = {"practice_no": number, "profile": args.profile, "grade": grade, "date": day.isoformat(), "path": str(output), "question_ids": [q["id"] for q in selected], "fingerprints": [q["fingerprint"] for q in selected], "abilities": [q["ability"] for q in selected], "adaptive_note": focus}
    practices.append(record)
    save_json("practices.json", practices)
    if args.profile:
        ledger = load_json("ledger.json", [])
        ledger.append({"profile": args.profile, "date": day.isoformat(), "practice_no": number, "fingerprints": record["fingerprints"]})
        save_json("ledger.json", ledger)
    print(f"文件路径：{output}")
    print("选题摘要：" + "；".join(f"{index}.{q['ability']}/{q['difficulty']}" for index, q in enumerate(selected, 1)))
    print("调整说明：" + focus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
