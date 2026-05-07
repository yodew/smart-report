# smart-report 中文 API 文档

本文档面向中文使用者，描述当前公开 API 的推荐用法、参数语义和注意事项。

## 快速开始

```python
from smart_report import Canvas, Frame, document, register_font

register_font("SourceHanSansSC-Normal", "examples/fonts/SourceHanSansSC-Normal.ttf", set_default=True, fallback=True)

doc = document()
page = doc.page("A4")

hero = Canvas().height(160).background("#dbeafe")
hero.add_text("你好，smart-report").absolute(24, 24).font_size(24).color("#1e3a8a").z(2)
page.add(hero)

content = Frame().padding(24)
content.add_text("这里是流式内容区域。").font_size(12)
page.add(content)

doc.save("output.pdf")
```

## 顶层入口

### `document()`

创建一个文档构建器。

```python
doc = document()
```

常用方法：

| 方法 | 说明 |
| --- | --- |
| `doc.page(size="A4")` | 新建页面，支持 `"A4"`、`"LETTER"` 或 `(width, height)` 点值元组 |
| `doc.header()` | 创建重复页眉模板 |
| `doc.footer()` | 创建重复页脚模板 |
| `doc.watermark()` | 创建重复水印模板 |
| `doc.save(path)` | 渲染并保存 PDF |

页码占位符只在文本中生效：

```python
doc.header().height(40).add_text("第 {page_number} / {total_pages} 页").absolute("78%", 12)
```

## 容器 API

### `Frame`

`Frame` 是流式容器，子元素按从上到下的顺序排列，适合正文、段落和表格。

```python
frame = Frame().padding(vertical=24, horizontal=32)
frame.add_text("标题").font_size(20).margin(bottom=16)
frame.add_text("正文内容").font_size(12)
page.add(frame)
```

### `Canvas`

`Canvas` 是混合布局容器，支持绝对定位和 `z-index`，适合背景图、叠加文字、图文重叠等场景。

```python
hero = Canvas().height(180).margin(top=24, right=24, bottom=20, left=24)
hero.add_rect().absolute(0, 0).size("100%", 180).background("#dbeafe").z(0)
hero.add_text("季度报告").absolute(24, 24).font_size(26).z(2)
page.add(hero)
```

### `Table`

`Table` 接受二维数组，并提供适合报表场景的列宽、对齐、单元格 padding、表头样式、斑马纹、圆角边框和跨页重复表头能力。

```python
table = Table([
    ["地区", "收入", "增长", "说明"],
    ["APAC", "$1.20M", "+18%", "企业客户续约强劲"],
    ["EMEA", "$0.98M", "+11%", "公共部门项目稳定增长"],
]) \
    .column_widths([90, 80, 60, "auto"]) \
    .align(["left", "right", "right", "left"]) \
    .cell_padding(vertical=8, horizontal=10) \
    .header(background="#1d4ed8", color="#ffffff", repeat=True) \
    .zebra("#f8fafc") \
    .font_size(11) \
    .line_height(14) \
    .stroke("#94a3b8", 1) \
    .radius(10)

frame.add(table)
```

表格专用方法：

| 方法 | 说明 |
| --- | --- |
| `.column_widths(values)` | 设置列宽，支持点值、百分比、`"auto"`；未设置时平均分配 |
| `.align(value)` | 设置文本水平对齐，可传单个值或按列传列表；支持 `"left"`、`"center"`、`"right"` |
| `.cell_padding(...)` | 设置单元格内边距，推荐使用 `vertical` / `horizontal` 或方向命名参数 |
| `.header_padding(...)` | 单独设置表头单元格内边距；未设置时沿用 `.cell_padding(...)` |
| `.header(rows=1, background=None, color=None, repeat=True)` | 设置表头行数、表头颜色，以及跨页时是否重复表头 |
| `.header_style(background=None, color=None, font=None, font_size=None, line_height=None, align=None)` | 设置表头颜色、字体与对齐样式 |
| `.footer(rows, repeat=False, ...)` | 添加 footer 行；`repeat=True` 时跨页重复 footer |
| `.subtotal(row, ...)` | 添加单行汇总 footer |
| `.borders(color, width=1, inner_width=None, outer_width=None)` | 设置表格内外边框宽度 |
| `.cell_border(row_index, column_index, ...)` | 覆盖单元格边框 |
| `.zebra(background="#f8fafc")` | 设置隔行背景色 |
| `.repeat_header(value=True)` | 单独控制跨页重复表头 |
| `.row_style(index, ...)` | 覆盖指定逻辑行的 `background` / `color` / `align` |
| `.column_style(index, ...)` | 覆盖指定列的 `background` / `color` / `align` |
| `.cell_style(row_index, column_index, ...)` | 覆盖指定单元格的 `background` / `color` / `align` |
| `.radius(value)` | 设置表格外边框圆角；渲染时会裁剪外角单元格背景 |

样式覆盖优先级：

`cell_style > row_style > column_style > 表头/斑马纹/表格默认样式`

```python
table = Table(rows) \
    .column_style(2, color="#166534") \
    .row_style(3, background="#ecfeff") \
    .cell_style(6, 1, background="#dcfce7", color="#166534", align="right")
```

> 注意：这些索引基于原始逻辑行列。即使表格跨页拆分并重复表头，样式也会按原始行号继续生效。

表头字体可以通过 `header_style(...)` 单独设置：

```python
table = Table(rows) \
    .header(background="#1d4ed8", color="#ffffff", repeat=True) \
    .header_padding(vertical=10, horizontal=12) \
    .header_style(font="SourceHanSansSC-Bold", font_size=11, line_height=14, align="center")
```

跨行/跨列单元格使用 `span(...)`：

```python
table = Table([
    ["地区", "收入", "增长"],
    ["华北", "¥120K", "+8%"],
    ["", "¥96K", "+5%"],
]).span(1, 0, rowspan=2)
```

分页遇到 `rowspan` 时会把断点移动到合法行边界，避免把一个跨行单元格拆到两页。

v1.1 起，单元格可以放入 `Frame` / `Text` / `Image` 等 builder：

```python
details = Frame().padding(4)
details.add_text("嵌套说明").font_size(10)

table = Table([["指标", "详情"], ["收入", details]]) \
    .footer([["合计", "216K"]], repeat=True, background="#e2e8f0") \
    .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
```

v2.1 起，普通富单元格可以更细粒度分页：单个未参与 `rowspan` / `colspan` 的 `Frame` 或 `Text` 富单元格会随表格切片拆分；当某一行有多个富内容且它们全都是未跨行/跨列的 `Text` 时，也可以一起拆分；未跨行/跨列的混合 `Text` + `Frame` 行也可以一起拆分。重复表头/表尾和基于原始逻辑行号的样式仍会保留。含跨行/跨列、图片、多 `Frame`，或其他混合富内容的行仍保持原子分页，以避免破坏 span 边界。

v2.0 起，auto-height 容器中的百分比 absolute `top` 会基于最终内容高度解析；`top >= "100%"` 在 auto-height 父容器中会被拒绝，因为这类布局无法得到有限高度。

## 元素 API

### `Text`

```python
frame.add_text("中文文本").font_size(14).line_height(18).color("#0f172a")
```

常用方法：

| 方法 | 说明 |
| --- | --- |
| `.font(name)` | 设置字体名 |
| `.font_size(size)` | 设置字号 |
| `.line_height(value)` | 设置行高 |
| `.color(value)` | 设置文字颜色 |
| `.margin(...)` | 设置外边距 |

> 注意：中文字体需要先注册可用字体；当前默认字体为 `Helvetica`，并不适合中文正式输出。中文连续文本会按实际字形宽度换行，表格测量、分页和最终绘制使用同一套换行逻辑。

## 字体注册

推荐从顶层 API 注册字体：

```python
from smart_report import register_font, set_default_font, set_fallback_fonts

register_font("SourceHanSansSC-Normal", "examples/fonts/SourceHanSansSC-Normal.ttf", set_default=True, fallback=True)
register_font("SourceHanSansSC-Bold", "examples/fonts/SourceHanSansSC-Bold.ttf")
set_default_font("SourceHanSansSC-Normal")
set_fallback_fonts(["SourceHanSansSC-Normal"])
```

`set_default=True` 只影响后续创建的节点；已经创建的 `Text` / `Table` 仍保留自己的字体设置。
`fallback=True` 或 `set_fallback_fonts(...)` 用于混合文本：当主字体不支持某个字符时，渲染器会切换到第一个覆盖该字符的 fallback 字体，同时测量、分页和绘制保持一致。
顶层还导出 `get_font()`、`get_fallback_fonts()`、`add_fallback_font()`、`get_default_font_name()`、`resolve_text_runs()` 和 `string_width()`，方便调试字体注册和测量行为。

### `Image`

支持 PNG/JPEG 等位图，以及 SVG。

```python
hero.add_image("examples/box.png").absolute(24, 218).size(260, 37)
hero.add_image("examples/box.svg").absolute(286, 218).size(260, 37)
hero.add_image(png_bytes).size(120, 80).contain().radius(8)
hero.add_image("examples/photo.png").size(120, 80).cover()
```

说明：

- PNG/JPEG 走 ReportLab `drawImage`
- SVG 走 `svglib -> ReportLab Drawing -> renderPDF.draw`
- `.contain()` 保持比例完整显示；`.cover()` 保持比例并裁剪填满区域
- `Image(...)` / `.add_image(...)` 可接受图片 bytes 或 `data:image/...;base64,...` 字符串
- 透明 PNG 建议搭配深色背景测试，以确认白色图案是否可见

### `Rect` / `Line` / `Spacer`

```python
canvas.add_rect().absolute(0, 0).size("100%", 120).background("#dbeafe").radius(12)
canvas.add_line().absolute(0, 64).size("100%", 0).stroke("#94a3b8", 1)
frame.add_spacer(12)
```

## 通用链式样式方法

所有元素和容器都继承一组通用链式方法。

| 方法 | 说明 |
| --- | --- |
| `.width(value)` | 设置宽度，支持点值、百分比字符串、`"auto"` |
| `.height(value)` | 设置高度，支持点值、百分比字符串、`"auto"` |
| `.size(width, height)` | 同时设置宽高 |
| `.absolute(left=0, top=0)` | 绝对定位，常用于 `Canvas` 内 |
| `.flow()` | 恢复流式布局 |
| `.z(value)` | 设置层级，值越大越靠上 |
| `.background(color)` | 设置背景色 |
| `.stroke(color, width)` | 设置描边 |
| `.opacity(value)` | 设置透明度 |
| `.radius(value)` | 设置圆角半径 |
| `.margin(...)` | 设置外边距 |
| `.padding(...)` | 设置内边距 |
| `.flex(direction="row", gap=None)` | 使用 flex 行/列布局 |
| `.grid(columns, gap=None)` | 使用固定列数网格布局 |
| `.columns(count, gap=None)` | 使用多列瀑布流布局 |
| `.keep_together()` | 分页时尽量整体移动到下一页，不拆分该节点 |
| `.keep_with_next()` | 分页时尽量和下一个流式节点放在同一页 |
| `.page_break_before()` | 在节点前强制分页 |
| `.page_break_after()` | 在节点后强制分页 |

布局示例：

```python
cards = Frame().grid(3, gap=10)
cards.add_text("收入").padding(10).background("#f8fafc")
cards.add_text("增长").padding(10).background("#f8fafc")

summary = Frame().flex("row", gap=12)
summary.add_text("A")
summary.add_text("B")

notes = Frame().columns(2, gap=16)
notes.add_text("长说明一")
notes.add_text("长说明二")
```

## `margin()` / `padding()` 参数语义

推荐使用命名参数，避免误解坐标顺序：

```python
Canvas().margin(top=24, right=24, bottom=20, left=24)
Frame().padding(vertical=24, horizontal=32)
Text("标题").margin(bottom=16)
```

兼容旧的元组写法：

```python
margin(24)                  # 四边都是 24
margin((24, 32))            # vertical=24, horizontal=32
margin((24, 24, 20, 24))    # top, right, bottom, left
```

## 尺寸单位

支持以下尺寸写法：

```python
width(240)       # 240pt
width("100%")    # 相对父容器宽度
width("20mm")    # 毫米
width("3cm")     # 厘米
height("auto")   # 内容自适应
```

## 当前限制

- 表格支持 `rowspan` / `colspan`；跨行单元格分页时会整体保留在同一页切片中
- 分页支持嵌套 `Frame` 和固定高度 `Rect` / `Spacer` 的更细粒度切分
- 图片和 SVG 仍保持原子分页；当前页空间不足时会整体移动到下一页，超出整页高度的图片不会分片
- 富表格单元格分页是保守实现：单个未跨行/跨列的 `Frame` / `Text` 富单元格可以拆分；一行多个未跨行/跨列且全为 `Text` 的富单元格也可以拆分；未跨行/跨列的混合 `Text` + `Frame` 行也可以拆分；跨行/跨列、图片、多 `Frame` 或其他混合富内容的行仍保持原子分页
- `flex` / `grid` / `columns` 是实用布局模式，并非完整 CSS 约束求解器
- 字体 fallback 已支持；复杂字体 shaping、bidi 和 OpenType 特性依赖可选 ReportLab 能力，默认路径不保证完整支持
