#!/usr/bin/env python3
"""Rebuild the coverage lists from the pinned sources in ignored raw/.

Requires PyMuPDF and beautifulsoup4. See README.md and sources.json.
Use --check to verify the committed files without writing them.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import zipfile

import fitz
from bs4 import BeautifulSoup


HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def han(char):
    return "CJK UNIFIED IDEOGRAPH" in unicodedata.name(char, "") or (
        "CJK COMPATIBILITY IDEOGRAPH" in unicodedata.name(char, "")
    )


def mainland_common():
    soup = BeautifulSoup(
        (RAW / "mainland-common-1988-shanghai.html").read_bytes(), "html.parser"
    )
    text = soup.select_one("#ivs_content").get_text(" ", strip=True)
    text = text.split("常用字(2500字)", 1)[1]
    text = re.sub(r"[一二三四五六七八九十]+画", "", text)
    text = text.replace("笔画顺序表", "").replace("次常用字(1000字)", "")
    chars = [char for char in text if han(char)]
    require(len(chars) == len(set(chars)) == 3500, "Mainland table extraction changed")
    # Shanghai's transcription has 蟥. The printed reproduction, p. 81
    # (PDF p. 88), and the repository's original list both have 磺.
    require(chars.count("蟥") == 1 and "磺" not in chars, "Review mainland erratum")
    return set(chars) - {"蟥"} | {"磺"}


def gb_sets():
    with zipfile.ZipFile(RAW / "unihan-17.0.0.zip") as archive:
        text = archive.read("Unihan_OtherMappings.txt").decode("utf-8")
    return {
        tag: {chr(int(cp[2:], 16)) for cp in re.findall(
            rf"^(U\+[0-9A-F]+)\t{tag}\t", text, re.MULTILINE
        )}
        for tag in ("kGB0", "kGB1")
    }


def taiwan_common():
    rows = []
    with fitz.open(RAW / "taiwan-6063.pdf") as document:
        for page in document:
            rows.extend(re.findall(
                r"(\d+)\s+(\S)\s+A(\d{5})\s+([0-9A-F]{4,6})",
                page.get_text(sort=True),
            ))
    require(len(rows) == 4808, "Taiwan A-series extraction changed")
    require({int(row[2]) for row in rows} == set(range(1, 4809)), "Taiwan IDs incomplete")
    for serial, char, identifier, codepoint in rows:
        require(int(serial) == int(identifier), "Taiwan serial/ID mismatch")
        require(char == chr(int(codepoint, 16)), "Taiwan glyph/codepoint mismatch")
    return {row[1] for row in rows}


def hong_kong_common():
    rows = {}
    supplementary = {}
    for strokes in range(1, 34):
        soup = BeautifulSoup((RAW / f"hk-strokes-{strokes}.html").read_bytes(), "html.parser")
        for link in soup.select('a[href^="result.jsp"]'):
            identifier = re.search(r"[?&]id=([^&]+)", link["href"]).group(1)
            char = link.get_text(strip=True)
            require(len(char) == 1 and han(char), "Invalid Hong Kong head character")
            target = rows if identifier.isdigit() else supplementary
            require(identifier not in target, "Duplicate Hong Kong ID")
            target[identifier] = char
    require(set(rows) == {f"{i:04}" for i in range(1, 4763)}, "Hong Kong IDs incomplete")
    require(len(supplementary) == 42, "Review Hong Kong supplementary entries")
    return set(rows.values())


def japan_joyo():
    current, old = [], []
    old_rows = 0
    with fitz.open(RAW / "japan-joyo-2010.pdf") as document:
        # PDF pages 11–161 contain the main table. Restrict extraction to
        # the character column; example words and notes are outside it.
        for page in list(document)[10:161]:
            for x0, y0, x1, y1, word, *_ in page.get_text("words"):
                if 60 < x0 < 75 and len(word) == 1 and han(word):
                    current.append(word)
                if 75 < x0 < 110 and word.startswith("（"):
                    old_rows += 1
                    old.extend(char for char in word if han(char))
    require(len(current) == len(set(current)) == 2136, "Japanese current forms changed")
    require(old_rows == 361 and len(old) == len(set(old)) == 360, "Japanese old forms changed")
    # These four glyphs are drawn rather than extractable text. Checked
    # visually on PDF p. 33 (亀 → 龜) and p. 139 (弁 → 辨, 瓣, 辯).
    old.extend("龜辨瓣辯")
    require(len(set(old)) == 364, "Japanese kyujitai incomplete")
    require(not set(current) & set(old), "Unexpected current/old overlap")
    return set(current) | set(old)


def korea_basic_hanja():
    with fitz.open(RAW / "korea-textbook-compilation-2023.pdf") as document:
        # Printed/PDF pages 50–62 contain only the table and Korean headings.
        text = "\n".join(page.get_text() for page in list(document)[49:62])
    require(text.count("\x02") == 1, "Review Korean unmapped glyph")
    # 沿, printed/PDF p. 57, 연 row; verified against the rendered page.
    text = text.replace("\x02", "沿")
    chars = [char for char in text if han(char)]
    require(len(chars) == len(set(chars)) == 1800, "Korean table extraction changed")
    # Korean compatibility codepoints here distinguish readings rather
    # than additional shapes. Use their unified equivalents for coverage.
    result = {unicodedata.normalize("NFC", char) for char in chars}
    require(len(result) == 1800, "Korean normalization changed membership count")
    return result


def serialize(chars, count):
    require(len(chars) == count, f"Expected {count} characters, got {len(chars)}")
    require(all(len(char) == 1 and han(char) for char in chars), "Invalid character")
    return ("\n".join(sorted(chars, key=ord)) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without writing")
    args = parser.parse_args()
    manifest = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    for source in manifest["raw_sources"]:
        data = (RAW / source["file"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == source["sha256"],
                f"Source checksum mismatch: {source['file']}")
    gb = gb_sets()
    lists = {
        "mainland_china_frequently_used_characters_1988.txt": mainland_common(),
        "mainland_china_gb2312_1980.txt": gb["kGB0"],
        "mainland_china_gb12345_1990.txt": gb["kGB1"],
        "taiwan_standard_forms_of_common_national_characters.txt": taiwan_common(),
        "hong_kong_graphemes_of_commonly_used_characters.txt": hong_kong_common(),
        "japan_joyo_kanji_2010_with_kyujitai.txt": japan_joyo(),
        "south_korea_basic_hanja_for_educational_use.txt": korea_basic_hanja(),
    }
    for entry in manifest["lists"]:
        filename = entry["file"]
        data = serialize(lists[filename], entry["count"])
        require(hashlib.sha256(data).hexdigest() == entry["sha256"],
                f"Output checksum mismatch: {filename}")
        if args.check:
            require((HERE / filename).read_bytes() == data, f"Output differs: {filename}")
        else:
            (HERE / filename).write_bytes(data)
        print(f"{filename}: {entry['count']}")


if __name__ == "__main__":
    main()
