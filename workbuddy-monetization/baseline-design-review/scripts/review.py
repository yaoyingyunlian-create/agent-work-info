"""Verify a locked text review and route model-proposed findings."""
import argparse
from datetime import date
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys

DIMENSIONS = ("图签", "图号", "图例与材料表", "说明条款", "标准引用", "图间一致性")
LEVELS = ("高", "中", "低")
HEADER = ("序号", "图号", "位置", "问题描述", "依据", "建议", "严重程度", "证据片段")
CITATION = re.compile(r"([A-Z][A-Z0-9/]*(?: [A-Z]+)? [0-9]+(?:\.[0-9]+)*[-—][0-9]{4}) 第([0-9]+(?:\.[0-9]+)*)条")
DISCLAIMER = "初校辅助，不构成审查结论，不替代校对、审核、审定签字。依据以现行有效版本为准。"


class StopReview(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise StopReview(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON 键重复：" + key)
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def signature(data):
    return digest(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def stamp(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), "日期须为 YYYY-MM-DD")
    return date.fromisoformat(value)


def folder(config_path, value):
    path = (config_path.parent / value).resolve()
    require(path.is_dir(), "输入目录不存在：" + str(path))
    return path


def relative_file(root, name):
    entry = Path(name)
    require(not entry.is_absolute() and not entry.drive and ".." not in entry.parts,
            "清单路径须位于输入目录：" + name)
    path = (root / entry).resolve()
    require(root in path.parents and path.is_file(), "输入文件不可读：" + name)
    return path


def inventory(root):
    names = set()
    for item in root.rglob("*"):
        require(not item.is_symlink() and root in item.resolve().parents,
                "基准目录包含链接或越界路径：" + str(item))
        if item.is_file():
            names.add(item.relative_to(root).as_posix())
    return names


def load_documents(root, entries, is_baseline, as_of):
    require(isinstance(entries, list) and entries, "缺少基准或待审清单")
    documents = {}
    ledger = []
    used_paths = set()
    baseline_names = set()
    for item in entries:
        key = item["id"]
        require(nonempty(key) and key.casefold() not in documents, "清单 ID 为空或重复")
        path = relative_file(root, item["path"])
        relative = path.relative_to(root).as_posix()
        require(relative.casefold() not in used_paths, "清单文件重复：" + relative)
        used_paths.add(relative.casefold())
        raw = path.read_bytes()
        row = {"id": key, "path": relative, "sha256": digest(raw)}
        if is_baseline:
            name = path.stem.casefold()
            require(name not in baseline_names, "基准存在同名候选：" + path.stem)
            baseline_names.add(name)
            require(nonempty(item["version"]) and stamp(item["effective_date"]) <= as_of,
                    "基准版本缺失或尚未生效：" + relative)
            require(re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) and row["sha256"] == item["sha256"],
                    "基准哈希与已确认清单不符：" + relative)
            row.update(version=item["version"], effective_date=item["effective_date"])
        if path.suffix.lower() in (".txt", ".md"):
            anchors = {"L" + str(index): line for index, line in
                       enumerate(raw.decode("utf-8-sig").splitlines(), 1) if line.strip()}
        elif path.suffix.lower() == ".json":
            anchors = decode(raw)["anchors"]
        else:
            raise StopReview("输入须先转成可定位的 UTF-8 文本：" + relative)
        require(isinstance(anchors, dict) and anchors and
                all(nonempty(loc) and nonempty(body) for loc, body in anchors.items()),
                "无可回源文本：" + relative)
        documents[key.casefold()] = {"id": key, "anchors": anchors}
        ledger.append(row)
    return documents, ledger


def validate_rules(rules, standards, history, baseline):
    ids = set()
    for rule in rules:
        require(nonempty(rule["id"]) and rule["id"] not in ids and nonempty(rule["reason"]),
                "禁止提规则 ID 重复或说明为空")
        ids.add(rule["id"])
        require(rule["dimension"] in DIMENSIONS and nonempty(rule["field"]), "禁止提规则缺少明确字段范围")
        kind = rule["kind"]
        require(kind in ("equivalent", "excluded_field", "withdrawn"), "禁止提规则类型未知")
        if kind == "equivalent":
            values = rule["values"]
            require(isinstance(values, list) and len(values) >= 2 and all(nonempty(v) for v in values)
                    and len(set(v.strip() for v in values)) >= 2, "同义规则至少需要两个不同的非空值")
        else:
            locations = rule["locations"]
            require(isinstance(locations, list) and locations and all(nonempty(loc) for loc in locations),
                    "不查字段和撤销规则须指定精确位置")
        if kind == "withdrawn":
            require(nonempty(rule["basis"]) and CITATION.fullmatch(rule["basis"]),
                    "撤销规则缺少精确依据引用")
    require(isinstance(standards, dict) and isinstance(history, list), "依据表或历史库格式错误")
    active_codes = set()
    for edition, record in standards.items():
        require(CITATION.fullmatch(edition + " 第1条"), "标准版本格式无效：" + edition)
        require(record["state"] in ("current", "superseded"), "标准状态无效")
        if record["state"] == "current":
            code = edition[:-5]
            require(code not in active_codes, "同一标准登记了多个现行版本：" + code)
            active_codes.add(code)
        for clause, anchor in record.get("clauses", {}).items():
            require(re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", clause) and
                    anchor["id"].casefold() in baseline and
                    anchor["location"] in baseline[anchor["id"].casefold()]["anchors"],
                    "条款未指向基准正文：" + edition + " 第" + clause + "条")
    prior_ids = set()
    for item in history:
        require(all(nonempty(item[k]) for k in ("id", "sheet", "location", "dimension", "field",
                                                "basis", "evidence", "problem")) and
                item["id"] not in prior_ids and item["status"] in ("open", "closed"), "历史意见无效")
        stamp(item["date"])
        prior_ids.add(item["id"])


def prepare(config_path):
    config = decode(config_path.read_bytes())
    require(config["baseline_confirmed"] is True, "须由用户确认唯一有效的基准清单")
    as_of = stamp(config["review_date"])
    baseline_root = folder(config_path, config["baseline_dir"])
    target_root = folder(config_path, config["target_dir"])
    require(baseline_root != target_root and baseline_root not in target_root.parents and
            target_root not in baseline_root.parents, "待审和基准须使用分离的目录")
    require(config_path not in baseline_root.parents and baseline_root not in config_path.parents,
            "配置须保存在基准目录之外")
    expected = {item["path"].replace("\\", "/") for item in config["baseline"]}
    present = inventory(baseline_root)
    require(expected == present, "基准目录与批准清单不符。额外文件 " +
            repr(sorted(present - expected)) + "；缺失文件 " + repr(sorted(expected - present)))
    baseline, baseline_ledger = load_documents(baseline_root, config["baseline"], True, as_of)
    targets, target_ledger = load_documents(target_root, config["targets"], False, as_of)
    dimensions = config.get("dimensions", list(DIMENSIONS))
    require(isinstance(dimensions, list) and dimensions and all(d in DIMENSIONS for d in dimensions)
            and len(set(dimensions)) == len(dimensions), "校审维度不合法或重复")
    rules = config.get("suppressions", [])
    standards = config.get("standards", {})
    history = config.get("history", [])
    require(isinstance(rules, list), "禁止提清单须为列表")
    require(nonempty(config.get("rules_version")), "须声明规则库版本")
    validate_rules(rules, standards, history, baseline)
    ledger = {"baseline_dir": str(baseline_root), "target_dir": str(target_root),
              "baseline": baseline_ledger, "targets": target_ledger, "review_date": config["review_date"],
              "dimensions": dimensions, "rules_version": config["rules_version"],
              "suppression_rules": len(rules), "reference_only": not rules}
    snapshot = signature({"config": config, "ledger": ledger})
    return {"snapshot": snapshot, "ledger": ledger, "baseline": baseline, "targets": targets,
            "standards": standards, "suppressions": rules, "history": history}


def anchor(documents, ref):
    doc = documents.get(ref["id"].casefold())
    return doc["anchors"].get(ref["location"], "") if doc else ""


def source_match(quote, source):
    return sum(not c.isspace() for c in quote) >= 8 and quote in source


def suppress(row, rules, source, baseline):
    for rule in rules:
        if (rule["dimension"], rule["field"]) != (row["dimension"], row["field"]):
            continue
        if rule["kind"] == "equivalent":
            actual, expected = source.strip(), baseline.strip()
            values = {value.strip() for value in rule["values"]}
            if actual != expected and {actual, expected} <= values:
                return rule
        elif row["location"] in rule["locations"]:
            if rule["kind"] == "excluded_field" or row["basis"] == rule["basis"]:
                return rule
    return None


def basis_error(row, prepared):
    citation = CITATION.fullmatch(row["basis"])
    if not citation:
        return "缺少可解析的标准号、年号或条款"
    edition, clause = citation.groups()
    standard = prepared["standards"].get(edition)
    if not standard:
        return "版本未列入用户确认的依据表"
    if standard["state"] == "superseded":
        return "引用已被替代的版本"
    reference = standard.get("clauses", {}).get(clause)
    if not reference or not source_match(row["basis_quote"], anchor(prepared["baseline"], reference)):
        return "无本地条款正文或引文无法在对应条款回源"
    return ""


def continuation(row, history, used):
    scope = ("sheet", "location", "dimension", "field", "basis", "evidence")
    matches = []
    for item in history:
        if item["status"] == "open" and all(row[key] == item[key] for key in scope):
            similarity = SequenceMatcher(None, row["problem"], item["problem"], autojunk=False).ratio()
            if similarity >= 0.75:
                matches.append((similarity, item))
    matches.sort(key=lambda match: match[0], reverse=True)
    if matches and matches[0][1]["id"] not in used and (
            len(matches) == 1 or matches[0][0] - matches[1][0] >= 0.05):
        return matches[0]
    return None


def review(prepared, payload):
    require(payload["snapshot"] == prepared["snapshot"], "锁定后输入发生变化，须重新预检")
    ledger = prepared["ledger"]
    expected = {(row["id"], dim) for row in ledger["targets"] for dim in ledger["dimensions"]}
    coverage = {}
    for item in payload["coverage"]:
        key = (item["sheet"], item["dimension"])
        require(key in expected and key not in coverage and item["state"] in ("reviewed", "unavailable")
                and nonempty(item["note"]), "覆盖记录无效或重复")
        coverage[key] = item
    require(set(coverage) == expected, "覆盖记录缺少图号或勾选维度")
    rows = payload["candidates"]
    overrides = payload.get("keep_new", [])
    require(isinstance(rows, list) and isinstance(overrides, list) and all(nonempty(v) for v in overrides),
            "候选或还原清单格式错误")
    result = {"opinions": [], "continuations": [], "pending": [], "suppressed": [],
              "coverage": list(coverage.values()), "ledger": ledger, "snapshot": prepared["snapshot"]}
    seen = set()
    used_history = set()
    location_failures = basis_failures = 0
    fields = ("id", "sheet", "dimension", "field", "problem", "advice", "severity")
    for row in rows:
        require(all(nonempty(row[k]) for k in fields) and row["id"] not in seen and
                row["severity"] in LEVELS, "候选 ID 重复、字段缺失或严重程度不合法")
        require(all(isinstance(row[k], str) for k in
                    ("location", "basis", "basis_quote", "evidence", "baseline_quote")),
                "位置和证据字段须为字符串")
        key = (row["sheet"], row["dimension"])
        require(key in expected and coverage[key]["state"] == "reviewed", "候选来自未覆盖维度")
        seen.add(row["id"])
        source = anchor(prepared["targets"], {"id": row["sheet"], "location": row["location"]})
        baseline = anchor(prepared["baseline"], row["baseline_ref"])
        located = source_match(row["evidence"], source)
        grounded = source_match(row["baseline_quote"], baseline)
        if not located:
            location_failures += 1
        basis = basis_error(row, prepared)
        if basis:
            basis_failures += 1
        rule = suppress(row, prepared["suppressions"], source, baseline) if located and grounded else None
        if rule:
            result["suppressed"].append({"candidate": row, "rule": rule})
            continue
        reasons = []
        if not located:
            reasons.append("定位失败：指定图号及位置未找到足够长的逐字证据")
        if not grounded:
            reasons.append("基准待核：指定基准位置未找到足够长的逐字证据")
        if basis:
            reasons.append("依据待核：" + basis)
        if reasons:
            result["pending"].append({"candidate": row, "reasons": reasons})
            continue
        match = continuation(row, prepared["history"], used_history) if row["id"] not in overrides else None
        if match:
            score, prior = match
            used_history.add(prior["id"])
            result["continuations"].append({"candidate": row, "previous": prior, "similarity": round(score, 3)})
        else:
            result["opinions"].append(row)
    require(set(overrides) <= seen, "还原清单包含不存在的候选 ID")
    result["opinions"].sort(key=lambda row: (LEVELS.index(row["severity"]), row["sheet"], row["location"], row["id"]))
    counts = {key: len(result[key]) for key in ("opinions", "continuations", "pending", "suppressed")}
    total = len(rows)
    require(sum(counts.values()) == total, "分流指标与明细不一致")
    result["metrics"] = dict(counts, candidates=total, merged=counts["continuations"],
                             location_failures=location_failures, basis_failures=basis_failures,
                             location_failure_rate=location_failures / total if total else None,
                             basis_pending_rate=basis_failures / total if total else None)
    return result


def cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(
        "|", "&#124;").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "&#10;").replace(
        "`", "&#96;").replace("[", "&#91;").replace("]", "&#93;").replace("\\", "&#92;")


def details(items):
    return ["- " + cell(json.dumps(item, ensure_ascii=False)) for item in items] or ["无"]


def finding(row):
    location = row["location"] if row["location"].strip() else "未取得"
    return cell(f'{row["id"]} · {row["sheet"]} / {location} · {row["problem"]}')


def markdown(result):
    ledger = result["ledger"]
    lines = ["# 对照校审", "", "## 1. 校审台账", ""]
    if ledger["reference_only"]:
        lines += ["**仅供参考。** 本轮未启用禁止提规则，误报风险需人工评估。", ""]
    lines += [f'- 校审日期 {ledger["review_date"]}，规则版本 {cell(ledger["rules_version"])}',
              "- 锁定快照 " + result["snapshot"],
              f'- 禁止提规则 {ledger["suppression_rules"]} 条，维度 {"、".join(ledger["dimensions"])}',
              "- 基准目录 " + cell(ledger["baseline_dir"])]
    lines += details(ledger["baseline"]) + ["- 待审目录 " + cell(ledger["target_dir"])]
    lines += details(ledger["targets"]) + ["", "### 逐图覆盖记录（由模型申报）", ""]
    lines += details(result["coverage"]) + ["", "## 2. 意见表", "",
                                          "| " + " | ".join(HEADER) + " |",
                                          "| " + " | ".join(["---"] * len(HEADER)) + " |"]
    for index, row in enumerate(result["opinions"], 1):
        values = [index] + [row[key] for key in ("sheet", "location", "problem", "basis",
                                                "advice", "severity", "evidence")]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    if result["opinions"]:
        lines += ["", "### 基准回源", ""]
        for index, row in enumerate(result["opinions"], 1):
            reference = row["baseline_ref"]
            lines.append(f'- {index}. ' + cell(f'{reference["id"]} / {reference["location"]} · '
                         f'{row["baseline_quote"]}。条款引文 {row["basis_quote"]}'))
    lines += ["", "## 3. 延续项", ""]
    lines += [f'- {finding(item["candidate"])}。上轮 {cell(item["previous"]["date"])} '
              f'{cell(item["previous"]["id"])}，描述相似度 {item["similarity"]:.1%}。'
              f'上轮意见 {cell(item["previous"]["problem"])}'
              for item in result["continuations"]] or ["无"]
    lines += ["", "## 4. 待人工确认", ""]
    lines += [f'- {finding(item["candidate"])}。{cell("；".join(item["reasons"]))}'
              for item in result["pending"]] or ["无"]
    lines += ["", "## 5. 抑制清单", ""]
    lines += [f'- {finding(item["candidate"])}。命中规则 {cell(json.dumps(item["rule"], ensure_ascii=False))}'
              for item in result["suppressed"]] or ["无"]
    metrics = result["metrics"]
    def rate(key):
        return "未取得" if metrics[key] is None else f"{metrics[key]:.1%}"
    lines += ["", "## 6. 指标页", "",
              f'- 候选 {metrics["candidates"]}，入表 {metrics["opinions"]}，抑制 {metrics["suppressed"]}，待确认 {metrics["pending"]}，合并 {metrics["merged"]}',
              f'- 定位失败率 {rate("location_failure_rate")}，依据待核率 {rate("basis_pending_rate")}。'
              '分母均为全部候选，分子包含已抑制的候选。',
              "", "## 7. 中止或拒绝说明", ""]
    unavailable = [item for item in result["coverage"] if item["state"] == "unavailable"]
    lines += details(unavailable)
    lines += ["", "## 8. 口径声明", "", DISCLAIMER, "",
              "脚本验证文本回源与分流规则。条款适用性和意见语义由人工复核。", ""]
    return "\n".join(lines)


def output(text, path, prepared):
    if path is None:
        print(text)
        return
    path = path.resolve()
    for key in ("baseline_dir", "target_dir"):
        root = Path(prepared["ledger"][key])
        require(root != path and root not in path.parents, "输出须位于输入目录之外")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fingerprint = commands.add_parser("hash")
    fingerprint.add_argument("file", type=Path)
    preflight = commands.add_parser("prepare")
    preflight.add_argument("config", type=Path)
    preflight.add_argument("--out", type=Path)
    check = commands.add_parser("review")
    check.add_argument("config", type=Path)
    check.add_argument("candidates", type=Path)
    check.add_argument("--out", type=Path)
    check.add_argument("--format", choices=("md", "json"), default="md")
    args = parser.parse_args()
    if args.command == "hash":
        print(digest(args.file.read_bytes()))
        return 0
    try:
        prepared = prepare(args.config.resolve())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"《基准冲突或输入中止报告》\n- 原因 {exc}\n- 补齐或核对已确认的清单及源文件后重试。", file=sys.stderr)
        return 2
    try:
        if args.command == "prepare":
            text = json.dumps(prepared, ensure_ascii=False, indent=2)
        else:
            result = review(prepared, decode(args.candidates.read_bytes()))
            text = markdown(result) if args.format == "md" else json.dumps(result, ensure_ascii=False, indent=2)
        output(text, args.out, prepared)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"《交付中止报告》\n- 原因 {exc}\n- 核对快照、候选、覆盖或输出路径后重试。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
