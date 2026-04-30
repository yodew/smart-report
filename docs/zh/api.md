# smart-report 中文 API 文档

本文档面向中文使用者，描述当前公开 API 的推荐用法、参数语义和注意事项。

## 快速开始

```python
from smart_report import Canvas, Frame, document

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

`Table` 接受二维数组，并提供适合报表场景的列宽、对齐、单元格 padding、表头样式、斑马纹和跨页重复表头能力。

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
    .stroke("#94a3b8", 1)

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
| `.zebra(background="#f8fafc")` | 设置隔行背景色 |
| `.repeat_header(value=True)` | 单独控制跨页重复表头 |
| `.row_style(index, ...)` | 覆盖指定逻辑行的 `background` / `color` / `align` |
| `.column_style(index, ...)` | 覆盖指定列的 `background` / `color` / `align` |
| `.cell_style(row_index, column_index, ...)` | 覆盖指定单元格的 `background` / `color` / `align` |

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

当前表格限制：

- 暂不支持 `rowspan` / `colspan`
- 支持基础跨页拆分，但复杂单元格内容仍需后续增强

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

> 注意：中文字体需要先注册可用字体；当前默认字体为 `Helvetica`，并不适合中文正式输出。

### `Image`

支持 PNG/JPEG 等位图，以及 SVG。

```python
hero.add_image("examples/box.png").absolute(24, 218).size(260, 37)
hero.add_image("examples/box.svg").absolute(286, 218).size(260, 37)
```

说明：

- PNG/JPEG 走 ReportLab `drawImage`
- SVG 走 `svglib -> ReportLab Drawing -> renderPDF.draw`
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

- 表格暂不支持 `rowspan` / `colspan`
- 分页主要针对 `Frame` 内的流式内容
- 大型非文本/非表格块可能整体移动到下一页，而不是深度拆分
- 尚未实现 flex/grid/columns 约束布局
- 中文字体注册和字体 fallback 需要在后续版本系统化
