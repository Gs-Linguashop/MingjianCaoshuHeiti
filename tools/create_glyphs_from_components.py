# MenuTitle: Create Glyphs from Component List
# -*- coding: utf-8 -*-
__doc__ = """
Reads a text file that defines glyphs and their components, creates missing glyphs, and adds components.
File format example:
A.alt: A, acutecomb
B.alt: B, ringcomb
"""

import os
from GlyphsApp import *

def parse_str(s, keep_bracket=False):
	"""
	Split a string into list of single-character strings,
	but keep substrings enclosed in [...] together.

	Example:
		"A[Bc]D[e]F" → ["A", "Bc", "D", "e", "F"]
	"""
	result = []
	i = 0
	while i < len(s):
		if s[i] == "[":
			j = s.find("]", i + 1)
			if j == -1:
				# no closing bracket, take the rest
				if keep_bracket: result.append('[' + s[i+1:])
				else: result.append(s[i+1:])
				break
			if keep_bracket: result.append('[' + s[i+1:] + ']')
			else: result.append(s[i+1:j])
			i = j + 1
		else:
			result.append(s[i])
			i += 1
	return result

def read_radical_glyph_names(file_name):
	radical_glyph_names = {}
	with open(file_name, 'r', encoding='utf-8') as f:
		for line in f:
			parts = line.strip().split('\t')
			name, pos, glyph_name = parts[0], parts[1], parts[2]
			radical_glyph_names.setdefault(name, {})[pos] = glyph_name
	return radical_glyph_names

def add_radical_to_components(radical_glyph_name, components, radical_glyph_names, position='general'):
	# return is_success
	if radical_glyph_name not in radical_glyph_names:
		print(f"Glyph missing: {radical_glyph_name} {position}")
		return False
	elif position in radical_glyph_names[radical_glyph_name]:
		components.append(radical_glyph_names[radical_glyph_name][position])
		return True
	elif 'general' in radical_glyph_names[radical_glyph_name]:
		components.append(radical_glyph_names[radical_glyph_name]['general'])
		return True
	else:
		print(f"Glyph missing: {radical_glyph_name} {position}")
		return False

# === MAIN ===
print("Starting glyphs creation.")

font = Glyphs.font
if not font:
	print("⚠️ No font open.")
	raise SystemExit

font_path = font.filepath  # full path to the .glyphs file
font_dir = os.path.dirname(font_path)

definition_file = os.path.join(font_dir, "out/new_glyphs.txt")
if not os.path.exists(definition_file):
	print(f"⚠️ File not found: {definition_file}")
	raise SystemExit

radical_file = os.path.join(font_dir, "src/radicals.txt")
if not os.path.exists(radical_file):
	print(f"⚠️ File not found: {radical_file}")
	raise SystemExit
radical_glyph_names = read_radical_glyph_names(radical_file)

with open(definition_file, "r", encoding="utf-8") as f:
	lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

glyphs_created = ''
for line in lines:
	if "\t" not in line:
		print(f"Skipping malformed line: {line}")
		continue

	if line[0] == '#':
		continue  # skip comment lines

	glyph_name, comps_str = [x.strip() for x in line.split("\t", 1)]
	comps = parse_str(comps_str)
	components = []
	if comps[0] == '⿰':
		if len(comps) != 3:
			print(f"Skipping malformed line: {line}")
			continue
		if not add_radical_to_components(comps[1], components, radical_glyph_names, position='left'):
			print(f"Skipping line: {line}")
			continue
		if not add_radical_to_components(comps[2], components, radical_glyph_names, position='right'):
			print(f"Skipping line: {line}")
			continue
	elif comps[0] == '⿱':
		if len(comps) != 3:
			print(f"Skipping malformed line: {line}")
			continue
		if not add_radical_to_components(comps[1], components, radical_glyph_names, position='top'):
			print(f"Skipping line: {line}")
			continue
		if not add_radical_to_components(comps[2], components, radical_glyph_names, position='bottom'):
			print(f"Skipping line: {line}")
			continue
	else:
		if len(comps) == 0:
			print(f"Skipping malformed line: {line}")
			continue
		is_any_radical_missing = False
		for i in range(1, len(comps)):
			if not add_radical_to_components(comps[i], components, radical_glyph_names):
				print(f"Skipping line: {line}")
				is_any_radical_missing = True
				break
		if is_any_radical_missing:
			continue
	
	# check if components exist
	are_component_exist = True
	for comp in components:
		if font.glyphs[comp] is None:
			print(f"component {comp} missing from font")
			print(f"Skipping line: {line}")
			are_component_exist = False
	if not are_component_exist: continue

	# check if glyph exists
	glyph = font.glyphs[glyph_name]
	if glyph is None:
		glyph = GSGlyph(glyph_name)
		font.glyphs.append(glyph)
		print(f"🆕 Created glyph: {glyph_name}")
		glyphs_created += glyph_name
	else:
		print(f"Glyph already exists: {glyph_name}")
		continue

	# add components to master layer
	layer = glyph.layers[0]
	layer.width = 1000
	existing_component_names = [c.componentName for c in layer.components]

	for comp in components:
		if comp not in existing_component_names:
			new_comp = GSComponent(comp)
			layer.components.append(new_comp)
			print(f"  + Added component '{comp}' to {glyph_name}")
		else:
			print(f"  • Component '{comp}' already in {glyph_name}")

print("✅ Done.")
print("Created glyphs: " + glyphs_created)