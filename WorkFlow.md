# 工作流程

因为本字体的诞生较为坎坷，所以制作流程并不十分完整。作者计划以后继续制作其它草书字体，届时会分享更加完整优化的制作流程。

## 准备

将Glyphs字体文件保存至本主文件夹下。

### 从终端启动项目工具

在 Glyphs 3 中打开本项目已保存的字体，将其设为当前文档；需要操作选中字形的工具，先在 Glyphs 中完成选择。
然后在终端进入项目根目录，检查连接并查看可用工具：

```sh
python3 tools/run_in_glyphs.py --check
python3 tools/run_in_glyphs.py --list
```

运行工具时，将名称作为参数传给 `tools/run_in_glyphs.py`。脚本在打开的 Glyphs 中执行，使用当前文档和选择，
弹窗及标签页也在 Glyphs 中显示，输出转回终端。脚本保留在项目内，路径由启动器自动确定。
选项窗口出现后，终端命令可能已结束，继续在 Glyphs 中操作即可；字体修改按各工具说明检查后手动保存。

终端使用 Python 3.9 或更新版本，并需支持 PyObjC/Foundation；Glyphs 自身的 Python 和 Vanilla 单独配置。
依赖安装、完整命令及常见问题见[终端启动说明](tools/README.md#从终端运行-glyphs-工具)。

## 量产阶段

作者习惯大致以**形声字声旁**（部首外部分）为组批量生成新字。

### 自动生成智能部件图层

在 Glyphs 3 中选中一个或多个字形（不限名称前缀），运行
[部件图层生成宏](tools/generate_component_layers.py)：

```sh
python3 tools/run_in_glyphs.py generate_component_layers
```

也可以通过 Glyphs 的 Scripts 菜单或 Macro Panel 运行。
Macro Panel 中粘贴的完整脚本不会随仓库更新；建议使用上述启动命令，或在 Macro Panel
中用 `runpy.run_path` 加载当前脚本，避免继续运行旧副本。

运行后会弹出选项窗口，Width 和 Height 可分别选择缩放到 **50% 或 75%**，
已有智能部件轴时默认选中该轴的最小值，未设置的轴默认 **75%**。
已有轴必须是 **50–100 或 75–100**；其他范围或重复轴会弹出警告并停止，不修改字体。
批量选择时，各轴沿用所选字形中已有的一致设置；同一轴的已有设置不一致时会
警告并停止，请分别运行。点击 Generate 生成，点击 Cancel 取消且不修改字体。
脚本读取所选主版对应的 `Regular` 图层；以下用 W、H 表示所选宽度、高度百分比：

| 图层 | Width | Height |
| --- | --- | --- |
| Regular | 100 | 100 |
| Narrow | W | 100 |
| Short | 100 | H |
| Small | W | H |

脚本会建立或更新 Width、Height 智能部件轴：最小值分别为 W、H，最大值均为
100；同时设置以上四个图层的轴端点映射，包括 `Regular`。已有轴会保留原 ID。

准备 `Regular` 时，每个连续笔画必须独立成一个逆时针闭合轮廓；将笔画起点的
右侧节点设为路径起点，沿右侧到笔画末端，再沿左侧返回。两端必须是直线，
两侧节点及控制柄必须逐一对应，曲线使用三次贝塞尔。需要恢复平滑连接的节点
应在两侧都标记为平滑。脚本会检查轮廓结构，遇到不符合要求的字形会跳过，
并在 Macro Panel 中输出字形名和轮廓编号。
空轮廓会保留并跳过，不影响后续笔画的生成；只有空轮廓的 `Regular` 会报错。

缩放原点固定为**汉字字框右下角**，即 `(font.upm, master.descender)`，本字体为
`(1000, -120)`，不使用轮廓包围框。脚本线性缩放笔画中线，先旋转各节点
（含控制柄）到中线的偏移，再沿压缩方向轻微缩小偏移：若该方向的中线缩放比例
为 s，偏移乘以 `1 - (1 - s) / 20`。因此原间距 80 在缩放到 50% 时变为 78，
缩放到 75% 时变为 79；未压缩方向不做额外缩放。局部方向取相邻中线控制点的弦方向，端点使用单侧
方向，重合点跳过；控制柄不在曲线上，因此也使用这个控制多边形方向约定。
两侧都平滑且前后都有控制柄的连接，按柄长加权平均角度恢复共线，长柄旋转
较少，同时保留恢复前的柄长。平滑处理会进一步移动控制柄。

随后以 **Regular 原轮廓**为准恢复轴向对齐：原本水平或垂直的控制柄，以及没有
控制柄的直线段，在生成图层中保持同一方向；不使用角度阈值，原本只是接近水平
或垂直的特征不强制对齐。连续直线段共同调整，控制柄随锚点移动；需要对齐的
控制柄绕锚点旋转并保留柄长。

最后按字体当前网格成对取整，同时保持上述对齐关系。对应点的横、纵间距各取整
一次，避免分别取整把 79 变成 78 或 80。单独一对节点在整数网格上保持奇数间距
时，中点最多偏移半个网格。若多组约束的非整数间距无法同时取整，优先保持轴向
对齐和可精确表示的间距。网格为 0 时保留浮点精度。

原始 `Regular` 轮廓保留，字宽不变，锚点按相同原点线性变换。每次点击 Generate
只从 `Regular` 生成所选主版中缺少的 Narrow、Short、Small；已有同名图层保留，
不替换轮廓、锚点或图层 ID，仍配置四个图层的智能部件轴映射。调整选项会更新轴范围，
但不会重新缩放已有图层；需要重新生成时，请先删除相应图层。Macro Panel 会列出
本次生成和保留的图层。每个字形的修改合为一次撤销，脚本
不自动保存字体。选项窗口使用 Vanilla，与随机文本生成宏使用的界面库相同。

几何算法与图层适配的测试可在项目目录执行：
`python3 -m unittest discover -s tools/tests -v`。

API 参考：[Glyphs Python API](https://docu.glyphsapp.com/glyphs2/#GSLayer.smartComponentPoleMapping)
与 [Smart Components 手册](https://handbook.glyphsapp.com/components/smart/)。

### 日常生产流程

* 运行[字形整理](tools/format_glyph_decompositions.py)工具，将所有新字粘入输入区，这将在[输出](out/)区生成[新字符](out/new_glyphs.txt)文件；
	* 运行代码：`python3 tools/format_glyph_decompositions.py '样例新字'`
* 检查确认[新字符](out/new_glyphs.txt)文件中的字符和结构；
* 通过终端启动[智能缩放字形生成宏](tools/create_scaled_glyphs_from_components.py)，生成新字符；
	* 运行代码：`python3 tools/run_in_glyphs.py create_scaled_glyphs_from_components`
	* 按提示输入当前部件的宽度或高度权重，允许 `0 < x < 10` 的小数；两种权重在本次运行中分别只询问一次；
	* 每个新字生成后会单独打开标签页；统计与回退规则见[工具文档](tools/README.md#按智能部件统计生成新字)；
	* 如果有缺漏部件，补全后重新运行；
	* 已生成的字不会覆盖；如需覆盖须先删除；
	* 仅需原始部件组合时，可运行旧版：`python3 tools/run_in_glyphs.py create_glyphs_from_components`；
* 在GlyphsApp中逐一调整新字；
* 在GlyphsApp中运行[随机文本生成宏](tools/generate_sample_text.py)，将新字粘入对话框，查看效果，微调；
	* 运行代码：`python3 tools/run_in_glyphs.py generate_sample_text`
	* 可以重复几次确保不同情形的一致性；
* （可选）完成新字后，拆解新字中的部件；
* 完成新字后，把新字推入[字形表](src/dictionary.txt)；
	* 运行代码：`python3 tools/push_new_glyphs_to_dictionary.py`
	* 将新字中“同「...」”的标签替换为“同异”或“简体”；
	* 检查是否有特殊新字，比如应当标记为「偏旁」或有其它写法的；
* （可选）清空[新字符](out/new_glyphs.txt)文件，它是临时性的。

### 周期存档
* 检查WIP文档，无误后覆盖原字体文件，复制出新WIP文档；
* 将下列文件更新至cursive-chinese-learn：
	* MingjianCaoshuHeiti.ufo；
	* src/dictionary.txt。
