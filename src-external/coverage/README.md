# Character coverage lists

All seven `.txt` files contain **only characters**, one Unicode scalar value per
line, sorted by ascending Unicode codepoint. They are UTF-8 without a BOM, use LF
line endings, contain no duplicates, and end with a newline. English titles are
given below rather than inserted into the character files.

| File | English title | Characters |
| --- | --- | ---: |
| [mainland_china_frequently_used_characters_1988.txt](mainland_china_frequently_used_characters_1988.txt) | Mainland China — List of Frequently Used Characters in Modern Chinese (1988) | 3,500 |
| [mainland_china_gb2312_1980.txt](mainland_china_gb2312_1980.txt) | Mainland China — GB/T 2312-1980: Chinese Character Set for Information Interchange, Primary Set | 6,763 |
| [mainland_china_gb12345_1990.txt](mainland_china_gb12345_1990.txt) | Mainland China — GB/T 12345-1990: Chinese Ideogram Set for Information Interchange, Supplementary Set | 6,866 |
| [taiwan_standard_forms_of_common_national_characters.txt](taiwan_standard_forms_of_common_national_characters.txt) | Taiwan — Chart of Standard Forms of Common National Characters | 4,808 |
| [hong_kong_graphemes_of_commonly_used_characters.txt](hong_kong_graphemes_of_commonly_used_characters.txt) | Hong Kong — List of Graphemes of Commonly-used Chinese Characters | 4,762 |
| [japan_joyo_kanji_2010_with_kyujitai.txt](japan_joyo_kanji_2010_with_kyujitai.txt) | Japan — Jōyō Kanji Table (2010), including Kyūjitai | 2,500 |
| [south_korea_basic_hanja_for_educational_use.txt](south_korea_basic_hanja_for_educational_use.txt) | South Korea — Basic Hanja for Educational Use | 1,800 |

Sources were retrieved on **2026-10-29**. Raw documents, HTML responses, and local
extraction aids are saved in the ignored `raw/` directory. Exact input URLs and
SHA-256 checksums are recorded in [sources.json](sources.json). Existing repo
files were used for comparison and have not been changed.

## Sources and extraction decisions

### Mainland China: frequently used characters

《现代汉语常用字表》, issued on 26 January 1988: the 2,500 常用字 and 1,000
次常用字 together. This is the **1988 list**, not the different 3,500-character
first tier of the 2013 《通用规范汉字表》.

The character data comes from the [Shanghai Municipal Education Commission's
official transcription](https://edu.sh.gov.cn/yywz_gfbz_gygfhz/20150712/0015-yywz_2003.html).
Its sixteen-stroke 次常用字 section has `蟥` where the printed list has `磺`.
The output corrects that single transcription error. The correction was checked
visually in the published reproduction held by [Osaka University's
repository](https://ir.library.osaka-u.ac.jp/repo/ouka/all/80063/poufs_20.pdf),
printed page 81 / PDF page 88, and agrees with `../chars_3500_raw.txt`.

The resulting 3,500-character set matches `../chars_3500_raw.txt` exactly.
`../chars_3500.txt` contains project-specific traditional forms and expansions,
so it is not used as the source of the simplified coverage list.

### Mainland China: GB 2312 and GB 12345

The official SAMR catalog identifies [GB/T 2312-1980
《信息交换用汉字编码字符集 基本集》](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=5664A728BD9D523DE3B99BC37AC7A2CC)
and [GB/T 12345-1990
《信息交换用汉字编码字符集 辅助集》](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=90394D2B4115D9291C825A7651AEFE4B).
The actual Unicode character membership is extracted from the Unicode
Consortium's [Unihan 17.0.0 release](https://www.unicode.org/Public/17.0.0/ucd/Unihan.zip),
using `kGB0` and `kGB1` in `Unihan_OtherMappings.txt`, respectively. See the
[Unihan property documentation](https://www.unicode.org/reports/tr38/).
These are complete mappings, including characters shared by the two standards;
the sparse `G1-` references in `kIRG_GSource` alone would be incomplete.

These files contain the **Han characters only**; the encoding standards' other
symbols, punctuation, alphabets, and kana are excluded. Original GB standard
scans were not downloaded; the raw folder contains official catalog pages and
the Unicode Consortium's machine-readable mappings.

Despite its filename, `../chars_gb.txt` contains 8,105 general-standard characters
followed by an extra `〇` (8,106 entries), rather than the GB 2312 character set.
It therefore cannot serve as the GB 2312 source. Exact set differences are in
[comparisons.json](comparisons.json).

### Taiwan

《常用國字標準字體表》: use entries **A00001–A04808** of the Ministry of
Education's [official 6,063-character inventory](https://stroke-order.learningweb.moe.edu.tw/download/6063.pdf).
The later B/C-series entries belong to other categories and are excluded.
Every extracted head character was checked against the PDF's explicit Unicode
column and A-series number.

Compared with `../chars_trad.txt`, the official inventory has `汨` U+6C68 in place
of `汩` U+6C69, and `彝` U+5F5D in place of `彞` U+5F5E. The output follows the
official inventory for both differences.

### Hong Kong

《常用字字形表》, 2007 rearranged edition, published separately with Cantonese
and Mandarin pronunciations and English explanations in 2012. The Education
Bureau's [official introduction](https://www.edb.gov.hk/attachment/tc/curriculum-development/kla/chi-edu/resources/primary/lang/curriculum-materials/ziXingBiao_jianJie_TC.pdf)
identifies its 4,762 entries.

The data comes directly from the [Education Bureau's electronic
lookup](https://www.edbchinese.hk/lexlist_ch/), querying the stroke-count index
for 1–33 strokes and selecting the head characters with numeric IDs
**0001–4762**. Every ID is present exactly once. The lookup also returns 42
supplementary `ZC…` entries; these are excluded. This is the complete
4,762-character table, rather than just the 3,171-character primary learning
subset. For example, [entry 2000](https://www.edbchinese.hk/lexlist_ch/result.jsp?id=2000)
explicitly states that it belongs to the former but not the latter.

Only the numbered head forms are included. Unnumbered variants in notes are not
added. An older secondary transcription of the 2000 edition was consulted as a
reference, but the official lookup supplies the output.

### Japan

《常用漢字表》, Cabinet Notification No. 2 of 30 November 2010, from the
[Agency for Cultural Affairs' official publication](https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/kanji/)
and its [PDF](https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/pdf/joyokanjihyo_20101130.pdf).
Only the character column of the main table, PDF pages 11–161, is extracted.

The output includes **2,136 current forms plus the 364 parenthesized Kangxi/old
forms (kyūjitai) associated with 362 entries**, for **2,500 distinct characters**.
Four old-form glyphs are drawn rather than extractable text: `龜` beside `亀`
on PDF page 33, and `辨`, `瓣`, `辯` beside `弁` on PDF page 139. These were
verified visually and added explicitly.

Compatibility ideographs such as `逸` U+FA67 are preserved. **Do not apply NFC or
NFKC to this list**: normalization can erase old-form coverage. Glyph differences
that Unicode unifies cannot be represented as additional single-codepoint lines.
Square-bracketed permitted glyphs do not add any new codepoints to this file.

The 2,136 current forms match the numbered rows in `../chars_jp_2010.txt`
exactly. Its broader old-form column includes variants absent from the official
parenthesized column, and omits some official ones. The output follows the
official column; it does not union in those additional repo variants. The repo's
multiline `弁` old-form field is included when making the comparison.

### South Korea

《한문 교육용 기초 한자》 / 漢文敎育用基礎漢字: the Ministry of Education's
table in [2022 revised curriculum textbook compilation materials, volume
II, published in 2023](https://cdn.kosac.re.kr/files/legacy_data/jnrepo/upload/jnBrdBoard/202304/4218d69f2c4343b88c2a7dde9fa62706_1680754521571.pdf),
printed/PDF pages 50–62. Both middle-school and high-school columns are included.
One glyph, `沿` in the `연` row on page 57, has an invalid PDF text mapping; it
was recovered by visually inspecting the rendered page.

Korean compatibility ideographs used for readings are mapped to their unified
equivalents with per-character NFC; the count remains 1,800. Other encoded
orthographic choices follow the Ministry handbook. In particular, this source
is not replaced with Unihan's `kKoreanEducationHanja` set, which uses some
different variant codepoints. Japanese old-form compatibility characters are
handled separately and remain untouched.

## Rebuilding and verification

[generate.py](generate.py) extracts the seven lists from the local raw snapshots,
verifies their input checksums and expected counts, and checks output checksums
against [sources.json](sources.json). It requires Python 3, PyMuPDF (`fitz`), and
Beautiful Soup (`beautifulsoup4`). From the repository root:

```sh
python3 src-external/coverage/generate.py --check
python3 src-external/coverage/generate.py
```

`--check` verifies without writing. The second command rebuilds the `.txt` files.
The ignored `raw/` snapshots are available in this working copy; a fresh clone
must first download the `raw_sources` URLs in `sources.json` to their named files
under `raw/`. Live websites may change; a checksum mismatch requires source
review rather than silently accepting a different table. The comparison JSON
records the existing repo data at the time of this import.
