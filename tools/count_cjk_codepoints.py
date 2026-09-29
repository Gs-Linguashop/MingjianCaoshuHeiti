# MenuTitle: Count CJK Code Points
# -*- coding: utf-8 -*-
"""Paste into Glyphs' Macro Panel and run with a font open.

Save covered characters to out/cjk_characters.txt beside the font file and
print only the total count. The UTF-8 file is overwritten on each run and
contains unique characters in code point order, without separators. Includes all
glyphs in the current font (including non-exporting glyphs) and every Unicode
assignment on each glyph. Duplicate code points are counted only once.

Covers unified ideographs and Extensions A-J, compatibility ideographs and
their supplement, Kangxi Radicals, and CJK Radicals Supplement. Reserved
positions are excluded. Ranges use Unicode 18.0 data rather than Python's
bundled Unicode database, which may lack recent extensions.
Source: https://www.unicode.org/Public/18.0.0/ucd/UnicodeData.txt
"""

import os

from GlyphsApp import Glyphs


CJK_RANGES = (
    (0x2E80, 0x2E99),    # CJK Radicals Supplement (gap at U+2E9A)
    (0x2E9B, 0x2EF3),
    (0x2F00, 0x2FD5),    # Kangxi Radicals
    (0x3400, 0x4DBF),    # Extension A
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0xF900, 0xFA6D),    # CJK Compatibility Ideographs
    (0xFA70, 0xFAD9),
    (0x20000, 0x2A6DF),  # Extension B
    (0x2A700, 0x2B73F),  # Extension C
    (0x2B740, 0x2B81E),  # Extension D
    (0x2B820, 0x2CEAD),  # Extension E
    (0x2CEB0, 0x2EBE0),  # Extension F
    (0x2EBF0, 0x2EE5D),  # Extension I
    (0x2F800, 0x2FA1D),  # CJK Compatibility Ideographs Supplement
    (0x30000, 0x3134A),  # Extension G
    (0x31350, 0x323AF),  # Extension H
    (0x323B0, 0x33479),  # Extension J
)


def main():
    Glyphs.showMacroWindow()
    font = Glyphs.font
    if font is None:
        print("No font open. Open a font and run this macro again.")
        return
    if not font.filepath:
        print("Save the font first so the project folder can be determined.")
        return

    codepoints = set()
    for glyph in font.glyphs:
        # glyph.unicode exposes only the first assignment; use glyph.unicodes.
        for value in glyph.unicodes or ():
            codepoint = int(value, 16)
            if any(start <= codepoint <= end for start, end in CJK_RANGES):
                codepoints.add(codepoint)

    characters = "".join(chr(codepoint) for codepoint in sorted(codepoints))
    output_dir = os.path.join(os.path.dirname(font.filepath), "out")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "cjk_characters.txt")
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(characters)

    print("Total unique CJK code points: {}".format(len(codepoints)))


main()
