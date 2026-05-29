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
| `doc.save_to_bytes()` | 渲染并返回 PDF 原始字节；不写入文件 |

页码占位符只在文本中生效：

```python
doc.header().height(40).add_text("第 {page_number} / {total_pages} 页").absolute("78%", 12)
```

### `doc.metadata(...)` (v2.4)

设置 PDF 文档元数据，支持链式调用：

```python
doc.metadata(title="季度报告", author="团队", subject="Q4 总结", keywords="报告, 数据")
```

| 参数 | 说明 |
| --- | --- |
| `title` | 文档标题 |
| `author` | 作者 |
| `subject` | 主题 |
| `keywords` | 关键词，逗号分隔 |

仅非 `None` 的参数会覆盖已有值；多次调用会合并字段。

### `doc.section(...)` (v2.4)

创建命名 section，返回 `SectionBuilder`：

```python
section = doc.section("Introduction", page_numbering="restart", outline=True)
page = section.page("A4")
```

| 参数 | 说明 |
| --- | --- |
| `name` | section 名称，出现在 outline 和 `{section_name}` 占位符中 |
| `page_numbering` | `"restart"`（默认）重新开始计数，`"continue"` 加入当前计数组 |
| `outline` | `True`（默认）在 PDF outline 中显示，`False` 则隐藏 |

`SectionBuilder` 方法：

| 方法 | 说明 |
| --- | --- |
| `section.page(size="A4")` | 在该 section 中新建页面 |
| `section.header()` | 创建 section 级别页眉，覆盖同类型全局页眉 |
| `section.footer()` | 创建 section 级别页脚，覆盖同类型全局页脚 |
| `section.watermark()` | 创建 section 级别水印，覆盖同类型全局水印 |
| `section.suppress_header()` | 抑制该 section 的全局页眉回退 |
| `section.suppress_footer()` | 抑制该 section 的全局页脚回退 |
| `section.suppress_watermark()` | 抑制该 section 的全局水印回退 |

### Section 占位符 (v2.4)

| 占位符 | 说明 |
| --- | --- |
| `{section_name}` | 当前 section 名称 |
| `{section_page_number}` | 当前 section 内的物理页码（从 1 开始） |
| `{section_total_pages}` | 当前计数组的总物理页数 |
| `{page_number}` | 文档绝对页码（不受 section 影响） |
| `{total_pages}` | 文档绝对总页数 |

`page_numbering="restart"` 开始新的计数组，`"continue"` 加入上一个计数组共享 `{section_total_pages}`。

Overlay 覆盖优先级：section 抑制 > section 模板 > 全局模板。

空 section 不产生页面也不产生 outline 条目。

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
| `.auto_fit_columns(columns=None)` | 启用列宽自动适配；不传参数时适配所有列，传入列索引列表时仅适配选中列。遗留 `column_widths(["auto"])` 不传 `.auto_fit_columns()` 仍保持等分行为 |
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

### 列宽自动适配 (v2.6)

```python
table = Table([
    ["地区", "收入", "增长"],
    ["APAC", "$1.20M", "+18%"],
    ["EMEA", "$0.98M", "+11%"],
    ["North America", "$1.60M", "+23%"],
]).auto_fit_columns()
```

`.auto_fit_columns()` 根据每个单元格的纯文本自然宽度（含水平内边距）自动设置列宽。传入列索引列表（如 `.auto_fit_columns([1, 2])`）时仅适配选中列，其余列保持原有宽度。

**Fit Then Clamp 行为**：先测量自然宽度，再应用 `column_min_widths` 和 `column_max_widths` 约束。较窄的适配表格不会被拉伸填满可用宽度。

**兼容性**：遗留写法 `column_widths(["auto"])` 在不调用 `.auto_fit_columns()` 时仍保持等分分配，向后兼容。

**限制**：v2.6 仅支持纯字符串单元格的自然宽度测量；富 `Frame` / `Text` / `Image` 单元格不参与自动适配计算。连字（hyphenation）、多行省略号、富单元格自然宽度和 Rich Text Links 在 v2.6 中不可用。

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
frame.add_text("مرحبا smart-report").typography("auto").text_direction("rtl")
```

常用方法：

| 方法 | 说明 |
| --- | --- |
| `.font(name)` | 设置字体名 |
| `.font_size(size)` | 设置字号 |
| `.line_height(value)` | 设置行高 |
| `.typography(value)` | 设置文字预处理模式，支持 `"plain"`、`"auto"`、`"advanced"` |
| `.text_direction(value)` | 设置文字方向，支持 `"auto"`、`"ltr"`、`"rtl"` |
| `.color(value)` | 设置文字颜色 |
| `.link(url)` | 为整个文字节点添加 PDF 外部 URL 链接注释；`url` 必须为非空字符串 |
| `.margin(...)` | 设置外边距 |

> 注意：中文字体需要先注册可用字体；当前默认字体为 `Helvetica`，并不适合中文正式输出。中文连续文本会按实际字形宽度换行，表格测量、分页和最终绘制使用同一套换行逻辑。

v2.2 起，`typography("auto")` 会在测量、换行、分页和绘制前对阿拉伯文字做形变，并按 bidi 规则生成显示顺序：

```python
from smart_report import shape_text

text = "مرحبا smart-report"
frame.add_text(text).typography("auto").text_direction("rtl")
display_text = shape_text(text, "auto", "rtl")
```

正式输出请注册支持阿拉伯文/希伯来文的 TTF 字体。`examples/v2_2_typography.py` 会注册内置的 `NotoNaskhArabic-Medium.ttf` / `NotoNaskhArabic-Bold.ttf` 并用于阿拉伯文本渲染，避免回退到 `Helvetica` 后乱码。当前功能是实用预处理层，不承诺完整 HarfBuzz/OpenType glyph positioning、Indic 文字 shaping 或高级字距调整。

### `Text.link(url)` (v2.7)

```python
linked = Text("Visit docs").link("https://example.com/docs").color("#2563eb")
frame.add(linked)
```

`.link(url)` 为整个文字节点添加 PDF 外部 URL 链接注释。点击文字区域即可在浏览器中打开链接。链接在 `Frame` 内的独立 `Text` 节点和富 `Text` 表格单元格中均可使用。

无自动链接样式。用户可通过现有的 Text 样式 API 手动设置颜色或其他视觉提示。

**限制**：仅支持 whole-text 链接，不支持行内子字符串链接、markdown/HTML 解析或任意注解 API。纯字符串表格单元格不支持链接。

## Flex 行换行布局 (v2.8)

```python
cards = Frame().flex("row", gap=10, wrap=True).width(480)
cards.add_text("卡片 1").width(140).padding(10).background("#dbeafe")
cards.add_text("卡片 2").width(140).padding(10).background("#dbeafe")
cards.add_text("卡片 3").width(140).padding(10).background("#dbeafe")
cards.add_text("卡片 4").width(140).padding(10).background("#dbeafe")
```

`.flex("row", gap=10, wrap=True)` 从左到右排列子元素，当子元素总宽度（含间距）超过容器宽度时自动换行到下一行。同一个 `gap` 值同时用于同行元素之间的水平间距和行与行之间的垂直间距。设置了显式宽度的子元素保持该宽度；没有宽度的文本子元素按自然文本宽度测量。单个子元素宽度超过容器时独占一行，可能水平溢出。

**限制**：仅支持行方向换行（`flex("column", wrap=True)` 会抛出 `ValueError`）；不支持列方向换行。不是完整 CSS flexbox 实现。分页时不保证按行边界切分。

## Flex 精细化控制 (v2.9)

```python
row = Frame().flex("row", gap=8, justify="center", align="center").width(400)
row.add_text("A").width(80).padding(8).background("#dbeafe")
row.add_text("B").width(80).padding(8).background("#dbeafe")

wrapped = Frame().flex("row", gap=8, wrap=True, row_gap=20, column_gap=8).width(300)
wrapped.add_text("项目 1").width(80).padding(8).background("#fef3c7")
wrapped.add_text("项目 2").width(80).padding(8).background("#fef3c7")

col = Frame().flex("column", gap=8, justify="space-between", align="center").width(300).height(200)
col.add_text("顶部").padding(8).background("#ede9fe")
col.add_text("底部").padding(8).background("#ede9fe")
```

`flex()` 新增四个关键字参数：`justify`、`align`、`row_gap` 和 `column_gap`。

`justify` 控制主轴放置。支持值：`start`、`center`、`end`、`space-between`。非换行行和换行行（逐行）均有效。Column justify 仅在父容器有显式内容高度时分配垂直空间；auto-height column justify 为 no-op。

`align` 控制交叉轴放置。支持值：`start`、`center`、`end`。行模式下按最高行高偏移各项；列模式下按内容宽度水平偏移各项。

`row_gap` 和 `column_gap` 分别设置轴向间距。行和换行行水平间距使用 `column_gap`（回退到 `gap`）。换行行垂直推进和列堆叠使用 `row_gap`（回退到 `gap`）。列堆叠忽略 `column_gap`。

**限制**：不是完整 CSS flexbox 实现。不支持 `stretch`、`space-around`、`space-evenly`。不支持 flex grow/shrink/basis。不支持反向方向。不支持列方向换行。分页时不保证按行边界切分。

## save_to_bytes (v2.10)

```python
from smart_report import document

doc = document()
page = doc.page("A4")
page.add_frame().padding(36).add_text("Hello from bytes")

pdf_bytes = doc.save_to_bytes()
assert isinstance(pdf_bytes, bytes)
assert pdf_bytes[:5] == b"%PDF-"
```

`save_to_bytes()` 构建并渲染文档，返回 PDF 原始字节而非写入文件。它与 `save()` 共享相同的 4-pass 渲染流程，可在 `DocumentBuilder` 和构建后的 `Document` 对象上调用。

### 异步集成（FastAPI / Starlette 等）

`save_to_bytes()` 是同步且 CPU 密集的。要与异步框架集成而不阻塞事件循环，可使用 `asyncio.to_thread` 卸载到线程池：

```python
import asyncio
from fastapi import FastAPI
from fastapi.responses import Response
from smart_report import document

app = FastAPI()

@app.get("/report")
async def generate_report():
    doc = document()
    page = doc.page("A4")
    page.add_frame().padding(36).add_text("异步报告")

    pdf_bytes = await asyncio.to_thread(doc.save_to_bytes)
    return Response(content=pdf_bytes, media_type="application/pdf")
```

`asyncio.to_thread` 在单独线程中执行阻塞调用，保持事件循环响应。它不会加速 PDF 生成；只是防止单次慢渲染拖慢其他请求。

要实现真正的并行 CPU 密集型批量生成（同时生成大量 PDF），请使用 `ProcessPoolExecutor` 或类似的基于进程的工作池。线程共享 GIL，基于线程的并发不会加速实际的渲染工作。

**限制**：smart-report 没有原生异步渲染。`save_to_bytes()` 是阻塞的。`asyncio.to_thread` 是集成模式，不是性能优化。不存在 `asave_to_bytes` 或 `asave`。

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
`fallback=True` 或 `set_fallback_fonts(...)` 用于混合文本：当主字体不支持某个字符时，渲染器会切换到第一个覆盖该字符的 fallback 字体；普通测量和 advanced HarfBuzz 测量都会按 fallback 字体 run 计算，从而让分页和绘制使用一致的换行结果。
顶层还导出 `get_font()`、`get_fallback_fonts()`、`add_fallback_font()`、`get_default_font_name()`、`resolve_text_runs()` 和 `string_width()`，方便调试字体注册和测量行为。

v2.3 起，可以注册字体族并使用 advanced typography 宽度测量：

```python
from smart_report import register_font_family, shaped_string_width

register_font_family(
    "NotoNaskhArabic",
    regular="examples/fonts/NotoNaskhArabic-Medium.ttf",
    bold="examples/fonts/NotoNaskhArabic-Bold.ttf",
    fallback=True,
)

frame.add_text("مرحبا smart-report") \
    .font_family("NotoNaskhArabic") \
    .typography("advanced") \
    .text_direction("rtl")

width = shaped_string_width("مرحبا", "NotoNaskhArabic", 14)
```

`typography("advanced")` 在注册 TTF 可用时按 fallback 字体 run 使用 HarfBuzz metrics 做 shaping-aware 测量和换行，但最终仍通过 ReportLab canvas 文本 API 绘制；精确 glyph positioning、任意 glyph-id 绘制、竖排和彩色字体仍不保证。

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
| `.typography(value)` | 设置文字预处理模式，支持 `"plain"`、`"auto"`、`"advanced"` |
| `.text_direction(value)` | 设置文字方向，支持 `"auto"`、`"ltr"`、`"rtl"` |
| `.flex(direction="row", gap=None, wrap=False, justify="start", align="start", row_gap=None, column_gap=None)` | 使用 flex 行/列布局；`wrap=True` 启用行换行（仅行方向）；`justify` 控制主轴对齐，`align` 控制交叉轴对齐；`row_gap` / `column_gap` 分别设置纵轴和横轴间距 |
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
- Flex 行换行仅支持行方向；不支持列方向换行，无行感知分页保证
- 字体 fallback 已支持；复杂字体 shaping、bidi 和 OpenType 特性依赖可选 ReportLab 能力，默认路径不保证完整支持
- 表格自动适配 (`auto_fit_columns`) 仅支持纯字符串单元格；富 `Frame` / `Text` / `Image` 单元格不参与 v2.6 自动宽度计算
- `Text.link(url)` 仅支持 whole-text 链接；不支持行内子字符串链接、markdown/HTML 解析、自动链接样式、纯字符串表格单元格链接 API 或任意注解 API
