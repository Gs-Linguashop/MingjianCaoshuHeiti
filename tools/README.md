# 工具脚本

交互式 Glyphs 工具通过下面的终端启动器运行，也可使用 Scripts 菜单或宏面板；使用 Vanilla 窗口的工具需在 Glyphs 中安装 Vanilla。
普通命令行工具在项目根目录直接运行：`python3 tools/脚本名.py`。

## 从终端运行 Glyphs 工具

也可以直接从终端启动本项目中的 Glyphs 工具，无须复制到系统 Scripts 文件夹或反复粘贴代码。
先在 Glyphs 3 中打开本项目的字体，并选中需要操作的字形；然后在项目根目录运行：

```sh
python3 tools/run_in_glyphs.py --check
python3 tools/run_in_glyphs.py --list
python3 tools/run_in_glyphs.py create_scaled_glyphs_from_components
python3 tools/run_in_glyphs.py generate_component_layers
python3 tools/run_in_glyphs.py generate_sample_text
```

也接受文件名或项目相对路径，例如 `python3 tools/run_in_glyphs.py tools/generate_sample_text.py`。
`--check` 仅检查连接，不运行工具。启动器从自身位置确定项目目录，没有硬编码的绝对路径，
工具始终保留在本项目中；如果当前字体来自另一项目，会拒绝运行以免误操作。
代码在打开的 Glyphs 应用中执行，因此可使用当前选择、弹窗和新标签页，输出转回终端。
浮动选项窗口打开后，终端命令可能已经结束；后续操作继续在 Glyphs 中完成。
启动器只列出 `tools/` 下首行含 `# MenuTitle:` 的交互脚本；普通命令行脚本仍使用 `python3 tools/脚本名.py`。
启动器本身不保存字体，运行后按具体工具的说明检查结果并保存。

### 依赖与项目内安装

终端使用 Python 3.9 或更新版本，并需支持 PyObjC/Foundation。若 `--check` 提示缺少 PyObjC，
在项目根目录建立虚拟环境并安装依赖：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install pyobjc-framework-Cocoa
.venv/bin/python tools/run_in_glyphs.py --check
.venv/bin/python tools/run_in_glyphs.py generate_sample_text
```

之后用 `.venv/bin/python` 替代示例中的 `python3` 即可，无须激活虚拟环境。
`.venv` 是本机依赖环境，不应提交到版本库。Glyphs 内的 Python 和 Vanilla 仍按原方式配置，
终端虚拟环境的依赖不会自动安装进 Glyphs。

### 常见问题

| 情况 | 处理方式 |
| --- | --- |
| 无法连接 Glyphs 3 | 打开 Glyphs 3 及本项目字体，再运行 `--check`。 |
| 提示没有已保存字体，或当前字体属于其它项目 | 在 Glyphs 中切换到本项目已保存的字体文档。 |
| 提示未知工具 | 用 `--list` 查找名称；可省略 `.py`，也可传入 `tools/文件名.py`。 |
| 终端已结束，但 Glyphs 中仍有选项窗口 | 继续在 Glyphs 中操作；命令结束表示脚本已打开窗口。 |
| 连接中断或按了 Ctrl-C | 先检查 Glyphs：已提交的脚本可能仍在执行，确认状态后再重跑。 |

启动器测试：`python3 -m unittest discover -s tools/tests -p 'test_run_in_glyphs.py' -v`。

该启动方式使用 [Glyphs 官方远程脚本接口](https://github.com/schriftgestalt/GlyphsSDK/blob/Glyphs3/Glyphs%20remote%20scripts/Glyphs.py)。
另有官方 [glyphs-cli](https://pypi.org/project/glyphs-cli/) 可进行批量处理；本项目这些依赖当前选择、
弹窗和编辑标签页的工具应使用上面的应用内启动器。

## 工具列表

| 工具 | 运行环境 | 简介 |
| --- | --- | --- |
| [run_in_glyphs.py](run_in_glyphs.py) | 终端 → Glyphs 3 | 从终端选择并运行项目中的交互工具；无需复制脚本或填写绝对路径。 |
| [generate_component_layers.py](generate_component_layers.py) | Glyphs 3 | 从所选字形的 Regular 补齐 Narrow、Short、Small，不限名称前缀，保留已有图层并配置智能部件轴。宽高可选 50% 或 75%，默认沿用已有轴设置，未设置时为 75%；异常或相互冲突的轴设置会警告并停止。以汉字字框右下角为原点缩放，轻微减细笔画，保持原有水平、垂直对齐及取整间距。 |
| [create_glyphs_from_components.py](create_glyphs_from_components.py) | Glyphs | 根据 `out/new_glyphs.txt` 和部件表创建缺失字形，保留已有字形。 |
| [create_fullwidth_glyphs.py](create_fullwidth_glyphs.py) | Glyphs 3 | 读取全角映射，为已有原字符创建缺失的全角字形；每个主版使用一个原字符部件，保持原大小及纵向位置，在一个 em 字宽内水平居中。 |
| [create_scaled_glyphs_from_components.py](create_scaled_glyphs_from_components.py) | Glyphs 3 | 识别当前部件，按字体内同位置搭配的双部件字形统计智能 Width/Height 与位移；宽、高分别询问一次权重，逐字打开新标签页。 |
| [generate_sample_text.py](generate_sample_text.py) | Glyphs | 输入待检查的文字，混入字体中的随机字符，生成测试文本并打开新标签页。 |
| [count_cjk_codepoints.py](count_cjk_codepoints.py) | Glyphs | 统计字体覆盖的汉字及部首字码，导出至 `out/cjk_characters.txt`。 |
| [check_character_coverage.py](check_character_coverage.py) | Glyphs 3 | 直接读取当前字体的全部 Unicode 分配，对照七个覆盖字表，将缺字与统计写入 `out/coverage/`。 |
| [format_glyph_decompositions.py](format_glyph_decompositions.py) | 命令行 | 整理汉字拆分结构，输出至 `out/new_glyphs.txt`；运行时追加参数，如 `'样例新字'`。 |
| [push_new_glyphs_to_dictionary.py](push_new_glyphs_to_dictionary.py) | 命令行 | 将新字记录合并到 `src/dictionary.txt`，去重并按字码排序。 |
| [find_component_users.py](find_component_users.py) | 命令行 | 在本地 Glyphs 字体包中查找使用指定部件及其变体的字形；可追加部件名，默认 `uni2E94`。 |
| [utils.py](utils.py) | 辅助模块 | 提供字符串拆分函数，将方括号内的内容作为一个整体。 |

详细流程见[工作流程](../WorkFlow.md)。

`format_glyph_decompositions.py` 根据字形映射输出“包含”提示时，会紧接原字添加对应的
`同「原字」` 行。全部输入处理完后，若同一字符还有独立拆分结构，将该结构行加上 `# ` 注释，
保留同字标记生效；不受输入顺序影响。例如处理 `縊缢` 得到：

```text
縊	⿰糸益
缢	同「縊」
# 缢	⿰糸益
```

生成宏与字形表合并工具均会忽略注释行。

## 检查字表覆盖率

在 Glyphs 3 中打开本项目字体，然后运行：

```sh
python3 tools/run_in_glyphs.py check_character_coverage
```

直接读取当前字体的全部 Unicode 分配（含次要码位、不导出的字形及未保存修改），
对照 `src-external/coverage/` 下所有 `.txt` 字表，不修改字体。
结果写入 `out/coverage/`：各表的 `missing_<字表文件名>.txt`、缺字并集 `missing_all.txt`
和统计 `summary.json`。缺字按 Unicode 升序，每行 `字符<TAB>大写十六进制码位`，
码位至少四位、无 `U+` 前缀；完全覆盖时为空文件。每次覆盖同名报告，该目录已被 Git 忽略。
此检查针对源字体的码位分配，不验证导出字体的 cmap 或轮廓。

## 从原字符创建全角字形

在 Glyphs 3 中打开本项目字体，然后运行：

```sh
python3 tools/run_in_glyphs.py create_fullwidth_glyphs
```

读取 `src-external/fullwidth-glyph-map.txt`，按 Unicode 查找原字符，为缺失的全角字符创建字形。
每个主版使用一个原字符部件，保持大小和纵向位置，在一个 em 字宽内水平居中。
已有字形及缺少原字符或主版图层的条目跳过；新增字形显示在新标签页中，检查后手动保存。

## 按智能部件统计生成新字

运行：`python3 tools/run_in_glyphs.py create_scaled_glyphs_from_components`，
也可通过 Scripts 菜单或宏面板运行 `create_scaled_glyphs_from_components.py`。
先统计 `out/new_glyphs.txt` 第二列的部件出现次数，忽略结构符号，方括号名称视为一个部件；
仅一行时排除康熙部首及常见变体。无法唯一确定时弹窗选择。
第二列为 `同「峰」` 这类同字标记时，不创建第一列的字形，而将第一列字符的 Unicode
追加到被引用字形的 `unicodes` 列表，保留其原主码位及所有其它码位。
例如 `峯<TAB>同「峰」` 会把 U+5CEF 追加到峰的字形（`<TAB>` 表示制表符）。
这些行不参与当前部件统计，也不触发权重询问；只有同字标记的文件也可直接运行。
别名在普通字形生成后处理，可以引用同批新建字形，也支持同字标记之间的连续引用。
重复运行不重复添加码位；引用缺失、循环引用或码位已属于另一字形时，报告并跳过该行。
优先使用 `src/radicals.txt` 的位置专用字形，其次使用 general；未列出时读取
`uniXXXX`（也支持 `uXXXXX` 及自定义 Unicode 字形名）的智能部件副本。
当前部件回退字形含原始轮廓或非智能部件时，整批在修改前停止；其它缺失部件只跳过受影响的新字。
表中指定字形若本身是复合字，也按同一规则展开。

新字的左右、上下结构取自 `new_glyphs.txt`。参考字须在同一主版中只有两个部件且没有原始轮廓，
已有参考字的结构优先读取 `src/dictionary.txt`；没有结构记录时，仅接受在一个方向明确分离、
另一方向重叠的两个部件。排除已知包围结构、相互包含的包围框及结构不明确的参考字。
再按另一部件的**确切字形名**与位置筛选，不混入来源、轴范围可能不同的 `.alt` 字形。
参考统计在生成前固定，按主版分开计算，避免新生成的字污染统计。
权重允许 `0 < x < 10` 的小数；当前部件使用正态分布的 `x/10` 分位数，另一部件使用互补分位数，
标准差采用总体标准差。左右结构对智能 **Width** 使用分位数；当前部件保留原有高度和纵向位置，
不应用智能 Height、普通矩阵的纵向缩放或额外 y 位移，也不按参考字的中心上下移动。
展开的每个子部件保留在源字形中的 y 位移；另一部件的 **Height** 使用均值。
上下结构仍对智能 **Height** 使用分位数、**Width** 使用均值。
普通仿射矩阵取均值，不重复应用权重缩放。另一部件使用同一指定字形，因此沿用其平均位移；
当前部件及展开后的复合部件，则按参考部件实际插值后的包围框定位：左右结构固定左侧部件的左边缘、
右侧部件的右边缘；当前部件的纵向位置沿用源字形，其它展开部件的纵向中心使用参考均值。
上下结构固定上侧部件的上边缘、下侧部件的下边缘，横向使用中心位置的均值。
这些位置不随权重改变。这样可兼容 `.left`、`.top` 等专用字形和 general 字形不同的缩放原点，
避免把不同原点下的位移直接用于新部件（例如 `戤 ⿰盈戈` 中的盈）。
智能值按真实轴 ID 读写；省略的值按所属主版默认图层的
轴端点映射读取，而不是一律取 100。字体内已有超出轴端点范围的合法外推值，因此不强行截断这些值。
没有某个轴的参考部件不参与该轴统计；目标缺少该轴时保留该方向设置并在宏面板提示。
宏面板记录各侧样本数、均值和标准差。

Unicode 回退的复合字没有整体 Width/Height 轴：逐个插入其智能子部件，将每个子部件原有的
Width/Height 值乘以统计宽高除以 100 得到的比例，其它智能轴保持原值。
左右结构中当前部件的纵向比例固定为 1，额外 y 位移为 0；逐个子部件定位和整组定位时都只调整横向位置。
若子部件已有旋转或错切，先将整体缩放换算到该子部件的局部方向。
由智能轴负责的缩放从普通矩阵中移除，避免再次压缩轮廓和笔画粗细；缺少相应智能轴时，
仅该方向使用普通矩阵缩放并在宏面板提示。原有普通矩阵仍与参考矩阵复合。
源字形仍连接字体时就记录智能值和位置；复制后脱离图层的部件不能提供可靠的插值包围框。
每个子部件插入新图层、设置智能值并完成插值后，按整体变换后的中心位置定位，再插入下一个。
最后按上述边缘和中心位置统计统一平移整组子部件。
无参考字时保留源部件变换；其它平面结构也直接放入源部件，嵌套结构跳过。
已有字形不覆盖，创建的每个字形单独打开标签页，不自动保存字体。

相关测试：`python3 -m unittest discover -s tools/tests -p 'test_create_scaled*' -v`。
另有 `tools/tests/native_scaled_smoke.py`，使用独立内存中的字体，通过本机 GlyphsCore 验证
当前部件在左、右、上、下四个位置、权重 2 与 8 时的真实智能插值、包围框变化及外侧边缘定位，
并验证复合字回退时每个子部件的智能缩放和位置；不会保存字体。
智能轴 API 参考：[Glyphs 3 Python wrapper](https://github.com/schriftgestalt/GlyphsSDK/blob/Glyphs3/ObjectWrapper/GlyphsApp/__init__.py)。
