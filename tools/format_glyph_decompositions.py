def read_chaizi():
	result = {}
	for filename in ['src-external/chaizi-ft.txt', 'src-external/chaizi-jt.txt']:
		with open(filename, 'r', encoding='utf-8') as f:
			for line in f:
				parts = line.strip().split('\t')
				if len(parts) < 2:
					continue  # skip lines without two tab-separated fields
				key = parts[0].replace(' ', '')
				value = '⿰' + parts[1].replace(' ', '')
				result[key] = value
	return result

def read_GB_glyph_map():
	map = {}
	d = {}
	with open('src-external/GB-ext-glyph-map.txt', 'r', encoding='utf-8') as f:
		for line in f:
			parts = line.strip().split('\t')
			if len(parts) < 2:
				continue  # skip lines without two tab-separated fields
			if parts[0] not in parts[1]: print(f'Error! Key {parts[0]} not included in items.')
			for key in parts[1]:
				map[key] = parts[0]
			d[parts[0]] = parts[1]
	return map, d

if __name__ == "__main__":
	import sys
	if len(sys.argv) != 2:
		print("输入错误！")
		sys.exit(1)

	chars = sys.argv[1]
	decompositions = read_chaizi()
	GB_glyph_map, GB_glyph_dict = read_GB_glyph_map()

	lines = []
	for char in chars:
		uni = format(ord(char), 'X')
		if char not in decompositions:
			print(f'「{char} {uni} 」拆字未知，请手动添加！')
		else:
			if char not in GB_glyph_map:
				print(f'「{char} {uni} 」未收录，请手动检查！')
			elif char != GB_glyph_map[char]:
				char_to_use_uni = format(ord(GB_glyph_map[char]), 'X')
				print(f'「{char} {uni} 」请使用「{GB_glyph_map[char]} {char_to_use_uni} 」字形。')
			elif len(GB_glyph_dict[char]) > 1:
				print(f'「{char} {uni} 」字形包含以下字码，请手动添加！')
				for item in GB_glyph_dict[char]:
					if item == char: continue
					item_uni = format(ord(item), 'X')
					print(f'「...包含{item} {item_uni} 」；')
			lines.append(f'{char}\t{decompositions[char]}')
			print(f'「{char} {uni} 」拆字已添加！')
	
	with open("out/new_glyphs.txt", "w", encoding="utf-8") as f:
		f.write("\n".join(lines))
	print('运行完成！新字及结构以添加至临时文档。')