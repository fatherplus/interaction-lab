# 贡献指南

感谢你愿意改进 Interaction Lab。这个项目的核心约束很少，但都很硬。

## 三条硬约束

1. **零第三方依赖**。Python 只用标准库，前端不用框架、不用 CDN、不引外部字体。新增依赖的 PR 需要先开 issue 说明为什么标准库/原生 API 做不到。
2. **数据同源**。标本的分类、Token、状态机、DO NOT 只写在 `data/patterns.json` 里；界面、API、`.md` 规范都由它派生。不要在两处手写同一份参数。
3. **桌面优先**。只按 Mac / 桌面浏览器验收，不加移动端断点。见 `AGENTS.md`。

## 本地开发

```bash
python3 build.py                 # 构建 dist/
python3 server/app.py            # http://127.0.0.1:8900
python3 -m unittest discover -s tests -v
```

改完 `src/` 或 `data/` 后重跑 `build.py`；`dist/` 不入库。想边改边看，改完重新构建并刷新即可（`?v=` 会随 `VERSION` 变化）。

## 新增或修改一个标本

1. 在 `src/pages/` 对应世界里实现交互：单文件、无外部请求、真实控件、`prefers-reduced-motion` 有降级。
2. 在 `data/patterns.json` 的 `patterns[]` 新增条目，字段见 `data/schema.md`。`id` 是永久 slug，一旦发布不要改名（URL、埋点、`.md` 路径都依赖它）。
3. 在 `scripts/extract_specimens.py` 的 `SPECIMEN_MAP` 里登记抽取源。
4. 跑构建与测试；确认 `dist/specimens/<id>.html` 独立可运行。
5. 如果新增了分类，同步更新 `categories[]` 与 README 的特性列表。

## 代码风格

- Python：跟现有文件一致——`from __future__ import annotations`、类型注解、标准库优先。
- JS/CSS：原生语法；只动 `transform` / `opacity` / 颜色；显式列出过渡属性，不用 `transition: all`。
- 文案：中文为主，术语保留英文原词。
- 提交信息：`type(scope): summary`，例如 `fix(server): clamp telemetry payload size`。

## 提交 PR 前

```bash
python3 build.py
python3 -m unittest discover -s tests -v
```

构建自带安全检查：产物中出现内网地址、个人绝对路径或密钥会直接失败。请不要绕过它，而是修掉来源。

## 报告问题

开 issue 时附上：复现步骤、浏览器与系统版本、期望与实际。视觉问题请附截图；涉及标本参数的问题请指出 `pattern id`。

## 署名与出处

如果你认为某个标本的出处标注不准确，或希望调整署名方式，请直接开 issue，我们会优先处理。
