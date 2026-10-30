# MenuTitle: Check Character Coverage
# -*- coding: utf-8 -*-
"""Check the open Glyphs font against src-external/coverage/*.txt.

Read every Unicode assignment directly from every glyph in the live font,
including non-exporting glyphs and secondary assignments on shared glyphs.
Write Unicode-sorted character<TAB>uppercase hexadecimal codepoint rows to
out/coverage/. Codepoints use at least four digits, without a U+ prefix.
Run through tools/run_in_glyphs.py or Glyphs' Scripts menu; does not edit the font.
"""

import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent
COVERAGE_DIR = PROJECT / "src-external" / "coverage"
OUTPUT_DIR = PROJECT / "out" / "coverage"


def font_codepoints(font):
    """Use actual assignments, never glyph names or external alias records."""
    codepoints = set()
    for glyph in font.glyphs:
        # glyph.unicode exposes only the first assignment. A custom-named
        # glyph can cover several characters through glyph.unicodes.
        for value in glyph.unicodes or ():
            codepoint = int(value, 16)
            if not 0 <= codepoint <= 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
                raise ValueError("Invalid Unicode assignment %r on %s" % (value, glyph.name))
            codepoints.add(codepoint)
    return codepoints


def read_character_list(path):
    codepoints = set()
    with path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            char = line.rstrip("\r\n")
            if len(char) != 1 or 0xD800 <= ord(char) <= 0xDFFF or char == "\ufeff":
                raise ValueError("Expected one character at %s:%d" % (path, number))
            codepoints.add(ord(char))
    if not codepoints:
        raise ValueError("Empty coverage list: %s" % path)
    return codepoints


def write_characters(path, codepoints):
    # An empty missing set produces an empty file, with no blank character row.
    text = "".join("%s\t%04X\n" % (chr(codepoint), codepoint)
                   for codepoint in sorted(codepoints))
    path.write_text(text, encoding="utf-8")


def check_coverage(font, coverage_dir=COVERAGE_DIR, output_dir=OUTPUT_DIR):
    coverage_dir, output_dir = Path(coverage_dir), Path(output_dir)
    paths = sorted(coverage_dir.glob("*.txt"))
    if not paths:
        raise ValueError("No character lists found in %s" % coverage_dir)
    # Validate every input before replacing any reports.
    required_lists = [(path, read_character_list(path)) for path in paths]
    available = font_codepoints(font)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "font_family": font.familyName,
        "font_path": str(font.filepath) if font.filepath else None,
        "unicode_source": "Live Glyphs font: every glyph.unicodes assignment",
        "includes_non_exporting_glyphs": True,
        "assigned_codepoints": len(available),
        "lists": [],
    }
    all_required = set()
    for path, required in required_lists:
        all_required.update(required)
        missing = required - available
        filename = "missing_" + path.name
        write_characters(output_dir / filename, missing)
        summary["lists"].append({
            "list": path.name,
            "required": len(required),
            "covered": len(required) - len(missing),
            "missing": len(missing),
            "missing_file": filename,
        })
    all_missing = all_required - available
    write_characters(output_dir / "missing_all.txt", all_missing)
    summary["combined"] = {
        "required": len(all_required),
        "covered": len(all_required) - len(all_missing),
        "missing": len(all_missing),
        "missing_file": "missing_all.txt",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main():
    from GlyphsApp import Glyphs

    font = Glyphs.font
    if font is None:
        raise RuntimeError("Open a font in Glyphs first.")
    summary = check_coverage(font)
    print("Font: %s (%d assigned codepoints; includes non-exporting glyphs)" % (
        summary["font_family"], summary["assigned_codepoints"]
    ))
    for entry in summary["lists"]:
        print("%s: %d/%d covered, %d missing" % (
            entry["list"], entry["covered"], entry["required"], entry["missing"]
        ))
    combined = summary["combined"]
    print("Combined: %d/%d covered, %d missing" % (
        combined["covered"], combined["required"], combined["missing"]
    ))
    print("Reports: %s" % OUTPUT_DIR)


if __name__ == "__main__":
    main()
