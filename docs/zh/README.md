# smart-report 中文文档

当前中文文档入口：

- [API 文档](./api.md)
- [中文表格示例](../../examples/zh_table_demo.py)

v1.1 已覆盖：

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

后续改动应保持向后兼容；破坏性 API 调整应留到下一个主版本。
