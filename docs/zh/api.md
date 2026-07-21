# smart-report 中文 API 参考

本文档描述当前公开 API 的推荐用法、参数语义、返回值和注意事项。版本更新信息请查看根目录 [CHANGELOG.md](../../CHANGELOG.md)。

## 快速开始

```python
from smart_report import Canvas, Frame, document, register_font

register_font(
    "SourceHanSansSC-Normal",
    "examples/fonts/SourceHanSansSC-Normal.ttf",
    set_default=True,
    fallback=True,
)

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

创建 `DocumentBuilder`。所有页面、全局页眉页脚、水印、section 和最终保存操作都从它开始。

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `document()` | 无 | `DocumentBuilder` | 创建新的文档构建器 |

### `DocumentBuilder.page(size="A4")`

创建页面并返回 `PageBuilder`。页面也是容器，可以继续添加 `Frame`、`Canvas`、`Table` 等内容。

| 参数 | 类型 / 可选值 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `size` | `"A4"`、`"LETTER"` 或 `(width, height)` | `"A4"` | 页面尺寸。元组单位是 pt，宽高必须为正数 |

```python
page = document().page("A4")
custom = document().page((595.0, 842.0))
```

### 保存和构建

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `doc.save(path)` | `path: str` | `None` | 构建并保存 PDF 文件 |
| `doc.save_to_bytes()` | 无 | `bytes` | 构建并返回 PDF 原始字节，不写文件 |
| `doc.build()` | 无 | `Document` | 构建不可变文档对象，可再调用 `save()` 或 `save_to_bytes()` |
| `doc.pages` | 属性 | `list[LayoutNode]` | 当前已添加页面，主要用于调试或测试 |

```python
pdf_bytes = doc.save_to_bytes()
assert pdf_bytes[:5] == b"%PDF-"
```

`save_to_bytes()` 是同步 CPU 密集操作。在 FastAPI / Starlette 等异步框架中，可用 `asyncio.to_thread(doc.save_to_bytes)` 避免阻塞事件循环；这只是集成方式，不会加速 PDF 生成。

### `doc.metadata(...)`

设置 PDF 元数据。只会覆盖非 `None` 字段，多次调用会合并已有值。

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `title` | `str | None` | `None` | 文档标题 |
| `author` | `str | None` | `None` | 作者 |
| `subject` | `str | None` | `None` | 主题 |
| `keywords` | `str | None` | `None` | 关键词，通常用逗号分隔 |

```python
doc.metadata(title="季度报告", author="数据团队", subject="Q4 总结", keywords="报告, 数据")
```

### `doc.header()` / `doc.footer()` / `doc.watermark()`

创建全局重复覆盖层，返回 `Canvas`。这些模板会复制到每个页面。

| 方法 | 返回 | 默认定位 / 层级 | 说明 |
| --- | --- | --- | --- |
| `doc.header()` | `Canvas` | `absolute(0, 0)`, `z(200)` | 页眉模板 |
| `doc.footer()` | `Canvas` | `absolute(0, 0)`, `z(210)` | 页脚模板，渲染时锚定到底部 |
| `doc.watermark()` | `Canvas` | `absolute(0, 0)`, `z(-100)` | 水印模板 |

文本中可使用页码占位符：

| 占位符 | 说明 |
| --- | --- |
| `{page_number}` | 文档绝对页码，从 1 开始 |
| `{total_pages}` | 文档绝对总页数 |
| `{section_name}` | 当前 section 名称 |
| `{section_page_number}` | 当前 section 计数组内页码 |
| `{section_total_pages}` | 当前 section 计数组总页数 |

```python
doc.header().height(40).add_text("第 {page_number} / {total_pages} 页").absolute("78%", 12)
```

### `doc.section(...)`

创建命名 section，返回 `SectionBuilder`。section 可拥有自己的页眉、页脚、水印和页码计数组。

| 参数 | 类型 / 可选值 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `name` | `str | None` | `None` | section 名称，出现在 outline 和 `{section_name}` 中 |
| `page_numbering` | `"restart"` 或 `"continue"` | `"restart"` | 是否重启 section 页码计数 |
| `outline` | `bool` | `True` | 是否写入 PDF outline |

| `SectionBuilder` 方法 | 返回 | 说明 |
| --- | --- | --- |
| `section.page(size="A4")` | `PageBuilder` | 在该 section 中新建页面 |
| `section.header()` | `Canvas` | 创建 section 级页眉，覆盖全局页眉 |
| `section.footer()` | `Canvas` | 创建 section 级页脚，覆盖全局页脚 |
| `section.watermark()` | `Canvas` | 创建 section 级水印，覆盖全局水印 |
| `section.suppress_header()` | `SectionBuilder` | 不继承全局页眉 |
| `section.suppress_footer()` | `SectionBuilder` | 不继承全局页脚 |
| `section.suppress_watermark()` | `SectionBuilder` | 不继承全局水印 |

Overlay 优先级：section 抑制 > section 模板 > 全局模板。空 section 不产生页面，也不产生 outline 条目。

```python
intro = doc.section("Introduction", page_numbering="restart", outline=True)
intro.header().height(28).add_text("{section_name} {section_page_number}/{section_total_pages}").absolute(36, 8)
intro.page("A4").add_frame().padding(36).add_text("Introduction")
```

## 容器 API

### `Frame`

`Frame` 是流式容器，子元素按从上到下的顺序排列，适合正文、段落、表格和普通报告区域。

```python
frame = Frame().padding(vertical=24, horizontal=32)
frame.add_text("标题").font_size(20).margin(bottom=16)
frame.add_text("正文内容").font_size(12)
page.add(frame)
```

### `Canvas`

`Canvas` 是图层容器，适合绝对定位、背景图、叠加文字、装饰图形和多图层报告。

```python
hero = Canvas().height(180).margin(top=24, right=24, bottom=20, left=24)
hero.add_rect().absolute(0, 0).size("100%", 180).background("#dbeafe").z(0)
hero.add_text("季度报告").absolute(24, 24).font_size(26).z(2)
page.add(hero)
```

### 容器添加方法

`PageBuilder`、`Frame`、`Canvas` 都是容器。

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `.add(child)` | 已创建的 builder | 当前容器 | 添加已有 `Text` / `Table` / `Frame` / `Canvas` / `Image` 等 |
| `.add_text(text)` | `text: str` | `Text` | 添加文本节点 |
| `.add_rich_text(text="")` | `text: str` | `RichText` | 添加富文本节点 |
| `.add_image(src)` | 路径、`Path`、bytes、data URL | `Image` | 添加图片节点 |
| `.add_rect()` | 无 | `Rect` | 添加矩形 |
| `.add_line()` | 无 | `Line` | 添加线段 |
| `.add_spacer(height)` | 固定尺寸 | `Spacer` | 添加流式空白 |
| `.add_canvas()` | 无 | `Canvas` | 添加嵌套图层容器 |
| `.add_frame()` | 无 | `Frame` | 添加嵌套流式容器 |
| `.add_table(rows)` | 二维数组 | `Table` | 添加表格 |

所有 `add_*` 方法都会把新节点放入当前容器，并返回新节点 builder，方便继续链式设置。

## `Table`

`Table(rows)` 接收二维数组。单元格可为字符串、数字，或 `Frame`、`Text`、`RichText`、`Image` 等 builder。

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
    .borders("#94a3b8", width=1) \
    .radius(10)
```

### 表格数据和尺寸

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `.rows(values)` | 二维数组 | `Table` | 替换表格数据 |
| `.cell(row_index, column_index, value)` | 行、列、值 | `Table` | 设置或扩展单元格；索引从 0 开始 |
| `.column_widths(values)` | `list[SizeInput]` | `Table` | 设置列宽，支持 pt、单位字符串、百分比和 `"auto"` |
| `.column_min_widths(values)` | `list[SizeInput]` | `Table` | 设置自动适配列宽下限，不支持 `"auto"` |
| `.column_max_widths(values)` | `list[SizeInput]` | `Table` | 设置自动适配列宽上限，不支持 `"auto"` |
| `.auto_fit_columns(columns=None)` | `None` 或列索引序列 | `Table` | 根据纯文本自然宽度自动适配列宽 |
| `.row_height(row_index, height)` | 行索引、固定尺寸 | `Table` | 设置逻辑行最小高度 |
| `.row_heights(values)` | 高度列表，`None` 表示跳过 | `Table` | 批量设置逻辑行最小高度 |
| `.cell_height(row_index, column_index, height)` | 行、列、固定尺寸 | `Table` | 设置逻辑单元格最小高度 |

行高和单元格高度是“最小高度”：内容更高时内容优先。高度值要求是固定点值兼容尺寸，例如 `36`、`"12mm"`、`"1cm"`；不支持百分比、`"auto"`、负数或无穷值。

`auto_fit_columns()` 只测量纯字符串单元格。富 `Frame` / `Text` / `RichText` / `Image` 单元格不参与自然宽度计算。自然宽度先测量，再应用 min/max 约束；较窄的适配表格不会被强制拉伸填满可用宽度。

### 表格对齐、内边距和溢出

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `.align(value)` | `"left"` / `"center"` / `"right"` 或列表 | `Table` | 设置水平对齐，可按列传列表 |
| `.valign(value)` | `"top"` / `"middle"` / `"bottom"` | `Table` | 设置垂直对齐 |
| `.text_overflow(value)` | `"wrap"` / `"clip"` / `"ellipsis"` | `Table` | 设置纯文本单元格溢出策略 |
| `.cell_padding(...)` | 固定尺寸或命名边 | `Table` | 设置默认单元格内边距 |
| `.header_padding(...)` | 固定尺寸或命名边 | `Table` | 设置表头内边距；未设置时沿用默认内边距 |

### 表头、表尾和边框

| 方法 | 关键参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `.header(rows=1, background=None, color=None, repeat=True)` | 表头行数、颜色、是否跨页重复 | `Table` | 配置开头若干行为表头 |
| `.header_style(...)` | `background`, `color`, `font`, `font_size`, `line_height`, `align` | `Table` | 覆盖表头样式 |
| `.footer(rows, repeat=False, background=None, color=None)` | footer 行、是否重复、颜色 | `Table` | 添加表尾行 |
| `.footer_style(...)` | `background`, `color`, `font`, `font_size`, `line_height`, `align` | `Table` | 覆盖表尾样式 |
| `.subtotal(row, repeat=False, background="#f1f5f9", color=None)` | 单行 footer | `Table` | 添加单行汇总 |
| `.borders(color="#cbd5e1", width=1, inner_width=None, outer_width=None)` | 边框颜色和宽度 | `Table` | 设置内外边框 |
| `.border_collapse(value=True)` | 布尔值 | `Table` | 合并相邻单元格边框，避免双线效果 |
| `.cell_border(row_index, column_index, color=None, width=1)` | 行、列、边框样式 | `Table` | 覆盖单元格边框 |
| `.zebra(background="#f8fafc")` | 背景色 | `Table` | 设置隔行背景 |
| `.repeat_header(value=True)` | 布尔值 | `Table` | 单独控制表头跨页重复 |

如只想设置文字颜色但不想显示边框，请显式关闭边框：`.borders("transparent", width=0)`。

### 行、列、单元格样式和合并

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `.row_style(index, ...)` | 行索引和样式关键字 | `Table` | 覆盖指定逻辑行样式 |
| `.column_style(index, ...)` | 列索引和样式关键字 | `Table` | 覆盖指定列样式 |
| `.cell_style(row_index, column_index, ...)` | 行、列和样式关键字 | `Table` | 覆盖指定单元格样式 |
| `.span(row_index, column_index, rowspan=1, colspan=1)` | 行、列、跨行、跨列 | `Table` | 合并单元格 |
| `.radius(value)` | 统一值、四元组或命名角 | `Table` | 设置表格外边框圆角，并裁剪外角背景 |

`row_style(...)`、`column_style(...)`、`cell_style(...)` 支持：`background`、`color`、`align`、`font`、`font_size`、`line_height`、`text_overflow`、`valign`。

样式优先级：`cell_style > row_style > column_style > 表头/表尾/斑马纹/表格默认样式`。索引基于原始逻辑行列；即使跨页拆分并重复表头，样式也按原始行号生效。

```python
table = Table(rows) \
    .column_style(2, color="#166534") \
    .row_style(3, background="#ecfeff") \
    .cell_style(6, 1, background="#dcfce7", color="#166534", align="right")
```

```python
Table([
    ["地区", "收入", "增长"],
    ["华北", "¥120K", "+8%"],
    ["", "¥96K", "+5%"],
]).span(1, 0, rowspan=2)
```

分页遇到 `rowspan` 时会把断点移动到合法行边界，避免把跨行单元格拆到两页。

## `Text`

`Text(text)` 创建普通文本节点。固定宽高后可使用水平/垂直对齐和溢出策略。

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `.text(value)` | `str` | `Text` | 替换文本内容 |
| `.font(name)` | 字体名 | `Text` | 设置字体 |
| `.font_family(name)` | 已注册字体族 | `Text` | 使用字体族 regular face |
| `.font_size(size)` | pt 数值 | `Text` | 设置字号；若未显式设置行高，行高变为 `size * 1.2` |
| `.line_height(value)` | pt 数值 | `Text` | 设置固定行高，并关闭自动行高 |
| `.color(value)` | 颜色值 | `Text` | 设置文字颜色 |
| `.align(value)` | `"left"` / `"center"` / `"right"` | `Text` | 设置文本框内水平对齐，需给宽度才明显 |
| `.valign(value)` | `"top"` / `"middle"` / `"bottom"` | `Text` | 设置固定高度文本框内垂直对齐 |
| `.letter_spacing(value)` | 数值、`"0.05em"`、`"5%"` | `Text` | 设置字距 |
| `.text_overflow(value)` | `"wrap"` / `"clip"` / `"ellipsis"` | `Text` | 设置固定文本框溢出策略 |
| `.link(url)` | 非空字符串 | `Text` | 为整个文本节点添加 PDF 外部 URL 链接 |
| `.typography(value)` | `"plain"` / `"auto"` / `"advanced"` | `Text` | 设置文字预处理/测量模式 |
| `.text_direction(value)` | `"auto"` / `"ltr"` / `"rtl"` | `Text` | 设置文字方向 |

```python
frame.add_text("体质辨析：气虚质 + 痰湿质") \
    .size("100%", 32) \
    .font_size(10) \
    .align("center") \
    .valign("middle") \
    .letter_spacing("0.05em")
```

`text_overflow("clip")` 使用类似表格单元格的单行固定框行为：硬换行会折叠为空格，并直接裁切文本框外内容。`text_overflow("ellipsis")` 会先按文本框宽度换行，再按固定高度保留可见行，内容被隐藏时在最后一条可见行追加 `…`。默认 `wrap` 保持自动换行。

```python
frame.add_text("过长的指标名称需要适配固定区域，并在固定高度内显示多行省略号") \
    .size(96, 36) \
    .line_height(12) \
    .text_overflow("ellipsis")
```

表格纯文本单元格的 `text_overflow("ellipsis")` 仍保持单行省略行为，用于稳定表格行高。

`.link(url)` 不会自动改变样式。如需视觉提示，请手动设置颜色、下划线替代样式或背景。当前仅支持 whole-text 链接，不支持行内子字符串链接、Markdown/HTML 解析或任意注解 API。

## `RichText`

`RichText` 是独立富文本元素，适合同一段文字中混合字体、字号、颜色、加粗、字距和硬换行。它不解析 HTML/Markdown。

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `.text(value)` | `str` | `RichText` | 清空 runs，并设置为一个普通文本 run |
| `.span(text, font=None, font_family=None, font_size=None, color=None, bold=False, letter_spacing=None)` | 文本和 span 样式 | `RichText` | 追加行内片段 |
| `.letter_spacing(value)` | 数值、`"0.05em"`、`"5%"` | `RichText` | 设置全局字距；span 级设置会覆盖 |
| `.br(count=1)` | 正整数 | `RichText` | 追加一个或多个硬换行 |
| `.clear()` | 无 | `RichText` | 清空所有 runs |
| `.align(value)` | `"left"` / `"center"` / `"right"` | `RichText` | 设置富文本框整体水平对齐 |
| `.valign(value)` | `"top"` / `"middle"` / `"bottom"` | `RichText` | 设置富文本框整体垂直对齐 |

```python
rich = (
    RichText()
    .letter_spacing("4%")
    .span("收入 ", font_size=12, color="#0f172a")
    .span("+18%", font="Helvetica", font_size=14, color="#166534", bold=True, letter_spacing="0.08em")
    .br()
    .span("企业客户续约强劲", font_size=10, color="#475569")
    .width(180)
)
frame.add(rich)
```

`RichText.align(...)` / `.valign(...)` 是整个富文本框的对齐方式。行内 span 共享同一个 line box，不提供单个 span 独立左/中/右或上/中/下对齐。如需某段内容独立对齐，请拆成单独的 `Text` / `RichText` 节点。

## `Image`

支持 PNG/JPEG 等位图和 SVG。图片可来自字符串路径、`pathlib.Path`、bytes 或 `data:image/...;base64,...` 字符串。

| 方法 | 参数 | 返回 | 说明 |
| --- | --- | --- | --- |
| `Image(src)` | 图片来源 | `Image` | 创建图片节点 |
| `.src(value)` | 图片来源 | `Image` | 替换图片来源 |
| `.bytes(value)` | `bytes` | `Image` | 直接设置图片 bytes |
| `.fit(value)` | `"stretch"` / `"contain"` / `"cover"` | `Image` | 设置适配方式 |
| `.contain()` | 无 | `Image` | 等同 `.fit("contain")`，保持比例完整显示 |
| `.cover()` | 无 | `Image` | 等同 `.fit("cover")`，保持比例并裁剪填满 |
| `.radius(...)` | 统一值、四元组或命名角 | `Image` | 设置圆角；圆角应用在适配后的实际图片区域 |

```python
hero.add_image("examples/box.png").absolute(24, 218).size(260, 37)
hero.add_image("examples/box.svg").absolute(286, 218).size(260, 37)
hero.add_image(png_bytes).size(120, 80).contain().radius(8)
hero.add_image("examples/photo.png").size(120, 80).cover().radius((12, 12, 0, 0))
```

相对路径以运行脚本时的当前工作目录为基准。示例脚本中建议用 `Path(__file__).resolve().parent / "image.png"` 转成绝对路径。

## `Rect` / `Line` / `Spacer`

### `Rect`

矩形图形节点，用于背景块、卡片底色、遮罩、边框和装饰形状。

```python
canvas.add_rect().absolute(0, 0).size("100%", 120).background("#dbeafe").radius(12)
```

常用方法：`.size(...)`、`.absolute(...)`、`.background(...)`、`.stroke(...)`、`.radius(...)`、`.opacity(...)`、`.z(...)`。

### `Line`

线段节点。起点为 `.absolute(left, top)`，终点由 `.size(width, height)` 决定，即 `(left + width, top + height)`。

```python
canvas.add_line().absolute(36, 120).size(520, 0).stroke("#cbd5e1", 0.8)
canvas.add_line().absolute(80, 80).size(0, 160).stroke("#94a3b8", 1)
canvas.add_line().absolute(80, 80).size(120, 60).stroke("#2563eb", 1)
```

### `Spacer`

流式空白节点，只占据高度，不绘制内容。`add_spacer(height)` 要求固定点值兼容尺寸，不支持百分比或 `"auto"`。

```python
frame.add_text("标题")
frame.add_spacer(16)
frame.add_text("正文")
```

## 字体注册

中文正式输出应注册可用中文字体。默认 `Helvetica` 不适合中文正式输出。

```python
from smart_report import register_font, register_font_family, set_default_font, set_fallback_fonts

register_font("SourceHanSansSC-Normal", "examples/fonts/SourceHanSansSC-Normal.ttf", set_default=True, fallback=True)
register_font("SourceHanSansSC-Bold", "examples/fonts/SourceHanSansSC-Bold.ttf")
set_default_font("SourceHanSansSC-Normal")
set_fallback_fonts(["SourceHanSansSC-Normal"])
```

| 方法 / 类型 | 说明 |
| --- | --- |
| `register_font(name, path, set_default=False, fallback=False)` | 注册单个 TTF 字体 |
| `set_default_font(name)` / `get_default_font_name()` | 设置或读取默认字体名 |
| `set_fallback_fonts(names)` / `get_fallback_fonts()` / `add_fallback_font(name)` | 管理 fallback 字体链 |
| `register_font_family(name, regular=..., bold=..., italic=..., bold_italic=..., fallback=False)` | 注册字体族 |
| `set_default_font_family(name)` / `get_font_family(name)` | 设置默认字体族或读取字体族配置 |
| `set_fallback_font_families(names)` / `get_fallback_font_families()` / `add_fallback_font_family(name)` | 管理字体族 fallback 链 |
| `get_font(name)` | 读取已注册字体信息 |
| `resolve_text_runs(text, font_name)` | 调试混合文本如何拆成 fallback 字体 run |
| `string_width(text, font_name, size)` | 普通宽度测量 |
| `shaped_string_width(text, font_name, size)` | advanced typography 宽度测量 |

`typography("auto")` 会在测量、换行、分页和绘制前对阿拉伯文字做形变，并按 bidi 规则生成显示顺序。`typography("advanced")` 在注册 TTF 可用时按 fallback 字体 run 使用 HarfBuzz metrics 做 shaping-aware 测量和换行，但最终仍通过 ReportLab canvas 文本 API 绘制；精确 glyph positioning、任意 glyph-id 绘制、竖排和彩色字体不保证。

## 通用链式样式方法

所有元素和容器都继承一组通用链式方法。除特殊说明外，方法都会返回当前 builder，便于继续链式调用。

### 尺寸、位置和图层

| 方法 | 参数 | 说明 |
| --- | --- | --- |
| `.width(value)` | 尺寸值 | 设置宽度 |
| `.height(value)` | 尺寸值 | 设置高度 |
| `.size(width, height)` | 尺寸值、尺寸值 | 同时设置宽高 |
| `.name(value)` | `str` | 设置调试名称 |
| `.absolute(left=0, top=0)` | 尺寸值 | 在父容器内容盒中绝对定位 |
| `.flow()` | 无 | 恢复流式布局 |
| `.z(value)` | `int` | 设置层级，值越大越靠上 |
| `.overflow("hidden")` | `"visible"` / `"hidden"` | 裁剪超出节点边界的子内容 |

### 外观和文本

| 方法 | 参数 | 说明 |
| --- | --- | --- |
| `.background(value)` | 颜色或 `None` | 设置背景色；`None` 表示不绘制背景 |
| `.stroke(color, width)` | 颜色、pt 宽度 | 设置描边 / 边框 |
| `.opacity(value)` | `0.0` 到 `1.0` | 设置整体透明度 |
| `.radius(value)` | 统一值、四元组或命名角 | 设置圆角半径 |
| `.color(value)` | 颜色 | 设置前景 / 文字颜色 |
| `.font(name)` | 字体名 | 设置字体 |
| `.font_family(name)` | 字体族名 | 设置字体族 |
| `.font_size(size)` | pt 数值 | 设置字号 |
| `.line_height(value)` | pt 数值 | 设置行高 |
| `.typography(value)` | `"plain"` / `"auto"` / `"advanced"` | 设置文字预处理模式 |
| `.text_direction(value)` | `"auto"` / `"ltr"` / `"rtl"` | 设置文字方向 |

### 布局和分页控制

| 方法 | 参数 | 说明 |
| --- | --- | --- |
| `.layout(value)` | `"flow"` / `"flex"` / `"grid"` / `"columns"` | 直接设置布局模式；通常优先使用快捷方法 |
| `.gap(value)` | 固定尺寸 | 设置布局间距 |
| `.flex(direction="row", gap=None, wrap=False, justify="start", align="start", row_gap=None, column_gap=None)` | 见下文 | 使用 flex 行/列布局 |
| `.grid(columns, gap=None)` | 列数、间距 | 使用固定列数网格布局 |
| `.columns(count, gap=None)` | 列数、间距 | 使用多列瀑布流布局 |
| `.keep_together(value=True)` | 布尔值 | 分页时尽量整体移动到下一页 |
| `.keep_with_next(value=True)` | 布尔值 | 分页时尽量和下一个流式节点同页 |
| `.page_break_before(value=True)` | 布尔值 | 在节点前强制分页 |
| `.page_break_after(value=True)` | 布尔值 | 在节点后强制分页 |

`flex()` 参数：

| 参数 | 可选值 / 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `direction` | `"row"` / `"column"` | `"row"` | 主轴方向 |
| `gap` | 固定尺寸或 `None` | `None` | 行列间距默认值 |
| `wrap` | `bool` | `False` | 仅 `direction="row"` 支持换行 |
| `justify` | `"start"` / `"center"` / `"end"` / `"space-between"` | `"start"` | 主轴对齐 |
| `align` | `"start"` / `"center"` / `"end"` | `"start"` | 交叉轴对齐 |
| `row_gap` | 固定尺寸或 `None` | `None` | 纵向间距，回退到 `gap` |
| `column_gap` | 固定尺寸或 `None` | `None` | 横向间距，回退到 `gap` |

`flex` 不是完整 CSS flexbox：不支持 `stretch`、`space-around`、`space-evenly`、flex grow/shrink/basis、反向方向或列方向换行。分页时不保证按行边界切分。

## `margin()` / `padding()` 参数语义

推荐使用命名参数，避免误解坐标顺序。

```python
Canvas().margin(top=24, right=24, bottom=20, left=24)
Frame().padding(vertical=24, horizontal=32)
Text("标题").margin(bottom=16)
```

| 写法 | 说明 |
| --- | --- |
| `margin(24)` / `padding(24)` | 四边都是 24 |
| `margin((24, 32))` | `vertical=24`, `horizontal=32` |
| `margin((24, 24, 20, 24))` | `top, right, bottom, left` |
| `margin(top=..., right=..., bottom=..., left=...)` | 明确指定方向 |
| `padding(vertical=..., horizontal=...)` | 同时指定上下和左右 |

位置、内外边距、圆角和表格内边距要求固定点值兼容尺寸；百分比和 `"auto"` 不适用于这些边距类值。

## 尺寸单位

| 写法 | 含义 |
| --- | --- |
| `240` | 240 pt |
| `"100%"` | 相对父容器对应方向的百分比 |
| `"20mm"` | 20 毫米 |
| `"3cm"` | 3 厘米 |
| `"auto"` | 内容自适应，通常用于宽高 |

```python
frame.width(240)
frame.width("100%")
frame.height("auto")
```

## 圆角

`.radius(...)` 支持统一圆角、四角元组和命名角。顺序统一为：左上、右上、右下、左下。

```python
Image("avatar.png").size(64, 64).cover().radius(8)
Image("hero.png").size(120, 80).cover().radius((12, 12, 0, 0))
Frame().background("#fff").radius(top_left=12, bottom_right=12)
```

圆角值必须是固定点值兼容尺寸且非负。不要同时使用位置参数和命名角参数。

## 颜色值

颜色解析用于 `background(...)`、`color(...)`、`stroke(...)`、表格背景和文字颜色等。

```python
background("white")
background("transparent")
background("#ffffff")
background("#ffffff80")
background("rgba(255,255,255,0.6)")
background(None)
```

`None` 表示不绘制背景；`"transparent"` 表示透明色。

## 当前限制

- 表格支持 `rowspan` / `colspan`，但跨行单元格分页时会整体保留在同一页切片中。
- 图片和 SVG 保持原子分页；当前页空间不足时整体移动到下一页，超出整页高度的图片不会分片。
- 富表格单元格分页是保守实现：简单未跨行/跨列的 `Frame` / `Text` / `RichText` 情况可以拆分；跨行/跨列、图片、多 `Frame` 或复杂混合富内容保持原子分页。
- `flex` / `grid` / `columns` 是实用布局模式，并非完整 CSS 约束求解器。
- Flex 行换行仅支持行方向；不支持列方向换行，也不保证按行分页。
- 字体 fallback 已支持；复杂 shaping、bidi 和 OpenType 特性依赖可选能力，默认路径不保证完整文本引擎行为。
- 表格自动适配仅支持纯字符串单元格；富 `Frame` / `Text` / `RichText` / `Image` 单元格不参与自然宽度计算。
- `Text.link(url)` 仅支持 whole-text 链接；不支持行内子字符串链接、Markdown/HTML 解析、自动链接样式、纯字符串表格单元格链接或任意注解 API。
