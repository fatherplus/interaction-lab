# Design System — Interaction Lab 桌面工作台

> 本文描述**当前已交付**的画廊界面（`src/index.html` + `src/css/workbench.css`）。
> 索引页的方向合同见 `docs/DESIGN-CONTRACT.md`，产品定义见 `docs/PRODUCT.md`。
> 桌面端验收（`AGENTS.md`）：不加移动端断点。

## 1. 两套世界，一套语法

| | 暗室（默认） | 暖白 |
| :--- | :--- | :--- |
| 定位 | 光学实验台，色谱沉底，标本本身发光 | 纸面工作室，标本成为纸上的实物 |
| 触发 | `:root` | `html[data-theme="light"]` |
| 强调色 | 冰蓝 `#38bdf8` | 深蓝 `#0066d6` |

两套主题共用同一套布局、间距、圆角与动效曲线，只替换颜色变量。主题选择持久化在 `localStorage`，标本页通过 `specimen-bridge.js` 同步。

## 2. 颜色 Token

### 暗室（默认）

| Token | 值 | 用途 |
| :--- | :--- | :--- |
| `--bg` | `#05070c` | 页面底色 |
| `--surface` | `rgba(13,17,26,.78)` | 顶栏、浮层 |
| `--surface-solid` | `#0d111a` | 卡片实体面 |
| `--surface-2` | `rgba(255,255,255,.045)` | Chip、次级按钮 |
| `--surface-hover` | `rgba(255,255,255,.08)` | Hover 态 |
| `--ink` | `#f4f6fb` | 主文字 |
| `--ink2` | `#9ba5b7` | 次级文字 |
| `--ink3` | `#636e82` | 标签、测量读数 |
| `--line` | `rgba(255,255,255,.095)` | 1px 描边 |
| `--line-soft` | `rgba(255,255,255,.055)` | 弱分隔 |
| `--accent` | `#38bdf8` | 唯一强调色 |
| `--accent-soft` | `rgba(56,189,248,.14)` | 强调底色 |
| `--accent-border` | `rgba(56,189,248,.38)` | 强调描边 |
| `--accent-glow` | `rgba(56,189,248,.28)` | 光晕 |
| `--code-bg` | `#070a10` | 命令块 |
| `--code-ink` | `#e2e8f0` | 命令文字 |

### 暖白

`--bg: #f4f1ea`、`--surface-solid: #fffdf8`、`--ink: #1b1812`、`--ink2: #575041`、`--ink3: #837b6c`、`--accent: #0066d6`；阴影改用暖色 `rgba(34,29,21,·)`，标本舞台底色改为 `#eae5da`。

**The One Lamp Rule.** 界面色只有冰蓝一个强调色，且只用于可交互点：激活态、焦点环、CLI chip、主按钮。饱和色属于标本内容，不属于界面框架。

## 3. 字体

- 正文 / 标题：`-apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif`。
- 读数 / 命令：`--font-mono`（SF Mono → ui-monospace → Menlo）。
- 所有计数、价格、参数使用 `font-variant-numeric: tabular-nums`。
- 不内联 Web 字体，零外部请求；`assets/` 内的 Bricolage Grotesque 供自托管变体按需使用，默认构建不引用。

## 4. 布局

```
┌ topbar 56px · sticky · surface + blur ─────────────────┐
│ brand │ 分类导航 │              ⌘K 搜索 │ 接入 AI │ 主题 │
├ main-shell · max-width 1400px ─────────────────────────┤
│ hero-showcase      1fr 舞台(470px) │ 316px 侧栏 pod    │
├ section-head · 标题 + 计数 + SKILL/llms/api 链接 ───────┤
│ gallery-grid · 2 列 · gap 22px                         │
│   pcard(18px) → pcard-stage 344px → 标题/CLI/essence    │
└────────────────────────────────────────────────────────┘
```

- 顶栏 `56px`、内宽 `1440px`；主区 `1400px`。
- Hero 侧栏是交互说明面板：标题、英文名、一句话本质、可复制的 `ilab get` 命令、主/次操作。
- 画廊固定两列；每张卡片的舞台内嵌独立同源 iframe，按容器比例缩放，保证 1:1 可操作。
- 浮层全部居中：`lightbox-dialog`（1:1 放大）、`ai-dialog`（CLI/Skill 接入）、`cmd-dialog`（⌘K 搜索）。

## 5. 层级与动效

- 阴影：`--shadow-sm`（卡片静止）、`--shadow-md`（卡片 hover）、`--shadow-modal`（浮层）。
- 卡片 hover 有一层跟随指针的径向高光（`--mx/--my` 驱动 `::before`），只在桌面 hover 生效。
- 统一曲线 `--ease: cubic-bezier(.16,1,.3,1)`；只动 `transform` / `opacity` / 颜色 / `stroke-dashoffset`。
- 浮层进出 160–240ms；标本内部动效由各标本自己的 token 决定（见 `/patterns/{id}.md`）。
- 全部 `prefers-reduced-motion: reduce` 下降级为无位移、无动画，状态仍完整可达。

## 6. 组件

### Topbar
毛玻璃 sticky 条。品牌球 + 双行字标；分类导航由 `patterns.json` 渲染；右侧三件套：⌘K 搜索触发器、AI 接入按钮（带呼吸点）、主题切换。

### Hero Showcase
「旗舰展台」：顶部一行 kicker + 5 个旗舰交互切换 tab；左侧 470px 舞台内嵌 `iframe`；右侧 pod 展示当前旗舰的名称与本质，并提供「复制 AI 蓝图规范 / 放大 1:1 / 反转明暗」。

### Pattern Card
18px 外框（1px `--line` 描边）：344px 标本舞台 + 分类 chip + 标题/英文 slug + 可复制 CLI chip + 两行 essence。点击舞台打开 1:1 lightbox；点击 CLI chip 复制命令。

### Lightbox
无框浮层：标题、英文名、CLI chip、反转明暗、复制规范、`.md` 原文外链、关闭。舞台按视口等比缩放，保证标本以 1:1 尺寸渲染。

### AI Setup Dialog
三步接入：装 CLI、装 Skill、四条核心命令。每段命令都可一键复制，站点地址由服务端在下载时注入，不在前端硬编码。

### Command Palette（⌘K / Ctrl+K）
症状词检索：支持中文口语（「按钮没反馈」）与英文术语。↑↓ 选择、Enter 放大、Esc 关闭。

### Toast
`role="status" aria-live="polite"`，仅承载「已复制」类轻反馈。

## 7. 可访问性

- 全部可交互元素用真实 `<button>` / `<a>`，不用 div 模拟。
- `:focus-visible` 统一 2px 强调色描边，不用 `outline: none`。
- 浮层：打开时聚焦首个可操作元素，`Esc` 关闭，关闭后焦点返回触发元素；背景 `aria-hidden`。
- 图标一律内联 SVG stroke 图标，`aria-hidden="true"`；图标按钮必须有 `aria-label`。
- 对比度：正文与次级文字在暗室/暖白两套下均 ≥ 4.5:1。

## 8. 桌面端规则

**The Desktop-Only Rule.** 画廊不提供手机/平板布局，不加宽度断点、不加底部抽屉。`chrome.css` 中标本页自己的窄屏规则属于那六个世界，不要改动。

## 9. Do / Don't

**Do**
- 用 token，不写魔法色值；新颜色先加变量。
- 强调色只落在可交互点和当前状态上。
- 新浮层复用 `modal-scrim` + 现有阴影与 160–240ms 节奏。
- 标本舞台内保持零外部请求；新增依赖前先问「标准库/原生 API 能不能做」。

**Don't**
- 不要为单个组件引入第二强调色、渐变文字、霓虹泛光。
- 不要在卡片里嵌套「卡片里的卡片」——舞台是凹面，不是新面板。
- 不要用 `transition: all`；显式列出属性。
- 不要为移动端改布局（见 `AGENTS.md`）。
