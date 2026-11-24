#!/usr/bin/env python3
"""Interaction Lab v3 — Data-Driven Static, High-Craft Specimens & AI-Native Builder.

Reads:
  data/patterns.json           Single Source of Truth (48 patterns, 6 categories)
  src/pages/ep26..31.html      High-craft source specimens
  src/pages/anim-lab/          16 high-craft animation specimens
  src/js/specimen-bridge.js    WAAPI slow-mo, theme sync, reduced-motion, telemetry bridge
  src/index.html               Obsidian Optical Lab Desktop Workbench HTML shell
  src/css/*.css                Workbench stylesheets
  src/js/*.js                  AI Engine, Telemetry SDK, App Controller

Outputs (dist/):
  dist/index.html              Cache-busted desktop workbench
  dist/css/*.css
  dist/js/*.js
  dist/specimens/<id>.html     48 standalone high-craft specimens
  dist/api/patterns.json       Full machine-readable catalog
  dist/llms.txt                Standard llms.txt index for AI coding agents
  dist/patterns/<id>.md        48 standalone AI-Native pattern specs (dumb-model-proof)
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from extract_specimens import extract_all  # noqa: E402

SRC = ROOT / "src"
DATA = ROOT / "data" / "patterns.json"
OUT = ROOT / "dist"
VERSION = "20261124v5"

FORBIDDEN_PATTERNS = [
    # Internal / private network addresses must never ship to a public site.
    (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "private LAN IPv4"),
    (r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "private LAN IPv4"),
    # Personal absolute paths leak machine/user names.
    (r"/Users/[A-Za-z0-9._-]+/", "absolute macOS home path"),
    (r"[A-Za-z]:\\\\Users\\\\", "absolute Windows home path"),
    # Credentials and keys.
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"sk-[A-Za-z0-9_-]{20,}", "API secret key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
]



def render_pattern_md(p: dict, cat_map: dict) -> str:
    cat = cat_map.get(p["category"], {})
    tokens_lines = "\n".join(f"  {k}: {v};" for k, v in p.get("tokens", {}).items())
    sm_lines = "\n".join(
        f"| `{s['state']}` | {s['trigger']} | {s['visual']} | `{s['timing']}` |"
        for s in p.get("state_machine", [])
    )
    do_not_lines = "\n".join(f"- **DO NOT:** {d}" for d in p.get("do_not", []))
    check_lines = "\n".join(f"- [ ] {c}" for c in p.get("self_check", []))
    use_lines = "\n".join(f"- {u}" for u in p.get("when_to_use", []))
    not_use_lines = "\n".join(f"- {u}" for u in p.get("when_not_to_use", []))
    curve = p.get("easing_curve") or {}
    bez = ", ".join(str(x) for x in curve.get("bezier", [0.16, 1, 0.3, 1]))

    return f"""# {p['name_cn']} ({p['name_en']})

- **Pattern ID:** `{p['id']}`
- **Category:** {cat.get('name_cn', p['category'])} (`{p['category']}`)
- **Scope:** `{p['scope']}` | **Drive:** {', '.join(p.get('drive', []))} | **Tech:** {', '.join(p.get('tech', []))}
- **Motion Curve:** `cubic-bezier({bez})` ({curve.get('label', '')})
- **Essence:** {p['essence']}

## 1. Exact Token Contract (Do Not Substitute with Generic `0.5s ease`)

```css
:root {{
{tokens_lines}
}}
```

## 2. Explicit State Machine

| State | Trigger | Visual Behavior | Timing |
| :--- | :--- | :--- | :--- |
{sm_lines}

## 3. Anti-Pattern Guardrails (Mandatory)

{do_not_lines}

## 4. Minimal Runnable Reference Skeleton (Zero Dependencies)

```html
{p['code_snippet']}
```

## 5. Self-Check Before Outputting Code

{check_lines}

## 6. Usage Guidance

**Use when:**
{use_lines}

**Avoid when:**
{not_use_lines}
"""


def render_llms_txt(catalog: dict) -> str:
    cats = catalog["categories"]
    patterns = catalog["patterns"]
    lines = [
        "# Interaction Lab — AI-Native Open Interaction Workbench",
        "",
        "> 48 live, tunable UI/UX interaction patterns with exact motion tokens, explicit state machines,",
        "> anti-pattern guardrails (DO NOTs), and zero-dependency reference skeletons designed so even",
        "> lightweight / low-cost LLMs produce crisp, tactile UI interactions.",
        "",
        "## Machine-Readable Endpoints",
        "- Full JSON Catalog: `/api/patterns.json`",
        "- Per-Pattern Spec: `/patterns/{id}.md`",
        "- Live Standalone Specimen: `/specimens/{id}.html`",
        "- Interactive Workbench: `/#/pattern/{id}`",
        "",
        "## Global Motion Rules (Always Apply)",
        "1. Animate only GPU-composited properties (`transform`, `opacity`, `stroke-dashoffset`, colors). Never animate `width`, `height`, `top`, `left`, or `margin`.",
        "2. Always apply `font-variant-numeric: tabular-nums` to counters, timers, metrics, and prices.",
        "3. Always implement `@media (prefers-reduced-motion: reduce)` fallbacks.",
        "4. Never replace specified `cubic-bezier(...)` curves with generic `0.5s ease` or `linear` (except continuous marquees/spinners).",
        "",
    ]

    for c in cats:
        lines.append(f"## {c['num']}. {c['name_cn']} ({c['name_en']})")
        lines.append(f"> {c['summary']}")
        lines.append("")
        for p in [x for x in patterns if x["category"] == c["id"]]:
            syms = " / ".join(p.get("symptoms", [])[:4])
            lines.append(
                f"- [{p['name_cn']} ({p['name_en']})](/patterns/{p['id']}.md): {p['essence']} "
                f"(Triggers: {syms})"
            )
        lines.append("")
    return "\n".join(lines)


def build() -> None:
    catalog = json.loads(DATA.read_text(encoding="utf-8"))
    cats = catalog["categories"]
    patterns = catalog["patterns"]
    cat_map = {c["id"]: c for c in cats}
    patterns_by_id = {p["id"]: p for p in patterns}

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "css").mkdir(parents=True)
    (OUT / "js").mkdir(parents=True)
    (OUT / "api").mkdir(parents=True)
    (OUT / "patterns").mkdir(parents=True)
    (OUT / "specimens").mkdir(parents=True)
    (OUT / "cli").mkdir(parents=True)

    # 1. Copy CSS, JS, CLI & Skill
    for f in (SRC / "css").glob("*.css"):
        shutil.copy2(f, OUT / "css" / f.name)
    for f in (SRC / "js").glob("*.js"):
        shutil.copy2(f, OUT / "js" / f.name)
    shutil.copy2(ROOT / "cli" / "ilab", OUT / "cli" / "ilab")
    shutil.copy2(ROOT / "skill" / "SKILL.md", OUT / "SKILL.md")

    # 2. Build index.html with cache-busting query strings
    html = (SRC / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'(href="css/[^"]+\.css)"', rf'\1?v={VERSION}"', html)
    html = re.sub(r'(src="js/[^"]+\.js)"', rf'\1?v={VERSION}"', html)
    (OUT / "index.html").write_text(html, encoding="utf-8")

    # 3. Extract 48 high-craft standalone specimens
    spec_count = extract_all(OUT / "specimens", patterns_by_id)

    # 4. Emit /api/patterns.json
    (OUT / "api" / "patterns.json").write_text(
        json.dumps(catalog, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    # 5. Emit /llms.txt
    (OUT / "llms.txt").write_text(render_llms_txt(catalog), encoding="utf-8")

    # 5b. Emit /robots.txt — the whole point is to be readable by humans AND agents
    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\n"
        "# Machine-readable index for AI coding agents:\n"
        "# /llms.txt  /api/patterns.json  /patterns/{id}.md  /SKILL.md\n",
        encoding="utf-8",
    )

    # 6. Emit /patterns/<slug>.md for all 48 patterns
    for p in patterns:
        md = render_pattern_md(p, cat_map)
        (OUT / "patterns" / f"{p['id']}.md").write_text(md, encoding="utf-8")

    # 7. Public-release safety gate: no internal addresses, personal paths or keys
    leaks = []
    for path in OUT.rglob("*"):
        if path.is_file():
            content = path.read_text(encoding="utf-8", errors="ignore")
            for pattern, label in FORBIDDEN_PATTERNS:
                if re.search(pattern, content):
                    leaks.append((str(path.relative_to(OUT)), label))
    if leaks:
        raise RuntimeError(f"BUILD FAILED — forbidden content detected: {leaks[:10]}")

    print(f"Built Interaction Lab v3 -> {OUT}")
    print(f"  Categories : {len(cats)}")
    print(f"  Patterns   : {len(patterns)} (index + api/patterns.json + llms.txt + {len(patterns)} .md specs)")
    print(f"  Specimens  : {spec_count} standalone high-craft HTML pages")
    print("  Safety check: PASS (0 leaks)")


if __name__ == "__main__":
    build()
