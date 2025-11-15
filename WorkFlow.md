# 工作流程

因为本字体的诞生较为坎坷，所以制作流程并不十分完整。作者计划以后继续制作其它草书字体，届时会分享更加完整优化的制作流程。

# 准备

将Glyphs字体文件保存至本主文件夹下。

# 量产阶段

作者习惯大致以**形声字声旁**（部首外部分）为组批量生成新字。

## 日常生产流程
* 运行[字形整理](tools/format_glyph_decompositions.py)工具，将所有新字粘入输入区，这将在[输出](out/)区生成[新字符](out/new_glyphs.txt)文件；
	* 运行代码：`python3 tools/format_glyph_decompositions.py '样例新字'`
* 检查确认[新字符](out/new_glyphs.txt)文件中的字符和结构；
* 在GlyphsApp中运行[字形生成宏](tools/create_glyphs_from_components.py)文件，生成新字符；
	* 如果有缺漏部件，补全后重新运行；
	* 已生成的字不会覆盖；如需覆盖须先删除；
* 在GlyphsApp中逐一调整新字；
* 在GlyphsApp中运行[随机文本生成宏](tools/generate_sample_text.py)，将新字粘入对话框，查看效果，微调；
	* 可以重复几次确保不同情形的一致性；
* （可选）完成新字后，拆解新字中的部件；
* 完成新字后，把新字推入[字形表](out/dictionary.txt)，确认无误后覆盖[原表](src/dictionary.txt)；
	* 运行代码：`python3 tools/push_new_glyphs_to_dictionary.py`
	* 检查是否有特殊新字，比如应当标记为「偏旁」或有其它写法的
* （可选）清空[新字符](out/new_glyphs.txt)文件，它是临时性的。

## 周期存档
* 检查WIP文档，无误后覆盖原字体文件，复制出新WIP文档；
* 将下列文件更新至cursive-chinese-learn：
	* MingjianCaoshuHeiti.ufo；
	* src/dictionary.txt。