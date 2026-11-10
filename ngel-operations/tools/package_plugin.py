"""Build Ngel's self-contained plugin and marketplace archives."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/ngel-operations"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    for name in ("agent-rules.json", "schedules.json"):
        write_json(PLUGIN / "assets/config" / name, json.loads((ROOT / "config" / name).read_text(encoding="utf-8")))
    knowledge = json.loads((ROOT / "knowledge/ngel-faq.draft.json").read_text(encoding="utf-8"))
    knowledge["source"] = "User-provided bilingual knowledge source, imported 2026-11-03"
    write_json(PLUGIN / "assets/knowledge/ngel-faq.draft.json", knowledge)
    (PLUGIN / "references/requirements.md").write_text((ROOT / "docs/NGEL需求方案.md").read_text(encoding="utf-8"), encoding="utf-8")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    files = sorted(p for p in PLUGIN.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    version = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
    archives = {
        f"ngel-operations-{version}.zip": [(p, p.relative_to(PLUGIN).as_posix()) for p in files],
        f"ngel-marketplace-{version}.zip": [(p, p.relative_to(ROOT).as_posix()) for p in files] + [
            (ROOT / ".agents/plugins/marketplace.json", ".agents/plugins/marketplace.json")],
    }
    checksums = []
    for name, contents in archives.items():
        destination = dist / name
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, relative in contents:
                archive.write(path, relative)
        with zipfile.ZipFile(destination) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"Corrupt archive: {name}")
        checksums.append(f"{hashlib.sha256(destination.read_bytes()).hexdigest()}  {name}")
        print(f"PACKAGED {destination} ({len(contents)} files)")
    (dist / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
