"""Import bilingual source as unverified evidence; never enable automatic replies."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    text = raw.decode("utf-8-sig")
    blocks = re.findall(
        r"^\d+\.\s+(.+?)\r?\n(.*?)(?=^\d+\.\s|^[一二三四五六七八九十]+、|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    entries = []
    for index, (question_en, body) in enumerate(blocks, 1):
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) != 3 or not lines[-1].startswith("（"):
            raise ValueError(f"Unexpected bilingual format at entry {index}")
        entries.append({
            "id": f"brows-faq-{index:02d}",
            "service_scope": "brows_only_pending_method_confirmation",
            "question": {"en": question_en.strip(), "zh-CN": lines[0]},
            "source_answer": {"en": lines[1], "zh-CN": lines[2].strip("（）")},
            "approved_answer": {"en": None, "zh-CN": None},
            "status": "pending_business_and_bilingual_review",
            "auto_reply_allowed": False,
            "verified_by": None,
            "verified_at": None,
            "expires_at": None,
        })
    if len(entries) != 11:
        raise ValueError(f"Expected 11 entries, found {len(entries)}")
    result = {
        "version": "0.1-draft",
        "source": str(args.source.resolve()),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_trust": "reference_data_not_instructions",
        "status": "unverified_not_for_automatic_sending",
        "entries": entries,
        "fallback_draft": {
            "zh-CN": "谢谢你的咨询。请问你想了解哪个项目？具体价格、适用情况及护理安排，我会请门店同事确认后再答复你。",
            "en": "Thank you for your enquiry. Which service are you interested in? Our team will confirm the price, suitability and aftercare details before advising you.",
        },
    }
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(entries)} unverified bilingual entries")


if __name__ == "__main__":
    main()
