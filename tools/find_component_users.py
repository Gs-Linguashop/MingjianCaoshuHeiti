#!/usr/bin/env python3
"""Find all glyphs that use a given component (or its alts) in the Glyphs package.

Usage:
    python tools/find_component_users.py [component_base]

Default component_base is uni2E94.
"Alts" are any glyphs whose name starts with component_base followed by '.'
(e.g. uni2E94.alt, uni2E94.alt2).
"""

import os
import re
import sys


def find_component_users(package_dir, component_base):
    glyphs_dir = os.path.join(package_dir, "glyphs")
    if not os.path.isdir(glyphs_dir):
        print(f"  No glyphs directory: {glyphs_dir}")
        return [], set()

    glyphname_pat = re.compile(r'glyphname\s*=\s*([^;]+);')
    ref_pat = re.compile(r'\bref\s*=\s*([^;]+);')

    # Pass 1: collect all glyphname -> file content, identify target components
    target_components = set()
    glyph_contents = {}  # glyphname -> file content

    for fname in sorted(os.listdir(glyphs_dir)):
        if not fname.endswith(".glyph"):
            continue
        fpath = os.path.join(glyphs_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            content = f.read()

        m = glyphname_pat.search(content)
        if not m:
            continue
        glyphname = m.group(1).strip()
        glyph_contents[glyphname] = content

        if glyphname == component_base or glyphname.startswith(component_base + "."):
            target_components.add(glyphname)

    if not target_components:
        target_components = {component_base}

    # Pass 2: find every glyph that references any target component
    users = []
    for glyphname, content in sorted(glyph_contents.items()):
        if glyphname in target_components:
            continue  # skip the components themselves
        refs = {r.strip() for r in ref_pat.findall(content)}
        used = sorted(target_components & refs)
        if used:
            users.append((glyphname, used))

    return users, target_components


def main():
    component_base = sys.argv[1] if len(sys.argv) > 1 else "uni2E94"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    packages = [
        p for p in [
            os.path.join(project_dir, "MingjianCaoshuHeiti.glyphspackage"),
            os.path.join(project_dir, "MingjianCaoshuHeitiWIP.glyphspackage"),
        ]
        if os.path.isdir(p)
    ]

    if not packages:
        print("No .glyphspackage found.")
        sys.exit(1)

    for package_dir in packages:
        print(f"Package: {os.path.basename(package_dir)}")
        users, targets = find_component_users(package_dir, component_base)

        print(f"  Target components ({len(targets)}): {', '.join(sorted(targets))}")

        if not users:
            print(f"  No glyphs found using these components.")
        else:
            print(f"  Glyphs using them ({len(users)}):")
            for glyphname, used_comps in users:
                print(f"    {glyphname}  [{', '.join(used_comps)}]")
        print()


if __name__ == "__main__":
    main()
