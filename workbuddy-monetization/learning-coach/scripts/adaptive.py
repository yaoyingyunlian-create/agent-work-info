from __future__ import annotations

import argparse
import json
from collections import defaultdict

from common import load_json


def recommendation(profile: str) -> dict:
    feedback = [row for row in load_json("feedback.json", []) if row["profile"] == profile]
    scores: dict[str, list[int]] = defaultdict(list)
    for row in feedback[-14:]:
        for answer in row["answers"]:
            scores[answer["ability"]].append(1 if answer["status"] == "对" else 0)
    weak = []
    for ability, values in scores.items():
        if len(values) >= 2 and sum(values) / len(values) < 0.6:
            weak.append({"ability": ability, "samples": len(values), "accuracy": round(sum(values) / len(values), 2)})
    if not weak:
        return {"profile": profile, "adaptive": False, "priority_abilities": [], "difficulty": {"基础": 2, "进阶": 2, "挑战": 1}, "reason": "反馈不足或暂无达到阈值的薄弱能力，保持均衡轮换。"}
    names = [item["ability"] for item in sorted(weak, key=lambda item: item["accuracy"])]
    return {"profile": profile, "adaptive": True, "priority_abilities": names, "difficulty": {"基础": 2, "进阶": 2, "挑战": 1}, "replace_challenge_with": names[0], "evidence": weak, "reason": f"{names[0]}近14次反馈正确率偏低，下一份练习优先安排1题该能力的进阶变式。"}


def main() -> int:
    parser = argparse.ArgumentParser(description="输出下一份练习的自适应建议")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    print(json.dumps(recommendation(args.profile), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
