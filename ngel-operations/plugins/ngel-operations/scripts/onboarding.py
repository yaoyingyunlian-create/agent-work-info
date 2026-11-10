"""Persist staged onboarding answers; no credentials, network or external writes."""
import argparse
import json
import os
import sys
from pathlib import Path
from validation import validate_timezone


QUESTIONS = [
    ("platform_accounts", "array", "首先接入哪些社交平台？请提供平台名和 Ngel 账号链接，不要提供密码。", "Which social platforms and Ngel account links should we connect first? Do not provide passwords."),
    ("boss_delivery", "object", "老板通过什么渠道接收日报？请提供渠道和准确收件人。", "Which channel and exact recipient should receive the daily report?"),
    ("staff_source", "string", "员工名单、班次和服务时长保存在哪里？请提供文件路径、表格链接，或说明尚未建立。", "Where are the staff roster, shifts and service durations stored? Provide a file path or sheet link, or say they are not available yet."),
    ("appointment_system", "string", "目前使用哪个预约系统或日历？如果没有，请说明需要新建。", "Which booking system or calendar do you use? If none, say a new one is needed."),
    ("reference_videos", "array", "希望参考哪些博主或视频？请提供链接。", "Which creators or videos should we use as references? Please provide links."),
    ("video_metrics_source", "string", "上一条发布视频及后台数据从哪里获取？请提供视频链接和数据文件或已授权后台入口。", "Where can we access the latest published video and its metrics? Provide the video link and an export or authorized dashboard."),
    ("timezone", "string", "晚八点按新加坡时间 Asia/Singapore 吗？也可以填写其他 IANA 时区。", "Should 8 pm use Asia/Singapore time? You may provide another IANA time zone."),
    ("script_languages", "array", "脚本使用中文、英文还是双语？请填写 zh-CN、en 或两者。", "Should scripts be in Chinese, English, or both? Use zh-CN, en, or both."),
    ("business_reviewer", "string", "谁负责确认价格、护理、补色、售后和知识库内容？请提供负责人姓名或角色。", "Who will verify prices, aftercare, touch-ups, policies and knowledge? Provide a name or role."),
    ("human_handoff_contact", "string", "需要人工处理的客户咨询转给谁？请提供联系渠道和负责人。", "Who should receive customer enquiries requiring a human? Provide a channel and contact."),
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".onboarding.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except FileExistsError:
        raise ValueError(f"Pending write exists; inspect before retrying: {temporary}")


def answered(key, business, rules):
    if key == "timezone":
        return rules.get("timezone_confirmed") is True
    if key == "boss_delivery":
        return bool(business.get("boss_recipient") and business.get("boss_channel"))
    # Template defaults are not user-confirmed answers.
    if key == "script_languages":
        return business.get("script_languages_confirmed") is True
    return bool(business.get(key))


def status(root):
    business = read(root / "config/business.json")
    rules = read(root / "config/agent-rules.json")
    state_path = root / "memory/onboarding.json"
    state = read(state_path) if state_path.exists() else {"deferred": []}
    missing = [q for q in QUESTIONS if not answered(q[0], business, rules)]
    next_questions = [{"id": key, "value_type": kind, "zh-CN": zh, "en": en}
                      for key, kind, zh, en in missing if key not in state["deferred"]][:3]
    return {"next_questions": next_questions, "deferred": state["deferred"],
            "missing": [q[0] for q in missing], "live_ready": False,
            "note": "Answers are intake data, not verified knowledge or platform authorization. Run workspace.py check and verify live systems separately."}


def apply(root, response):
    # One field per invocation avoids multi-file partial commits.
    if set(response) != {"id", "value"}:
        raise ValueError("Expected exactly id and value")
    key, value = response["id"], response["value"]
    question = next((q for q in QUESTIONS if q[0] == key), None)
    if question is None:
        raise ValueError("Unknown onboarding field")
    expected = {"array": list, "object": dict, "string": str}[question[1]]
    if not isinstance(value, expected) or not value:
        raise ValueError(f"{key} requires a non-empty {question[1]}")
    if isinstance(value, str) and not value.strip():
        raise ValueError("Empty answer")
    if key == "boss_delivery":
        if set(value) != {"channel", "recipient"} or not all(isinstance(v, str) and v.strip() for v in value.values()):
            raise ValueError("boss_delivery requires channel and recipient strings")
    if key in ("reference_videos", "script_languages"):
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("Array must contain non-empty strings")
    if key == "script_languages" and not set(value) <= {"zh-CN", "en"}:
        raise ValueError("Supported script languages: zh-CN, en")
    if key == "platform_accounts":
        if not all(isinstance(item, dict) and set(item) == {"platform", "account"}
                   and all(isinstance(v, str) and v.strip() for v in item.values()) for item in value):
            raise ValueError("Each account requires only platform and account strings; never store passwords")
    if key == "timezone":
        validate_timezone(value)
        path = root / "config/agent-rules.json"
        rules = read(path)
        schedule_path = root / "config/schedules.json"
        schedules = read(schedule_path)
        if any(job.get("enabled") for job in schedules["jobs"]):
            raise ValueError("Pause enabled schedules before changing timezone; verify host scheduler separately")
        schedules.update(timezone=value, timezone_confirmed=True)
        # Each write is atomic. If interrupted between writes, workspace check blocks the mismatch.
        save(schedule_path, schedules)
        rules.update(timezone=value, timezone_confirmed=True)
        save(path, rules)
        return
    path = root / "config/business.json"
    business = read(path)
    if key == "boss_delivery":
        business.update(boss_channel=value["channel"], boss_recipient=value["recipient"])
    else:
        business[key] = value
    if key == "script_languages":
        business["script_languages_confirmed"] = True
    save(path, business)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "apply", "defer", "resume"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--field", choices=[q[0] for q in QUESTIONS])
    args = parser.parse_args()
    root = args.workspace.resolve()
    if args.action == "apply":
        if not args.answer_file:
            parser.error("apply requires --answer-file")
        apply(root, read(args.answer_file))
    elif args.action in ("defer", "resume"):
        if not args.field:
            parser.error("defer/resume requires --field")
        path = root / "memory/onboarding.json"
        state = read(path) if path.exists() else {"deferred": []}
        deferred = set(state["deferred"])
        if args.action == "defer":
            deferred.add(args.field)
        else:
            deferred.discard(args.field)
        state["deferred"] = sorted(deferred)
        save(path, state)
    print(json.dumps(status(root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
