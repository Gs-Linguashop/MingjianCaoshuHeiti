# MenuTitle: Create Missing Fullwidth Glyphs
# -*- coding: utf-8 -*-
"""Create fullwidth glyphs from src-external/fullwidth-glyph-map.txt.

Use one unscaled source component per master, centered horizontally in one em.
Keep the source's vertical position. Skip existing targets and missing sources.
Run through tools/run_in_glyphs.py or Glyphs' Scripts menu; does not save.
"""

from pathlib import Path


MAPPING_FILE = Path(__file__).resolve().parent.parent / "src-external" / "fullwidth-glyph-map.txt"


def read_mappings(path=MAPPING_FILE):
    mappings = []
    with path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip() or line.startswith("#"):
                continue
            # Do not strip the character columns: the space mapping is literal.
            columns = line.rstrip("\r\n").split("\t")
            if len(columns) != 6 or len(columns[0]) != 1 or len(columns[1]) != 1:
                raise ValueError("Invalid mapping at %s:%d" % (path, number))
            target, original = ord(columns[0]), ord(columns[1])
            if columns[2:4] != ["U+%04X" % target, "U+%04X" % original]:
                raise ValueError("Mismatched code points at %s:%d" % (path, number))
            mappings.append((target, original))
    return mappings


def create_fullwidth_glyphs(font, mappings, glyph_factory, component_factory):
    # Include secondary Unicode assignments and custom glyph names.
    by_unicode = {}
    for glyph in font.glyphs:
        for code in glyph.unicodes or ():
            by_unicode.setdefault(int(code, 16), glyph)

    created = []
    for target, original in mappings:
        name = "uni%04X" % target
        if target in by_unicode or font.glyphs[name] is not None:
            print("Skipping U+%04X: fullwidth glyph already exists." % target)
            continue
        source = by_unicode.get(original)
        if source is None:
            print("Skipping U+%04X: source U+%04X is missing." % (target, original))
            continue
        if any(source.layers[master.id] is None for master in font.masters):
            print("Skipping U+%04X: source %s is missing a master layer." % (target, source.name))
            continue

        glyph = glyph_factory(name)
        # Glyphs may turn uniFF03 into a nice name such as numbersign.full.
        if font.glyphs[glyph.name] is not None:
            print("Skipping U+%04X: glyph name %s already exists." % (target, glyph.name))
            continue
        glyph.unicode = "%04X" % target
        font.glyphs.append(glyph)
        try:
            for master in font.masters:
                layer = glyph.layers[master.id]
                source_layer = source.layers[master.id]
                component = component_factory(source.name)
                layer.components.append(component)
                component.automaticAlignment = False
                # Empty components can report a placeholder box in Glyphs.
                if source_layer.paths or source_layer.components:
                    bounds = component.bounds
                    x = (font.upm - bounds.size.width) / 2 - bounds.origin.x
                else:
                    # Spaces have no ink bounds; center their advance instead.
                    x = (font.upm - source_layer.width) / 2
                component.position = (x, 0)
                layer.width = font.upm
        except Exception:
            # Remove only the incomplete new glyph if a master could not be built.
            del font.glyphs[glyph.name]
            raise
        by_unicode[target] = glyph
        created.append(glyph.name)
        print("Created U+%04X: %s from %s" % (target, glyph.name, source.name))
    return created


def main():
    from GlyphsApp import Glyphs, GSComponent, GSGlyph

    font = Glyphs.font
    if font is None:
        print("Open a font in Glyphs first.")
        return
    mappings = read_mappings()
    font.disableUpdateInterface()
    try:
        created = create_fullwidth_glyphs(font, mappings, GSGlyph, GSComponent)
    finally:
        font.enableUpdateInterface()
    print("Created %d fullwidth glyphs. Review the font and save when ready." % len(created))
    if created:
        font.newTab("/" + "/".join(created))


if __name__ == "__main__":
    main()
