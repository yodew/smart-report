# smart-report 中文文档

smart-report 是一个基于 ReportLab canvas 的 Python PDF 生成库，提供接近现代布局系统的链式 API。它适合生成报表、表格文档、多图层报告和需要精确位置控制的 PDF。

## 文档入口

- [中文 API 参考](./api.md)：按入口、容器、元素、表格、字体、尺寸、颜色和通用链式方法组织。
- [更新日志](../../CHANGELOG.md)：查看每个版本新增、变更和修复内容。
- [中文表格示例](../../examples/zh_table_demo.py)：可运行的中文表格 PDF 示例。
- [v2.11 分层表格区域示例](../../examples/v2_11_layered_table_region.py)：展示页面背景、居中表格和分层区域。

## 推荐阅读顺序

1. 先阅读 API 参考中的“快速开始”和“顶层入口”，了解 `document()`、页面、保存和页眉页脚。
2. 再阅读“容器 API”，选择使用 `Frame` 做流式正文，或使用 `Canvas` 做绝对定位和图层叠加。
3. 如果报告中有表格，阅读 `Table` 章节，重点关注列宽、内边距、表头、分页和样式优先级。
4. 如果需要中文、阿拉伯文或混合字体，阅读“字体注册”和“文字排版限制”。
5. 最后阅读“通用链式样式方法”，了解尺寸、边距、圆角、图层和布局方法怎样组合。

## 常用示例

```python
from smart_report import Canvas, Frame, Table, document

doc = document()
page = doc.page("A4")

hero = Canvas().height(120).background("#dbeafe")
hero.add_text("季度报告").absolute(24, 24).font_size(24).color("#1e3a8a")
page.add(hero)

body = Frame().padding(24)
body.add_text("核心指标").font_size(16).margin(bottom=12)
body.add_table([
    ["指标", "结果"],
    ["收入", "+18%"],
]).header(background="#1d4ed8", color="#ffffff")
page.add(body)

doc.save("report.pdf")
```


## 发布与工程化流程

发布或打 tag 前按以下顺序检查：

1. 用 `GIT_MASTER=1 git status --short` 和 `GIT_MASTER=1 git diff --stat` 确认工作区，只处理本次发布需要的文件。
2. 运行回归和类型检查：

```bash
.venv/bin/python -m unittest tests.test_table_v2
.venv/bin/python -m unittest tests.test_document_structure
npx --yes pyright
```

3. 确认 `.venv` 内有构建工具：

```bash
.venv/bin/python -m build --version
.venv/bin/python -m pip show build wheel setuptools
```

缺失时只安装到项目虚拟环境：

```bash
.venv/bin/python -m pip install build wheel setuptools
```

4. 本地构建 wheel 和 sdist：

```bash
.venv/bin/python -m build
```

5. 安装 wheel 做冒烟测试，并从项目目录外导入，确认使用的是已安装 wheel 而不是本地源码。
6. 如果 README 链接了文档、changelog 或示例，检查 sdist 是否包含 `CHANGELOG.md`、`docs/` 和 `MANIFEST.in` 声明的示例资源。
7. 验证和复审通过后，只提交源码、文档和打包元数据；不要提交 `dist/`、`build/` 等生成物。
8. 为通过验证的提交创建新 tag。不要移动已有发布 tag，除非明确要修正发布历史。
9. 推送分支和新 tag，然后创建 GitHub Release。在本项目中，提交、打 tag、push、创建 GitHub Release 是验证与复审通过后的固定收尾流程。
10. PyPI 发布是独立步骤，只有用户明确要求时才执行。

## 兼容性说明

后续改动应保持向后兼容；破坏性 API 调整应留到下一个主版本。版本新增内容统一记录在根目录 [CHANGELOG.md](../../CHANGELOG.md)，API 文档只描述当前公开 API 的行为。
