# `data/patterns.json` Schema (v2.0.0)

Single Source of Truth driving the Desktop Workbench UI, `/llms.txt`, `/api/patterns.json`, and `/patterns/<id>.md`.

## Top-Level Object
- `version`: Semver string (`"2.0.0"`)
- `title`, `subtitle`, `description`: Public workbench metadata
- `categories[]`: 6 mutually exclusive action-first categories:
  - `id`, `num`, `name_cn`, `name_en`, `summary`
- `patterns[]`: 48 structured interaction pattern specs

## Pattern Entry Fields
| Field | Type | Purpose |
| :--- | :--- | :--- |
| `id` | `string` | Permanent semantic kebab-case slug (URL, `.md` path, telemetry key) |
| `category` | `string` | One of the 6 category IDs |
| `name_cn` / `name_en` | `string` | Standard Chinese & English interaction terminology |
| `demo` | `{ kind, variant }` | Live specimen renderer binding |
| `default_surface` | `paper\|dark\|dots\|vivid` | Optimal default optical backdrop for the specimen |
| `drive[]` | `string[]` | Orthogonal trigger facets (`press`, `click`, `drag`, `hover`, `pointer`, `scroll`, `time`, `state`) |
| `tech[]` | `string[]` | Core web primitives (`css-transition`, `css-keyframes`, `css-3d`, `pointer-events`, `backdrop-filter`, `svg-stroke`, `raf`, `io`) |
| `scope` | `atom\|pattern\|layout` | Component granularity |
| `symptoms[]` | `string[]` | Colloquial Chinese & English queries for `⌘K` reverse lookup |
| `essence` | `string` | One-sentence physical/UX law of the interaction |
| `when_to_use[]` / `when_not_to_use[]` | `string[]` | Practical design applicability boundaries |
| `tokens` | `Record<string,string>` | Exact CSS custom property contract |
| `knobs[]` | `Array<{key,label,unit,min,max,step,default}>` | Live tunable parameters bound to stage & code/prompt output |
| `easing_curve` | `{ bezier: [n,n,n,n], label }` | Cubic-bezier parameters rendered in SVG motion graph |
| `state_machine[]` | `Array<{state,trigger,visual,timing}>` | Complete state transition contract |
| `do_not[]` | `string[]` | Negative constraints preventing low-IQ LLM failure modes |
| `self_check[]` | `string[]` | Verifiable QA checklist for AI output |
| `code_snippet` | `string` | Minimal zero-dependency HTML+CSS+JS reference skeleton |
