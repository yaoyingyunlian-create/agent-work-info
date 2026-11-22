"""Generate a complete simulated review workspace."""
import argparse
import json
from pathlib import Path
import sys

from review import digest, prepare


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def build(destination):
    fixture = Path(__file__).resolve().parents[1] / "assets" / "demo.json"
    sample = json.loads(fixture.read_text(encoding="utf-8"))
    destination = destination.resolve()
    destination.mkdir()
    for name in ("baseline", "targets"):
        (destination / name).mkdir()
    baseline = destination / "baseline" / "approved.json"
    save(baseline, sample["baseline"])
    save(destination / "targets" / "sheet.json", sample["target"])
    config = sample["config"]
    config["baseline"][0]["sha256"] = digest(baseline.read_bytes())
    config_path = destination / "config.json"
    save(config_path, config)
    candidates = sample["candidates"]
    candidates["snapshot"] = prepare(config_path)["snapshot"]
    save(destination / "candidates.json", candidates)
    return config_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="A new directory")
    args = parser.parse_args()
    try:
        config_path = build(args.destination)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    folder = config_path.parent
    print("演示资料为虚构内容。运行以下命令生成演示校审报告。")
    print(f'python -X utf8 scripts/review.py prepare "{config_path}" --out "{folder / "prepared.json"}"')
    print(f'python -X utf8 scripts/review.py review "{config_path}" "{folder / "candidates.json"}" --out "{folder / "review.md"}"')


if __name__ == "__main__":
    sys.exit(main())
