# 架构

零第三方依赖的静态站 + 一个小型标准库 HTTP 服务。没有数据库服务、没有构建链、没有前端框架。

## 数据流

```
data/patterns.json  ──┐
src/index.html        │
src/css src/js        ├─►  build.py  ─►  dist/  ─►  server/app.py  ─►  浏览器 / ilab CLI / AI Agent
src/pages/ep*.html    │      │                        │
src/pages/anim-lab    │      └─ 安全门禁（内网地址/路径/密钥）  └─ SQLite (WAL) 埋点
cli/ilab  skill/      ┘
```

`data/patterns.json` 是唯一真相。画廊、`/api/patterns.json`、`/llms.txt`、48 份 `/patterns/{id}.md` 与 48 个 `/specimens/{id}.html` 全部由它派生；改分类或参数只需要改这一个文件。

## 构建（`build.py`）

1. 清空并重建 `dist/` 目录结构。
2. 复制 CSS / JS / `cli/ilab` / `skill/SKILL.md`。
3. 渲染 `index.html`，给 `css/*` `js/*` 加 `?v=<VERSION>` 缓存击穿参数。
4. `scripts/extract_specimens.py` 从 `src/pages/` 抽取 48 个独立标本：按 `SPECIMEN_MAP` 定位容器，剥离外部依赖、注入共享的 `specimen-bridge.js`（慢放、主题同步、reduced-motion、埋点桥），并输出单文件 HTML。
5. 生成 `/api/patterns.json`、`/llms.txt`、`/robots.txt`。
6. 为每个标本生成 `/patterns/{id}.md`（Token 契约、状态机表、DO NOT、代码骨架、自检清单）。
7. **安全门禁**：扫描产物中的内网 IPv4、个人绝对路径、GitHub/API/AWS 密钥与私钥块，命中即让构建失败。

## 请求路径（`server/app.py`）

`ThreadingHTTPServer` + `SimpleHTTPRequestHandler` 托管 `dist/`，并在其前面拦截：

| 路径 | 处理 |
| :--- | :--- |
| `/api/categories` | 分类 + 各类标本数；记一次 Agent 读取 |
| `/api/search` | 症状词 / 分类 / 驱动过滤；无结果也记录（用于缺口分析） |
| `/api/patterns.json` | 直出构建产物；非同源请求计为 Agent 读取 |
| `/patterns/*.md`、`/specimens/*.html`、`/llms.txt`、`/SKILL.md` | 计为 Agent 读取后走静态托管 |
| `/cli/ilab` | 读取脚本，把 `@@DEFAULT_URL@@` 替换为当前 `Host`/`X-Forwarded-Proto` 推导的源 |
| `/api/t` | 浏览器批量埋点（≤25 事件、≤32KB、滑动窗口限流） |
| `/api/health` | 聚合状态：事件数、会话数、库体积 |
| 其他 | `dist/` 静态文件 |

限流：内存滑动窗口，默认 150 次/分钟/访客哈希，超限返回 429（`/api/t` 返回空 202 的关闭态除外）。

## 埋点模型（`server/db.py`）

- `events`：每条行为一行。`source` 区分 `web`（浏览器）与 `server_ai`（Agent/CLI 读取）。
- `sessions`：按 `session_id` 聚合的会话汇总（浏览、交互、复制次数）。
- 视图：`v_pattern_leaderboard`（标本热度）、`v_daily_overview`（日汇总）、`v_search_gaps`（零结果检索词）。
- 访客标识：`HMAC-SHA256(salt, ip|ua)[:24]`。IP 不落库；salt 首次运行生成于数据库旁或由 `IL_TELEMETRY_SALT` 提供。
- 浏览器端 SDK（`src/js/telemetry.js`）批量攒 20 条或 3.2s 后 `sendBeacon`；服务端只接受白名单事件类型。

## 前端

- `src/js/app.js`：路由（`#/pattern/{id}`）、画廊渲染、hero 展台、lightbox、⌘K 搜索、主题切换。
- `src/js/ai-engine.js`：把标本数据插值成「可交给模型」的 Prompt / 代码（支持 vanilla、React、Vue 输出）。
- `src/js/telemetry.js`：埋点 SDK。
- `src/js/specimen-bridge.js`：注入到每个标本页，负责慢放开关、主题同步、reduced-motion 与交互上报。
- 标本页 `src/pages/` 保持各自的内部世界，仅共享 `src/chrome.css` 顶栏（构建时注入）。

## 设计取舍

- **为什么不用前端框架**：画廊的核心成本在标本本身，框架只会增加构建链与依赖。原生 DOM + 一格 `patterns.json` 足够。
- **为什么用 SQLite**：单文件、可备份、可 `sqlite3` 直接查；WAL 下并发读不阻塞写入。
- **为什么规范是 `.md` 而不是 JSON**：Agent 直接读 Markdown 的 Token 表与状态机比解析 JSON 更稳，也方便人看。
