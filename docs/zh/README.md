# smart-report 中文文档

当前中文文档入口：

- [API 文档](./api.md)
- [中文表格示例](../../examples/zh_table_demo.py)

v2.4 已覆盖：

- 补齐公开 API 的中文说明
- 明确参数顺序、尺寸单位、分页和图层语义
- 为中文用户提供可复制运行的示例
- 顶层字体注册 API、中文连续文本换行、表格圆角边框
- 字体 fallback、中文行首/行尾基础禁则
- 表格 `rowspan` / `colspan`，分页时不切开跨行单元格
- 嵌套 Frame 与固定高度块的更深分页切分
- `flex`、`grid`、`columns` 实用布局模式
- 公开 API 导出、校验行为、测试和文档完成 1.0 稳定化
- 富表格单元格、分页控制、表格 footer/subtotal、自定义边框、图片 contain/cover/bytes 输入
- 保守版富表格单元格分页：无 `rowspan` / `colspan` 的单个 `Frame` 富单元格可跨页拆分，同时保留重复表头/表尾和逻辑行样式
- v1.3 将保守版富表格单元格分页扩展到单个未跨行/跨列的 `Text` 富单元格
- v1.5 将保守版富表格单元格分页扩展到一行多个未跨行/跨列的 `Text` 富单元格
- v2.0 修复 auto-height 容器中的百分比 absolute `top`，并明确图片/SVG 仍由用户自行控制尺寸或分页位置
- v2.1 支持未跨行/跨列的混合 `Text` + `Frame` 富单元格行分页，并让 `flex("column", gap=...)` 生效
- v2.2 增加 `typography("auto")`、`text_direction("rtl")` 和 `shape_text(...)`，用于阿拉伯文字形变与 bidi 显示顺序预处理，并贯穿测量、换行、分页、表格和绘制路径
- v2.2.1 更新 typography 示例，注册并使用内置 Noto Naskh Arabic 字体，避免阿拉伯文字回退到 Helvetica 后乱码
- v2.3 增加字体族注册、fallback-aware HarfBuzz-backed advanced 宽度测量，以及 RTL/mixed-script 示例；渲染仍保持 ReportLab canvas 文本路径
- v2.4 增加命名 section、section 级别的 header/footer/watermark 覆盖与抑制、section 页码占位符、PDF 元数据和自动 section outline
- v2.6 增加 `Table.auto_fit_columns()`，根据纯文本自然宽度自动调整列宽，支持 Fit Then Clamp 行为和可选 min/max 约束
- v2.7 增加 `Text.link(url)`，支持 whole-text PDF 外部 URL 链接注释，包括富 `Text` 表格单元格链接
- v2.8 增加 `.flex("row", wrap=True)` 行换行布局，单一 gap 同时控制水平和垂直间距

后续改动应保持向后兼容；破坏性 API 调整应留到下一个主版本。
