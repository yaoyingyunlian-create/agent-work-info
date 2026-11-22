"""Rebuild the WorkBuddy expert with an existing, validated skill release."""

import argparse
import json
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
CONFIG = ".codebuddy-plugin/plugin.json"


def package(skill_zip, output):
    config = json.loads((ROOT / CONFIG).read_text(encoding="utf-8"))
    agent = PurePosixPath(config["agents"][0]).as_posix()
    skill = PurePosixPath(config["skills"][0]).as_posix()
    if len(config["tags"]) != 3 or not 3 <= len(config["quickPrompts"]) <= 10:
        raise ValueError("WorkBuddy requires 3 tags and 3 to 10 quick prompts.")

    files = {
        name: (ROOT / name).read_bytes()
        for name in (CONFIG, agent, config["avatar"])
    }
    with ZipFile(skill_zip) as archive:
        names = [item.filename for item in archive.infolist() if not item.is_dir()]
        if "SKILL.md" not in names or len(names) != len(set(names)):
            raise ValueError("Expected a standalone WorkBuddy skill release.")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
                raise ValueError(f"Invalid skill archive path: {name}")
            files[f"{skill}/{name}"] = archive.read(name)

    with ZipFile(output, "x", ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(f"{config['name']}/{name}", data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-zip", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    package(arguments.skill_zip, arguments.output)
