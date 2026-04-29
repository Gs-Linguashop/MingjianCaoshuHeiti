import re

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
			decomp = decompositions[char].replace('⿰絲', '⿰糸').replace('⿰丝', '⿰糸')
			decomp = re.sub(r'⿰辵(.)', r'⿱\1辶', decomp)
			decomp = re.sub(r'⿰(.)火', r'⿱\1灬', decomp)
			decomp = re.sub(r'⿰(.)邑', r'⿰\1阝', decomp)
			decomp = re.sub(r'⿰(.)心', r'⿱\1心', decomp)
			decomp = re.sub(r'⿰(.)食', r'⿱\1食', decomp)
			decomp = re.sub(r'⿰(.)丝', r'⿱\1糸', decomp)
			decomp = re.sub(r'⿰(.)刀', r'⿰\1刂', decomp)
			decomp = re.sub(r'⿰(.)攴', r'⿰\1攵', decomp)
			decomp = decomp.replace('⿰病', '⿸疒')
			decomp = decomp.replace('⿰草', '⿱艸')
			decomp = decomp.replace('⿰蟲', '⿰虫')
			decomp = decomp.replace('⿰雨', '⿱雨')
			decomp = decomp.replace('⿰風', '⿺風')
			decomp = decomp.replace('⿰竹', '⿱竹')
			decomp = decomp.replace('⿰髟', '⿱髟')
			decomp = decomp.replace('⿰冰', '⿰冫')
			decomp = decomp.replace('⿰肉', '⿰月')
			decomp = decomp.replace('⿰門', '⿱門')
			decomp = decomp.replace('⿰门', '⿱门')
			decomp = decomp.replace('⿰皿', '⿱皿')
			decomp = decomp.replace('⿰黑', '⿴黑')
			decomp = decomp.replace('⿰虎', '⿱虍')
			decomp = decomp.replace('⿰囗', '⿴囗')
			decomp = decomp.replace('⿰行', '⿴行')
			decomp = decomp.replace('⿰穴', '⿱穴')
			decomp = decomp.replace('⿰阜', '⿰阝')
			decomp = decomp.replace('⿰饣', '⿰食')
			lines.append(f'{char}\t{decomp}')
			print(f'「{char} {uni} 」拆字已添加！')
	
	with open("out/new_glyphs.txt", "w", encoding="utf-8") as f:
		f.write("\n".join(lines))
	print('运行完成！新字及结构以添加至临时文档。')