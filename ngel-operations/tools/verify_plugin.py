"""Exercise packaged workspace initialization and knowledge publication guard."""
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="ngel-plugin-check-") as temporary:
        target = Path(temporary)
        version = json.loads((ROOT / "plugins/ngel-operations/.codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
        with zipfile.ZipFile(ROOT / f"dist/ngel-marketplace-{version}.zip") as archive:
            assert archive.testzip() is None
            archive.extractall(target)
        marketplace = json.loads((target / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        plugin = target / marketplace["plugins"][0]["source"]["path"]
        manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        assert (plugin / manifest["skills"]).is_dir()
        assert (plugin / manifest["extensions"]["com.openai"]["onboardingSkill"]).is_file()
        for path in plugin.rglob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))
        workspace = target / "workspace"
        command = [sys.executable, "-X", "utf8", str(plugin / "scripts/workspace.py")]

        def run(action):
            return subprocess.run(command + [action, "--workspace", str(workspace)],
                                  capture_output=True, text=True, encoding="utf-8")

        first = run("init")
        assert first.returncode == 0, first.stderr
        assert '"external_systems_tested": false' in first.stdout
        business_path = workspace / "config/business.json"
        business = json.loads(business_path.read_text(encoding="utf-8"))
        business["boss_recipient"] = "operator-test-marker"
        business_path.write_text(json.dumps(business), encoding="utf-8")
        original = business_path.read_bytes()
        assert run("init").returncode == 0
        assert business_path.read_bytes() == original, "init overwrote existing configuration"
        onboarding = [sys.executable, "-X", "utf8", str(plugin / "scripts/onboarding.py")]

        def intake(action, *extra):
            return subprocess.run(onboarding + [action, "--workspace", str(workspace)] + list(extra),
                                  capture_output=True, text=True, encoding="utf-8")

        questions = json.loads(intake("status").stdout)
        assert len(questions["next_questions"]) == 3
        answer_path = target / "answer.json"
        answer_path.write_text(json.dumps({"id": "platform_accounts", "value": [
            {"platform": "test", "account": "test-only"}]}), encoding="utf-8")
        applied = intake("apply", "--answer-file", str(answer_path))
        assert applied.returncode == 0, applied.stderr
        assert "platform_accounts" not in json.loads(applied.stdout)["missing"]
        deferred = intake("defer", "--field", "staff_source")
        deferred_state = json.loads(deferred.stdout)
        assert "staff_source" in deferred_state["missing"]
        assert "staff_source" not in [q["id"] for q in deferred_state["next_questions"]]
        intake("resume", "--field", "staff_source")
        answer_path.write_text(json.dumps({"id": "send_reply", "value": True}), encoding="utf-8")
        assert intake("apply", "--answer-file", str(answer_path)).returncode == 1
        rules = json.loads((workspace / "config/agent-rules.json").read_text(encoding="utf-8"))
        assert not rules["permissions"]["send_reply"]
        assert not rules["timezone_confirmed"]
        before_timezone = (workspace / "config/agent-rules.json").read_bytes()
        answer_path.write_text(json.dumps({"id": "timezone", "value": "Invalid/Imaginary_Zone"}), encoding="utf-8")
        assert intake("apply", "--answer-file", str(answer_path)).returncode == 1
        assert (workspace / "config/agent-rules.json").read_bytes() == before_timezone
        answer_path.write_text(json.dumps({"id": "timezone", "value": "UTC"}), encoding="utf-8")
        assert intake("apply", "--answer-file", str(answer_path)).returncode == 0
        for relative in ("config/agent-rules.json", "config/schedules.json"):
            assert json.loads((workspace / relative).read_text(encoding="utf-8"))["timezone"] == "UTC"
        strict = subprocess.run(command + ["check", "--workspace", str(workspace), "--strict"],
                                capture_output=True, text=True, encoding="utf-8")
        assert strict.returncode == 2 and not json.loads(strict.stdout)["live_ready"]
        kb_path = workspace / "knowledge/ngel-faq.json"
        kb = json.loads(kb_path.read_text(encoding="utf-8"))
        assert len(kb["entries"]) == 11
        kb["entries"][0]["auto_reply_allowed"] = True
        kb_path.write_text(json.dumps(kb), encoding="utf-8")
        bad = run("check")
        assert bad.returncode == 1 and "lacks bilingual verification" in bad.stdout
        kb["entries"][0]["auto_reply_allowed"] = False
        kb["entries"].append(kb["entries"][0])
        kb_path.write_text(json.dumps(kb), encoding="utf-8")
        duplicate = run("check")
        assert duplicate.returncode == 1 and "duplicate knowledge id" in duplicate.stdout
        kb["entries"].pop()
        entry = kb["entries"][0]
        entry.update(auto_reply_allowed=True, status="verified", verified_by="test reviewer",
                     verified_at="2000-01-01T00:00:00Z", expires_at="2001-01-01T00:00:00Z",
                     approved_answer={"zh-CN": "测试答案", "en": "Test answer"})
        kb_path.write_text(json.dumps(kb), encoding="utf-8")
        expired = run("check")
        assert expired.returncode == 1 and "expired" in expired.stdout
        assert json.loads(expired.stdout)["verified_auto_reply_entries"] == 0
        entry["expires_at"] = "2999-01-01T00:00:00Z"
        kb_path.write_text(json.dumps(kb), encoding="utf-8")
        valid = run("check")
        assert valid.returncode == 0 and json.loads(valid.stdout)["verified_auto_reply_entries"] == 1
        entry["approved_answer"]["en"] = "  "
        kb_path.write_text(json.dumps(kb), encoding="utf-8")
        assert run("check").returncode == 1
        entry["approved_answer"]["en"] = "Test answer"
        entry["verified_at"] = "2000-01-01"
        kb_path.write_text(json.dumps(kb), encoding="utf-8")
        assert run("check").returncode == 1
    print("PASS: package portability, non-overwrite, staged onboarding, permission isolation, invalid timezone rejection, timezone sync, strict readiness, duplicate IDs, expired/blank/invalid-date knowledge rejection, valid bilingual knowledge count")


if __name__ == "__main__":
    main()
