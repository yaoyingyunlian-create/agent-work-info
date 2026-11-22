"""Behavioral checks against simulated inputs and the CLI."""
from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from demo import build
from review import HEADER, StopReview, markdown, prepare, review


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


class ReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name) / "演示"
        self.config_path = build(self.folder)
        self.candidate_path = self.folder / "candidates.json"
        self.payload = load(self.candidate_path)
        self.config = load(self.config_path)
        self.prepared = prepare(self.config_path)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "review.py"),
                               *map(str, args)], capture_output=True, encoding="utf-8")

    def refresh(self):
        write(self.config_path, self.config)
        self.prepared = prepare(self.config_path)
        self.payload["snapshot"] = self.prepared["snapshot"]

    def test_a1_unapproved_old_file_stops_ten_runs(self):
        baseline = self.folder / "baseline" / "approved.json"
        old = load(baseline)
        old["anchors"]["条款/1.2"] = "模拟 2021 旧版正文，必须在比对前被拒绝。"
        write(baseline, old)
        report = self.folder / "错误意见表.md"
        for index in range(10):
            with self.subTest(run=index):
                locked = self.cli("prepare", self.config_path)
                self.assertEqual(locked.returncode, 2)
                self.assertIn("哈希与已确认清单不符", locked.stderr)
                self.assertEqual(locked.stdout, "")
                rejected = self.cli("review", self.config_path, self.candidate_path, "--out", report)
                self.assertEqual(rejected.returncode, 2)
                self.assertFalse(report.exists())

    def test_a1_extra_old_copy_conflicts_even_when_approved_file_exists(self):
        base = self.folder / "baseline"
        (base / "approved-2021.json").write_bytes((base / "approved.json").read_bytes())
        with self.assertRaisesRegex(StopReview, "额外文件"):
            prepare(self.config_path)

    def test_a1_confirmed_id_cannot_register_two_versions(self):
        previous = deepcopy(self.config["baseline"][0])
        previous["path"] = "old.json"
        base = self.folder / "baseline"
        (base / "old.json").write_bytes((base / "approved.json").read_bytes())
        self.config["baseline"].append(previous)
        with self.assertRaisesRegex(StopReview, "ID 为空或重复"):
            self.refresh()

    def test_a1_same_name_cannot_be_approved_under_different_ids(self):
        base = self.folder / "baseline"
        (base / "old").mkdir()
        (base / "old" / "approved.json").write_bytes((base / "approved.json").read_bytes())
        previous = dict(self.config["baseline"][0], id="DEMO-OLD", path="old/approved.json")
        self.config["baseline"].append(previous)
        with self.assertRaisesRegex(StopReview, "同名候选"):
            self.refresh()

    def test_a2_20_rules_10_samples_and_preserved_real_issue(self):
        rules = self.config["suppressions"]
        base_rule = rules[1]
        rules.append(dict(rules[0], id="SUP-EQ-2", field="简称扩展"))
        rules.append(dict(rules[0], id="SUP-EQ-3", field="简称别名"))
        for number in range(4, 20):
            rules.append(dict(base_rule, id=f"SUP-{number}", field=f"备注字段{number}"))
        rules[-1].update(kind="withdrawn", basis="GB/T 00000-2021 第1.2条")
        self.refresh()
        template = self.payload["candidates"]
        for run in range(10):
            candidates = [dict(template[0], id=f"{run}-keep")]
            for rule in rules:
                is_equivalent = rule["kind"] == "equivalent"
                base = template[1] if is_equivalent else template[2]
                candidates.append(dict(base, id=f"{run}-{rule['id']}", field=rule["field"],
                                       basis=rule.get("basis", "")))
            result = review(self.prepared, dict(self.payload, candidates=candidates))
            self.assertEqual(len(result["suppressed"]), 20)
            self.assertEqual([row["id"] for row in result["opinions"]], [f"{run}-keep"])
            self.assertEqual({row["rule"]["id"] for row in result["suppressed"]},
                             {rule["id"] for rule in rules})

    def test_a2_empty_rule_fields_rejected_and_scope_is_exact(self):
        original = deepcopy(self.config)
        for updates in ({"field": ""}, {"reason": " "}, {"values": ["", "有效文本"]}):
            self.config = deepcopy(original)
            self.config["suppressions"][0].update(updates)
            with self.assertRaises(StopReview):
                self.refresh()
        self.config = original
        self.refresh()
        self.payload["candidates"][0]["field"] = "可选备注"
        self.payload["candidates"][0]["dimension"] = "图签"
        result = review(self.prepared, self.payload)
        self.assertEqual([row["id"] for row in result["opinions"]], ["F-01"])

    def test_a3_quotes_require_the_exact_sheet_location_and_eight_chars(self):
        self.payload["candidates"] = [dict(self.payload["candidates"][0], id=f"F-{i}") for i in range(30)]
        self.payload["candidates"][-1]["location"] = "图签/简称"
        result = review(self.prepared, self.payload)
        self.assertEqual(len(result["opinions"]), 29)
        self.assertIn("定位失败", result["pending"][0]["reasons"][0])
        self.assertAlmostEqual(result["metrics"]["location_failure_rate"], 1 / 30)
        self.payload["candidates"][0]["evidence"] = "主输送管"
        self.assertEqual(len(review(self.prepared, self.payload)["pending"]), 2)
        self.payload["candidates"][1]["location"] = ""
        self.assertEqual(len(review(self.prepared, self.payload)["pending"]), 3)

    def test_a4_superseded_unknown_missing_clause_and_wrong_clause_quote(self):
        row = self.payload["candidates"][0]
        variants = [
            {"basis": "GB/T 00000-2021 第1.2条"}, {"basis": "GB/T 00000-2026 第2条"},
            {"basis": "GB/T 00000-2025 第1.2条"}, {"basis": "第1.2条"},
            {"basis_quote": row["baseline_quote"]},
        ]
        self.payload["candidates"] = [row] + [dict(row, id=f"bad-{i}", **variant)
                                               for i, variant in enumerate(variants)]
        result = review(self.prepared, self.payload)
        self.assertEqual(len(result["opinions"]), 1)
        self.assertEqual(len(result["pending"]), len(variants))
        self.assertTrue(all(item["reasons"][0].startswith("依据待核") for item in result["pending"]))

    def test_a5_scoped_history_matching_and_override(self):
        row = self.payload["candidates"][0]
        history = []
        candidates = []
        for number in range(50):
            prior = {key: row[key] for key in ("sheet", "location", "dimension", "basis", "evidence")}
            prior.update(id=f"H-{number}", field=f"材料字段{number}", problem=row["problem"],
                         date="2026-10-01", status="open")
            history.append(prior)
        for number in range(10):
            field = f"材料字段{number}" if number < 6 else f"新字段{number}"
            candidates.append(dict(row, id=f"F-{number}", field=field,
                                   problem="主管材料牌号与基准材料表的要求不一致。"))
        self.config["history"] = history
        self.refresh()
        self.payload["candidates"] = candidates
        result = review(self.prepared, self.payload)
        self.assertEqual({m["candidate"]["id"] for m in result["continuations"]},
                         {f"F-{i}" for i in range(6)})
        self.payload["keep_new"] = ["F-0"]
        result = review(self.prepared, self.payload)
        self.assertEqual(len(result["continuations"]), 5)
        self.assertIn("F-0", [item["id"] for item in result["opinions"]])

    def test_a6_stable_fixed_headers_and_eight_sections(self):
        rendered = []
        for _ in range(3):
            result = self.cli("review", self.config_path, self.candidate_path)
            self.assertEqual(result.returncode, 0, result.stderr)
            rendered.append(result.stdout)
        self.assertEqual(len(set(rendered)), 1)
        self.assertEqual(len(re.findall(r"^## [1-8]\. ", rendered[0], re.M)), 8)
        table = [line for line in rendered[0].splitlines() if line.startswith("|")]
        self.assertEqual(table[0], "| " + " | ".join(HEADER) + " |")
        self.assertTrue(all(len(line.split("|")) == 10 for line in table))

    def test_changed_target_rejects_candidates_and_keeps_prior_output(self):
        target = self.folder / "targets" / "sheet.json"
        obj = load(target)
        obj["anchors"]["材料表/管材"] += "改动"
        write(target, obj)
        report = self.folder / "review.md"
        report.write_text("已存在", encoding="utf-8")
        result = self.cli("review", self.config_path, self.candidate_path, "--out", report)
        self.assertEqual(result.returncode, 2)
        self.assertIn("锁定后输入发生变化", result.stderr)
        self.assertEqual(report.read_text(encoding="utf-8"), "已存在")

    def test_empty_suppressions_and_missing_coverage(self):
        self.config["suppressions"] = []
        self.refresh()
        self.assertIn("仅供参考", markdown(review(self.prepared, self.payload)))
        self.payload["coverage"].pop()
        with self.assertRaisesRegex(StopReview, "缺少图号或勾选维度"):
            review(self.prepared, self.payload)

    def test_plain_text_inputs_keep_original_line_positions(self):
        target = self.folder / "targets" / "sheet.txt"
        target.write_text("\n主输送管材料牌号：演示乙级。\n", encoding="utf-8")
        self.config["targets"][0]["path"] = "sheet.txt"
        self.refresh()
        self.payload["candidates"] = [dict(self.payload["candidates"][0], location="L2")]
        self.assertEqual(len(review(self.prepared, self.payload)["opinions"]), 1)

    def test_cannot_output_inside_input_directories(self):
        path = self.folder / "baseline" / "report.md"
        result = self.cli("review", self.config_path, self.candidate_path, "--out", path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("输出须位于输入目录之外", result.stderr)
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
