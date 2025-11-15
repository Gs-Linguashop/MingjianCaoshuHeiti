import os

# Input files
new_file = "out/new_glyphs.txt"
old_file = "src/dictionary.txt"
out_file = "out/dictionary.txt"

def get_unicode_hex(char):
	"""Return the uppercase Unicode hex string (4+ digits, zero-padded)."""
	return f"{ord(char):04X}"

# --- Read existing dictionary ---
existing_lines = []
if os.path.exists(old_file):
	with open(old_file, "r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if line:
				existing_lines.append(line)

# --- Read new glyphs ---
new_entries = []
with open(new_file, "r", encoding="utf-8") as f:
	for line in f:
		line = line.strip()
		if not line or "\t" not in line:
			continue
		char, structure = line.split("\t", 1)
		uni = get_unicode_hex(char)
		# Format: char<TAB>Unicode<TAB>字<TAB>推得<TAB>structure
		formatted = f"{char}\t{uni}\t字\t推得\t{structure}"
		new_entries.append(formatted)

# --- Merge and deduplicate ---
combined = set(existing_lines) | set(new_entries)

# --- Sorting rule: by unicode (2nd field), then full line ---
def sort_key(line):
	parts = line.split("\t")
	uni = parts[1] if len(parts) > 1 else "FFFFF"
	return (int(uni, 16), line)

sorted_lines = sorted(combined, key=sort_key)

# --- Write output ---
os.makedirs(os.path.dirname(out_file), exist_ok=True)
with open(out_file, "w", encoding="utf-8") as f:
	f.write("\n".join(sorted_lines))

print(f"✅ Merged {len(new_entries)} new entries into {out_file}")
