
"""Standard edition reimbursement precheck. Python 3.12 tested."""
import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from sources import FIELDS, inspect_file, kind_value

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.1"
CENT = Decimal("0.01")
TOLERANCE = {"S1": Decimal("0.00"), "S2": CENT, "S3": Decimal("0.02")}
MIN_CONFIDENCE = Decimal("0.90")
NUMBER = re.compile(r"[0-9]{20}")
LIMIT = 50
UNREADABLE = (OSError, ValueError, ParseError, BadZipFile, KeyError, RuntimeError, NotImplementedError)

def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                          encoding="utf-8")

def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}须为非空文本")
    return value.strip()

def money(value):
    if not isinstance(value, str):
        return None
    value = value.strip().lstrip("¥￥").strip()
    if not re.fullmatch(r"[+-]?(?:[0-9]{1,14}|[0-9]{1,3}(?:,[0-9]{3}){1,4})(?:\.[0-9]{1,2})?", value):
        return None
    return Decimal(value.replace(",", "")).quantize(CENT)

def rate(value):
    if not re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,8})?%?", value):
        return None
    result = Decimal(value.rstrip("%")) / (100 if value.endswith("%") else 1)
    return result if result <= 1 else None

def invoice_date(value):
    stamp = r"(?:[T ][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?)?"
    if re.fullmatch(r"[0-9]{8}", value):
        value = f"{value[:4]}-{value[4:6]}-{value[6:]}"
    value = value.replace("年", "-").replace("月", "-").removesuffix("日").replace("/", "-")
    match = re.fullmatch(r"([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})" + stamp, value)
    try:
        return date(*map(int, match.groups())) if match else None
    except ValueError:
        return None

def read_history(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream, strict=True)
        if not rows.fieldnames or not {"发票号码", "报销人", "报销日期"} <= set(rows.fieldnames):
            raise ValueError("历史 CSV 须含发票号码、报销人、报销日期三列")
        if len(set(rows.fieldnames)) != len(rows.fieldnames):
            raise ValueError("历史 CSV 存在重复列")
        numbers = set()
        for index, row in enumerate(rows, 2):
            number = (row.get("发票号码") or "").strip()
            if not NUMBER.fullmatch(number) or not (row.get("报销人") or "").strip() or not invoice_date(
                    (row.get("报销日期") or "").strip()) or None in row:
                raise ValueError(f"历史 CSV 第 {index} 行格式错误，请核对原台账票号及日期")
            numbers.add(number)
        return numbers

def read_columns(config):
    columns = config.get("columns")
    if not isinstance(columns, list) or not 1 <= len(columns) <= 60:
        raise ValueError("请提供报销系统字段及其顺序")
    parsed = []
    for column in columns:
        if not isinstance(column, dict):
            raise ValueError("字段映射格式错误")
        label = required_text(column.get("label"), "字段名称")
        key = column.get("key")
        if not isinstance(key, str) or key not in {*FIELDS, "file", "custom"}:
            raise ValueError(f"字段 {label} 映射未知，请按 references/input.md 明确映射")
        parsed.append((label, key))
    if len({label for label, _ in parsed}) != len(parsed):
        raise ValueError("系统字段名称重复，请区分列名")
    if sum(key == "total" for _, key in parsed) != 1:
        raise ValueError("须明确且仅映射一个价税合计列，用于按实际底稿单元格对账")
    return parsed

def read_batch(config, base):
    expected = config.get("expected_count")
    if type(expected) is not int or not 1 <= expected <= LIMIT:
        raise ValueError("应到张数须为 1–50 的整数")
    entries = config.get("files")
    if not isinstance(entries, list) or len(entries) > LIMIT:
        raise ValueError("文件清单须为数组，标准版实到上限 50 张")
    tickets, paths = [], set()
    for index, name in enumerate(entries, 1):
        path = (base / required_text(name, "文件路径")).resolve()
        if path in paths:
            raise ValueError("同一路径重复列入清单，请按实际附件计数")
        paths.add(path)
        ticket = {"id": str(index), "file": path.name, "source": "", "fields": {}, "lines": []}
        try:
            ticket.update(inspect_file(path))
        except UNREADABLE as exc:
            ticket["error"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            ticket["unreadable"] = isinstance(exc, OSError)
        tickets.append(ticket)
    return tickets

def compact(text):
    return re.sub(r"\s+", "", text)

def read_observation(entry, ticket, key):
    if not isinstance(entry, dict) or not isinstance(entry.get("value"), str):
        return None
    value = entry["value"].strip()
    evidence = entry.get("evidence")
    if not value or not isinstance(evidence, str) or not evidence.strip():
        return None
    if ticket["source"] == "S2":
        if compact(value) not in compact(evidence) or compact(evidence) not in compact(ticket["text"]):
            return None
        return {"value": value, "evidence": evidence}
    confidence = entry.get("confidence")
    if type(confidence) not in (float, int) or not 0 <= confidence <= 1:
        return None
    if Decimal(str(confidence)) < MIN_CONFIDENCE:
        return None
    return {"value": value, "evidence": evidence, "confidence": confidence}

def apply_observations(ticket, observation):
    if not observation:
        return
    if not isinstance(observation, dict) or observation.get("sha256") != ticket.get("sha256"):
        raise ValueError(f"第 {ticket['id']} 张观察记录缺少正确文件指纹，请重新 inspect")
    fields = observation.get("fields", {})
    lines = observation.get("lines", [])
    if not isinstance(fields, dict) or not isinstance(lines, list) or any(not isinstance(line, dict) for line in lines):
        raise ValueError("观察字段须为对象，明细须为对象数组")
    for key, entry in fields.items():
        if key not in FIELDS or key == "reason":
            raise ValueError(f"观察记录字段 {key} 未获支持，事由只能由脚本生成候选")
        if ticket["source"] == "S1" or ticket.get("error"):
            raise ValueError("S1 或解析失败的原文件字段不得用观察记录覆盖")
        field = read_observation(entry, ticket, key)
        if field:
            ticket["fields"][key] = field
        else:
            ticket.setdefault("unconfirmed", {})[key] = entry.get("evidence", "") if isinstance(entry, dict) else ""
    for line in lines:
        if ticket["source"] not in ("S2", "S3") or ticket.get("error"):
            raise ValueError("仅 S2/S3 支持明细观察记录")
        ticket["lines"].append({key: field for key in ("net", "tax", "rate") if
                                (field := read_observation(line.get(key), ticket, key))})

def field_value(ticket, key):
    return ticket["fields"].get(key, {}).get("value", "")

def compare_gap(blocks, field, actual, expected, tolerance):
    gap = actual - expected
    if abs(gap) > tolerance:
        blocks.append(("勾稽不平", f"{field}：票面 {actual:.2f}，计算 {expected:.2f}，差 {gap:+.2f} 元"))

def multiplication(ticket, net, tax, pending, blocks, tolerance):
    lines = ticket["lines"] or [ticket["fields"]]
    nets, taxes = [], []
    for index, line in enumerate(lines, 1):
        value = lambda key: line.get(key, {}).get("value", "")
        base, line_tax, raw_rate = money(value("net")), money(value("tax")), value("rate")
        exempt = raw_rate in {"免税", "不征税"}
        if exempt and value("tax") in {"***", "**", "*", "—", "-"}:
            line_tax = Decimal(0)
        if base is None or line_tax is None or (not exempt and rate(raw_rate) is None):
            pending.append(("勾稽明细", f"第 {index} 行金额、税额或税率缺失/不明，请看票面明细", True))
            continue
        expected_tax = Decimal(0) if exempt else (base * rate(raw_rate)).quantize(CENT, ROUND_HALF_UP)
        compare_gap(blocks, f"第 {index} 行税额", line_tax, expected_tax, tolerance)
        nets.append(base)
        taxes.append(line_tax)
    if ticket["lines"] and len(nets) == len(lines):
        compare_gap(blocks, "不含税合计与明细", net, sum(nets), tolerance)
        compare_gap(blocks, "税额合计与明细", tax, sum(taxes), tolerance)

def check_ticket(ticket, config, counts, history):
    value = lambda key: field_value(ticket, key)
    source = ticket["source"]
    blocks, pending = [], []
    if ticket.get("error"):
        return blocks, [("原件", ticket["error"], True)]
    for key, region in ticket.get("unconfirmed", {}).items():
        pending.append((FIELDS[key], f"字段待人工核对，请查看 {region or '原附件对应区域'}", True))
    kind = kind_value(value("kind"))
    number, issued = value("number"), invoice_date(value("date"))
    for key, readable in (("kind", kind), ("number", number), ("date", issued),
                          ("buyer", value("buyer")), ("buyer_id", value("buyer_id"))):
        if not readable:
            pending.append((FIELDS[key], "请查看原附件相应票面栏位", True))
    if number and not NUMBER.fullmatch(number):
        blocks.append(("号码异常", f"发票号码 {number}，需为 20 位 ASCII 数字"))
    elif number:
        if issued and number[:2] != str(issued.year)[-2:]:
            blocks.append(("号码异常", f"发票号码年度位 {number[:2]}，开票年度末两位 {str(issued.year)[-2:]}"))
        if counts[number] > 1:
            blocks.append(("号码异常", f"批内重复 {number}，共 {counts[number]} 张，请确认保留哪份原件"))
        if number in history:
            blocks.append(("号码异常", f"历史台账已含同票号 {number}"))
    if issued and issued.strftime("%Y-%m") != config["period"]:
        blocks.append(("期间外", f"开票日期 {issued}，报销期间 {config['period']}"))
    for key in ("buyer", "buyer_id"):
        if value(key) and value(key) != config[key]:
            blocks.append(("抬头不符", f"{FIELDS[key]}票面为 {value(key)}，预期 {config[key]}"))
    if kind:
        tolerance = TOLERANCE[source]
        mode = value("mode")
        exempt = mode in {"免税", "不征税", "免税/不征税"} or value("rate") in {"免税", "不征税"}
        differential = "差额" in mode
        if kind == "air":
            keys = ("fare", "fuel", "tax", "fund", "other", "total")
        else:
            keys = ("net", "tax", "total")
        amounts = {key: money(value(key)) for key in keys}
        if exempt and amounts["tax"] is None and value("tax") in {"***", "**", "*", "—", "-"}:
            amounts["tax"] = Decimal(0)
        for key, amount in amounts.items():
            if amount is None:
                pending.append((FIELDS[key], "请核对原件金额和人民币分位", True))
        if differential:
            pending.append(("计税口径", "差额征税，乘算不适用，请人工复核差额计税依据", True))
        if all(amount is not None for amount in amounts.values()):
            compare_gap(blocks, "价税合计", amounts["total"], sum(amounts[k] for k in keys[:-1]), tolerance)
            if not (differential or exempt or kind == "air"):
                multiplication(ticket, amounts["net"], amounts["tax"], pending, blocks, tolerance)
            elif kind == "air" and not (differential or exempt):
                vat = rate(value("rate"))
                if vat is None:
                    pending.append(("税率", "请查看行程单税率栏", True))
                else:
                    compare_gap(blocks, "民航增值税税额", amounts["tax"],
                                ((amounts["fare"] + amounts["fuel"]) * vat).quantize(CENT, ROUND_HALF_UP), tolerance)
    return blocks, pending

def cell_for(ticket, key, infer_reason):
    if key == "file":
        return {"value": ticket["file"], "state": "明示", "evidence": "附件名"}
    if key == "reason" and infer_reason:
        for basis in ("item", "train", "flight"):
            if field_value(ticket, basis):
                candidate = "交通出行（" + field_value(ticket, basis) + "）" if basis != "item" else field_value(ticket, basis)
                return {"value": candidate, "state": "可推定", "evidence": FIELDS[basis],
                        **({"confidence": ticket["fields"][basis]["confidence"]} if ticket["source"] == "S3" else {})}
    if key in ticket["fields"] and key != "reason":
        return {**ticket["fields"][key], "state": "明示"}
    return {"value": "", "state": "缺失", "evidence": ""}

def reconcile(tickets, rows, columns, blocks, pending):
    totals = [money(field_value(t, "total")) for t in tickets]
    total_index = next(i for i, (_, key) in enumerate(columns) if key == "total")
    if any(len(row["cells"]) != len(columns) for row in rows):
        raise ValueError("底稿行列自检失败")
    if any(cell["source"] not in TOLERANCE or cell["state"] not in {"明示", "可推定", "缺失"}
           or (cell["state"] == "可推定" and not cell["evidence"])
           for row in rows for cell in row["cells"]):
        raise ValueError("底稿来源或字段状态自检失败")
    values = [money(row["cells"][total_index]["value"]) for row in rows]
    if any(v is None for v in values):
        raise ValueError("底稿金额列自检失败")
    original = sum(totals, Decimal(0)) if all(t is not None for t in totals) else None
    draft = sum(values, Decimal(0))
    gap = original - draft if original is not None else None
    passed = gap == 0 and len(rows) == len(tickets) and not blocks and not pending
    return {"source_total": original, "draft_total": draft, "difference": gap,
            "status": "通过" if passed else "未通过"}

def run(config, base, tickets):
    actual = sum(not t.get("unreadable") for t in tickets)
    report = {"expected": config["expected_count"], "actual": actual, "tickets": tickets}
    if report["expected"] != actual or len(tickets) != actual:
        return report
    columns = read_columns(config)
    for key, label in (("buyer", "单位全称"), ("buyer_id", "单位税号"), ("period", "报销期间")):
        config[key] = required_text(config.get(key), label)
    if not re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", config["period"]):
        raise ValueError("报销期间须为 YYYY-MM")
    history_path = config.get("history")
    history = read_history(base / required_text(history_path, "历史台账路径")) if history_path else set()
    observations = config.get("observations", {})
    if not isinstance(observations, dict) or set(observations) - {t["id"] for t in tickets}:
        raise ValueError("观察记录包含未知附件序号")
    for t in tickets:
        apply_observations(t, observations.get(t["id"]))
    counts = Counter(field_value(t, "number") for t in tickets)
    rows, blocks, pending, verification = [], [], [], []
    for t in tickets:
        rejected, missing = check_ticket(t, config, counts, history)
        cells = []
        for label, key in columns:
            cell = cell_for(t, key, config.get("infer_reason") is True)
            cells.append({**cell, "source": t["source"]})
            if cell["state"] == "缺失":
                missing.append((label, f"从附件 {t['file']} 或对应业务记录补充", False))
            elif cell["state"] == "可推定":
                missing.append((label, f"候选依据为{cell['evidence']}，请由本人确认事由", False))
        if not rejected and not any(critical for _, _, critical in missing):
            rows.append({"file": t["file"], "cells": cells})
        identity = f"{t['id']}. {t['file']}"
        blocks.extend((identity, *item) for item in rejected)
        pending.extend((identity, *item) for item in dict.fromkeys((label, msg) for label, msg, _ in missing))
        verification.append((identity, *(field_value(t, k) for k in ("number", "date", "total"))))
    report.update(columns=columns, rows=rows, blocks=blocks, pending=pending, verification=verification,
                  history=bool(history_path), totals=reconcile(tickets, rows, columns, blocks, pending))
    return report

def escape(text):
    return str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ").replace(
        "<", "&lt;").replace(">", "&gt;").replace("]", "\\]").replace("[", "\\[")

def table(headers, rows):
    def line(values):
        return "| " + " | ".join(escape(v) for v in values) + " |"
    return [line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)]

def display(cell):
    if cell["state"] == "缺失":
        return ""
    value = cell["value"]
    if cell["state"] == "可推定":
        value = f"【推断】{value}（依据：{cell['evidence']}）"
    confidence = f"（置信度 {cell['confidence']:.0%}）" if "confidence" in cell else ""
    return f"{value}{confidence}〔{cell['source']}〕"

def render(report):
    lines = ["# 报销底稿（单据预审版）", "", "## 1. 输入清单", "",
             f"应到 {report['expected']} 张，实到可读 {report['actual']} 张。", ""]
    lines += table(["序号", "附件", "来源", "读取状态"], [
        (t["id"], t["file"], t["source"] or "待判定", t.get("error", "已读取"))
        for t in report["tickets"]])
    if "rows" not in report:
        return "\n".join(lines + ["", "已中止。请补齐或更正附件清单和应到张数。", ""])
    totals = report["totals"]
    lines += ["", "## 2. 底稿表", ""]
    lines += table([label for label, _ in report["columns"]],
                   [[display(c) for c in row["cells"]] for row in report["rows"]])
    if totals["status"] == "未通过":
        lines += ["", "当前表仅供复核。拦截项或关键字段待人工的票据已排除。"]
    for title, headers, data in (
        ("3. 拦截清单", ["附件", "类型", "字段与差异"], report["blocks"]),
        ("4. 待补清单", ["附件", "字段", "核对线索"], report["pending"]),
    ):
        lines += ["", "## " + title, ""] + (table(headers, data) if data else ["无。"])
    lines += ["", "## 5. 合计对账", "",
              f"底稿行数 {len(report['rows'])}，应对账票据 {report['expected']} 张。",
              "历史台账已纳入查重。" if report["history"] else "未提供历史台账，跨月重复无法发现。"]
    for key, label in (("source_total", "票据合计"), ("draft_total", "底稿合计"), ("difference", "差额")):
        amount = totals[key]
        lines.append(f"- {label} {'无法计算' if amount is None else f'{amount:.2f} 元'}")
    lines += [f"- 结论 **{totals['status']}**", "", "## 6. 待查验清单", ""]
    lines += table(["附件", "发票号码", "开票日期", "价税合计"], report["verification"])
    lines += ["", "请逐张使用[全国增值税发票查验平台](https://inv-veri.chinatax.gov.cn/)。"
              "按[查验说明](https://inv-veri.chinatax.gov.cn/fpcysm.html)，每张每日最多 5 次。",
              "", "## 7. 口径声明", "",
              "本表用于提交前单据预处理，财务审核与官方查验需另行完成。"
              "技能不代提交。业务事由由报销人确认。", ""]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="报销底稿（单据预审版）")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("action", choices=("inspect", "run"))
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8-sig"))
        base = args.config.resolve().parent
        target = args.output.resolve()
        inputs = [args.config.resolve(), *((base / file).resolve() for file in config["files"])]
        if config.get("history"):
            inputs.append((base / config["history"]).resolve())
        if target in inputs or target.exists():
            raise ValueError("输出须使用新的文件路径，避免覆盖票据或已有结果")
        tickets = read_batch(config, base)
        if args.action == "inspect":
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(tickets, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
            return 0
        report = run(config, base, tickets)
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(render(report))
        print(target)
        return 0 if report.get("totals", {}).get("status") == "通过" else 2
    except (OSError, ValueError, csv.Error, TypeError, KeyError, AttributeError) as exc:
        print(f"输入或运行错误：{exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
