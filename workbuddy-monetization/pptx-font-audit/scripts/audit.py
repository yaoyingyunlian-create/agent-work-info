"""Read font references without extracting or modifying the presentation."""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
PART = re.compile(r"ppt/(?:slides/slide\d+|slideLayouts/slideLayout\d+|slideMasters/slideMaster\d+|theme/theme\d+)\.xml$")
MAX_BYTES = 50_000_000


def audit(path):
    path = Path(path)
    if path.suffix.lower() != ".pptx" or path.stat().st_size > MAX_BYTES:
        raise ValueError("Expected a PPTX file no larger than 50 MB")
    fonts, inherited, embedded, relationships = [], [], [], []
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(set(names)) != len(names) or sum(entry.file_size for entry in entries) > 100_000_000:
            raise ValueError("Duplicate parts or uncompressed size limit exceeded")
        if "[Content_Types].xml" not in names or "ppt/presentation.xml" not in names:
            raise ValueError("Missing presentation package parts")
        for entry in entries:
            name = entry.filename
            if entry.flag_bits & 1:
                raise ValueError("Encrypted ZIP entries are unsupported")
            if not (PART.fullmatch(name) or name in ("ppt/presentation.xml", "ppt/_rels/presentation.xml.rels")):
                continue
            tree = ET.fromstring(archive.read(entry))
            slide_match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)
            slide_part_number = int(slide_match[1]) if slide_match else None
            for index, element in enumerate(tree.iter()):
                if element.tag in {A + "latin", A + "ea", A + "cs", A + "font"} and "typeface" in element.attrib:
                    family = element.attrib["typeface"]
                    fonts.append({
                        "part": name, "slide_part_number": slide_part_number,
                        "node_index": index, "slot": element.tag.split("}")[1],
                        "font": family, "status": "theme_reference" if family.startswith("+") else "declared",
                        "rendering_risk": "unknown",
                    })
                if slide_match and element.tag == A + "r":
                    text = "".join(t.text or "" for t in element.findall(A + "t"))
                    if re.search("[\u3400-\u9fff]", text):
                        properties = element.find(A + "rPr")
                        ea = properties.find(A + "ea") if properties is not None else None
                        if ea is None or not ea.get("typeface"):
                            inherited.append({"part": name, "node_index": index,
                                              "status": "CJK inherits font; effective font unresolved"})
                if name == "ppt/presentation.xml" and element.tag in {P + "regular", P + "bold", P + "italic", P + "boldItalic"}:
                    rid = element.get(R + "id")
                    if rid:
                        embedded.append({"style": element.tag.split("}")[1], "relationship_id": rid})
                if name == "ppt/_rels/presentation.xml.rels" and element.tag == REL + "Relationship":
                    relationships.append(element.attrib)
        rels = {rel.get("Id"): rel for rel in relationships}
        for font in embedded:
            relationship = rels.get(font["relationship_id"])
            font["relationship_found"] = relationship is not None
            if relationship:
                font["target"] = relationship.get("Target")
        return {
            "font_references": fonts,
            "cjk_inheritance_checks": inherited,
            "embedded_font_references": embedded,
            "font_parts": sorted(name for name in names if name.startswith("ppt/fonts/") and not name.endswith("/")),
            "limitations": [
                "XML references are not resolved rendered fonts.",
                "Slide part numbers may differ from displayed slide order.",
                "Embedding references and files do not prove embedding rights or availability on another machine.",
            ],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("presentation", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.presentation)
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, RuntimeError) as error:
        parser.exit(2, f"Cannot audit PPTX: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
