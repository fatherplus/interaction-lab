#!/usr/bin/env python3
"""Extracts 48 standalone, 100%-rendered high-craft specimen HTML files
from src/pages/ep26..31.html and src/pages/anim-lab/index.html.
"""
from __future__ import annotations

import pathlib
import re
from typing import Dict, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ROOT / "src" / "pages"
BRIDGE_PATH = ROOT / "src" / "js" / "specimen-bridge.js"

# Map every pattern ID -> (source_kind, selector_or_variant)
SPECIMEN_MAP: Dict[str, Tuple[str, str]] = {
    # EP26 (6)
    "sidebar-pill-nav": ("ep26", "1"),
    "grouped-section-nav": ("ep26", "2"),
    "top-capsule-bar": ("ep26", "3"),
    "compact-icon-rail": ("ep26", "4"),
    "brand-surface-nav": ("ep26", "5"),
    "outlined-group-tabs": ("ep26", "6"),
    # EP27 (6)
    "single-light-power-switch": ("ep27", "power"),
    "rotary-climate-dial": ("ep27", "climate"),
    "recessed-volume-slider": ("ep27", "audio"),
    "sculpted-segment-control": ("ep27", "transfer"),
    "tactile-calendar-matrix": ("ep27", "booking"),
    "tactile-quantity-stepper": ("ep27", "quantity"),
    # EP28 (8)
    "send-flight-receipt": ("ep28", "1"),
    "origin-growth-menu": ("ep28", "2"),
    "smooth-accordion-reveal": ("ep28", "3"),
    "stroke-check-select": ("ep28", "4"),
    "vertical-roller-stepper": ("ep28", "5"),
    "card-3d-flip-receipt": ("ep28", "6"),
    "tactile-chip-filter": ("ep28", "7"),
    "billing-cycle-price-roll": ("ep28", "8"),
    # EP29 (6)
    "dark-protagonist-grid": ("ep29", "1"),
    "frosted-overlay-dashboard": ("ep29", "2"),
    "editorial-image-hero": ("ep29", "3"),
    "light-asymmetric-columns": ("ep29", "4"),
    "dot-matrix-whitespace": ("ep29", "5"),
    "capsule-metric-bars": ("ep29", "6"),
    # EP30 (4)
    "glass-drag-bookshelf": ("ep30", "1"),
    "glass-drag-photo-tray": ("ep30", "2"),
    "glass-drag-task-sort": ("ep30", "3"),
    "glass-drag-photo-stack": ("ep30", "4"),
    # EP31 (2)
    "fan-focus-yield": ("ep31", "ltc"),
    "coverflow-depth-stage": ("ep31", "atl"),
    # ANIM-LAB (16)
    "conic-border-beam": ("anim", "border-beam"),
    "radial-cursor-spotlight": ("anim", "spotlight"),
    "perspective-tilt-glare": ("anim", "tilt"),
    "scroll-synced-story": ("anim", "scroll-storytelling"),
    "cipher-scramble-decode": ("anim", "scramble-text"),
    "multi-layer-parallax": ("anim", "parallax"),
    "magnetic-pull-cta": ("anim", "magnetic"),
    "stream-typewriter-cursor": ("anim", "typewriter"),
    "infinite-pause-marquee": ("anim", "marquee"),
    "diagonal-skeleton-shimmer": ("anim", "shimmer"),
    "easeout-count-up": ("anim", "count-up"),
    "viewport-scroll-reveal": ("anim", "scroll-reveal"),
    "spring-overshoot-compare": ("anim", "spring"),
    "staggered-list-cascade": ("anim", "stagger"),
    "hover-elevation-lift": ("anim", "hover-lift"),
    "weight-easing-comparison": ("anim", "easing"),
}

BASE_SHELL_CSS = """
*, *::before, *::after { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: transparent;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
}
html[data-reduced="true"] *,
html[data-reduced="true"] *::before,
html[data-reduced="true"] *::after {
  animation-duration: 0.001ms !important;
  animation-iteration-count: 1 !important;
  transition-duration: 0.001ms !important;
}
"""


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _strip_js_comments(js: str) -> str:
    # Remove block comments safely; only remove single-line comments that start a line
    # or follow whitespace so 'http://www.w3.org/2000/svg' is NEVER corrupted!
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js = re.sub(r"(?m)(?:^|[ \t])//[^\n]*", "", js)
    return js


def _strip_html_meta(html: str) -> str:
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    html = re.sub(r'\s+data-ep="[^"]*"', "", html)
    html = re.sub(r'\s+data-title="[^"]*"', "", html)
    return html


def _extract_ep_parts(filename: str) -> Tuple[str, str, str]:
    raw = (PAGES / filename).read_text(encoding="utf-8")
    styles = re.findall(r"<style[^>]*>(.*?)</style>", raw, flags=re.S)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", raw, flags=re.S)
    assert len(styles) >= 2 and len(scripts) >= 2, f"Unexpected blocks in {filename}"
    specimen_css = _strip_css_comments(styles[1])
    specimen_js = _strip_js_comments(scripts[1])

    m = re.search(r'(<section class="demo\b.*?</section>)\s*(?:<aside class="note"|</div>)', raw, flags=re.S)
    assert m, f"Could not locate section.demo in {filename}"
    section_html = re.sub(r'<p class="principle">.*?</p>', "", m.group(1), flags=re.S)
    section_html = _strip_html_meta(section_html)
    # Remove data-slug on ep sections only (anim-lab needs data-slug on fxcard)
    section_html = re.sub(r'\s+data-slug="[^"]*"', "", section_html)
    return specimen_css, section_html, specimen_js


def _wrap_page(pattern_id: str, title: str, css: str, body_html: str, js: str, bridge_js: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{BASE_SHELL_CSS}
{css}
</style>
</head>
<body>
{body_html}
<script>
window.__IL_SPECIMEN_ID__ = "{pattern_id}";
{bridge_js}
</script>
<script>
{js}
</script>
</body>
</html>
"""


def _build_ep26(pattern_id: str, idx: str, title: str, bridge_js: str) -> str:
    css, html, js = _extract_ep_parts("ep26.html")
    zero_idx = int(idx) - 1
    # Replace initial show(0) so target tab is activated natively by ep26 JS
    js = re.sub(r"\bshow\s*\(\s*0\s*\)\s*;", f"show({zero_idx});", js)
    override_css = f"""
.ep26 {{ padding: 0 !important; margin: 0 !important; width: 100%; height: 100%; border-radius: 0 !important; border: 0 !important; display: flex; flex-direction: column; }}
.ep26 .stage {{ height: 100% !important; flex: 1; border-radius: 0 !important; border: 0 !important; padding: 0 !important; }}
.ep26 .tabs {{ display: none !important; }}
.ep26 .views {{ height: 100% !important; position: relative; }}
.ep26 .view {{ display: none !important; }}
.ep26 #ep26-p{idx} {{
  display: flex !important;
  opacity: 1 !important;
  visibility: visible !important;
  transform: none !important;
  pointer-events: auto !important;
  position: relative !important;
  inset: auto !important;
  width: 100% !important;
  height: 100% !important;
  border-radius: 0 !important;
}}
"""
    return _wrap_page(pattern_id, title, css + override_css, html, js, bridge_js)


def _build_ep27(pattern_id: str, cell_name: str, title: str, bridge_js: str) -> str:
    css, html, js = _extract_ep_parts("ep27.html")
    # Fix dark mode: convert @media (prefers-color-scheme: dark) to html[data-theme="dark"] .ep27
    m = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*?)\n\}", css, flags=re.S)
    if m:
        dark_inner = re.sub(r"(^|\n)\s*\.ep27", r'\1html[data-theme="dark"] .ep27', m.group(1))
        css = css[:m.start()] + dark_inner + css[m.end():]

    override_css = f"""
.ep27 {{ padding: 14px !important; margin: 0 !important; width: 100%; height: 100%; border-radius: 0 !important; border: 0 !important; display: grid; place-items: center; }}
.ep27 .stage {{ width: 100% !important; height: 100% !important; grid-template-columns: 1fr !important; padding: 0 !important; }}
.ep27 .cell {{ display: none !important; width: 100%; height: 100%; min-height: 0 !important; }}
.ep27 .cell[data-c="{cell_name}"] {{ display: flex !important; }}
"""
    return _wrap_page(pattern_id, title, css + override_css, html, js, bridge_js)


def _build_ep28(pattern_id: str, idx: str, title: str, bridge_js: str) -> str:
    css, html, js = _extract_ep_parts("ep28.html")
    zero_idx = int(idx) - 1
    css = css.replace('.ep28[data-theme="dark"]', 'html[data-theme="dark"] .ep28, .ep28[data-theme="dark"]')
    # Replace initial select(0, false) with target panel index!
    js = re.sub(r"\bselect\s*\(\s*0\s*,\s*false\s*\)\s*;", f"select({zero_idx}, false);", js)
    override_css = f"""
.ep28 {{ padding: 0 !important; margin: 0 !important; width: 100%; height: 100%; border-radius: 0 !important; border: 0 !important; display: flex; flex-direction: column; }}
.ep28 .stage {{ height: 100% !important; flex: 1; padding: 18px !important; border-radius: 0 !important; border: 0 !important; }}
.ep28 .rail {{ display: none !important; }}
.ep28 .deck {{ height: 100% !important; position: relative; }}
.ep28 section.p {{ display: none !important; }}
.ep28 #ep28-p{idx} {{
  display: grid !important;
  place-items: center !important;
  opacity: 1 !important;
  visibility: visible !important;
  transform: none !important;
  pointer-events: auto !important;
  position: relative !important;
  inset: auto !important;
  width: 100% !important;
  height: 100% !important;
}}
"""
    post_js = """
(function() {
  requestAnimationFrame(function() { window.dispatchEvent(new Event('resize')); });
  setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 80);
})();
"""
    return _wrap_page(pattern_id, title, css + override_css, html, js + post_js, bridge_js)


def _build_ep29(pattern_id: str, idx: str, title: str, bridge_js: str) -> str:
    css, html, js = _extract_ep_parts("ep29.html")
    zero_idx = int(idx) - 1
    # Replace initial show(0) with target variant index!
    js = re.sub(r"\bshow\s*\(\s*0\s*\)\s*;", f"show({zero_idx});", js)
    override_css = f"""
.ep29 {{ padding: 0 !important; margin: 0 !important; width: 100%; height: 100%; border-radius: 0 !important; border: 0 !important; }}
.ep29 .stage {{ max-width: none !important; width: 100% !important; height: 100% !important; border-radius: 0 !important; border: 0 !important; padding: 0 !important; }}
.ep29 .tabs, .ep29 .spec {{ display: none !important; }}
.ep29 .views {{ height: 100% !important; position: relative; }}
.ep29 .view {{ display: none !important; }}
.ep29 #ep29-p{idx} {{
  display: block !important;
  opacity: 1 !important;
  visibility: visible !important;
  transform: none !important;
  pointer-events: auto !important;
  position: relative !important;
  inset: auto !important;
  width: 100% !important;
  height: 100% !important;
  border-radius: 0 !important;
}}
"""
    return _wrap_page(pattern_id, title, css + override_css, html, js, bridge_js)


def _build_ep30(pattern_id: str, idx: str, title: str, bridge_js: str) -> str:
    css, html, js = _extract_ep_parts("ep30.html")
    # Put .is-on directly on #ep30-p{idx} BEFORE scripts measure clientWidth/clientHeight
    html = html.replace('class="panel is-on"', 'class="panel"')
    html = html.replace(f'class="panel" id="ep30-p{idx}"', f'class="panel is-on" id="ep30-p{idx}"')
    override_css = f"""
.ep30 {{ padding: 0 !important; margin: 0 !important; width: 100%; height: 100%; border-radius: 0 !important; border: 0 !important; }}
.ep30 .stage {{ max-width: none !important; width: 100% !important; height: 100% !important; border-radius: 0 !important; border: 0 !important; }}
.ep30 .tabs {{ display: none !important; }}
.ep30 .panels {{ height: 100% !important; }}
.ep30 .panel {{ display: none !important; }}
.ep30 #ep30-p{idx} {{
  display: flex !important;
  opacity: 1 !important;
  visibility: visible !important;
  width: 100% !important;
  height: 100% !important;
}}
"""
    post_js = """
(function() {
  requestAnimationFrame(function() { window.dispatchEvent(new Event('resize')); });
  setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 90);
})();
"""
    return _wrap_page(pattern_id, title, css + override_css, html, js + post_js, bridge_js)


def _build_ep31(pattern_id: str, which: str, title: str, bridge_js: str) -> str:
    css, html, js = _extract_ep_parts("ep31.html")
    hide_other = ".ep31 .panel.atl { display: none !important; }" if which == "ltc" else ".ep31 .panel.ltc { display: none !important; }"
    override_css = f"""
.ep31 {{ padding: 0 !important; margin: 0 !important; width: 100%; height: 100%; border-radius: 0 !important; border: 0 !important; }}
.ep31 .stage {{ height: 100% !important; border-radius: 0 !important; border: 0 !important; padding: 0 !important; }}
.ep31 .stage > .bar {{ display: none !important; }}
.ep31 .cols {{ grid-template-columns: 1fr !important; height: 100% !important; padding: 0 !important; gap: 0 !important; }}
.ep31 .panel {{ height: 100% !important; border-radius: 0 !important; }}
{hide_other}
"""
    post_js = """
(function() {
  requestAnimationFrame(function() { window.dispatchEvent(new Event('resize')); });
  setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 90);
})();
"""
    return _wrap_page(pattern_id, title, css + override_css, html, js + post_js, bridge_js)


def _build_anim(pattern_id: str, slug: str, title: str, bridge_js: str) -> str:
    raw = (PAGES / "anim-lab" / "index.html").read_text(encoding="utf-8")
    styles = re.findall(r"<style[^>]*>(.*?)</style>", raw, flags=re.S)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", raw, flags=re.S)
    assert len(styles) >= 3 and len(scripts) >= 3, "Unexpected anim-lab blocks"

    m = re.search(rf'(<article class="fxcard" data-slug="{re.escape(slug)}"[^>]*>.*?</article>)', raw, flags=re.S)
    assert m, f"Could not find fxcard for {slug}"
    card_html = m.group(1)

    part_a_slugs = {"border-beam", "spotlight", "tilt", "scroll-storytelling", "scramble-text", "parallax", "magnetic", "typewriter"}
    is_a = slug in part_a_slugs
    part_css = _strip_css_comments(styles[1] if is_a else styles[2])
    part_js = _strip_js_comments(scripts[1] if is_a else scripts[2])

    # Guard Part B's count-up block so scroll-reveal doesn't crash when cu is absent!
    if not is_a:
        part_js = part_js.replace(
            "const cu = root.querySelector('[data-slug=\"count-up\"]');",
            "const cu = root.querySelector('[data-slug=\"count-up\"]');\n  if (cu) {"
        )
        part_js = part_js.replace(
            "const scroller = root.querySelector('[data-rv-root]');",
            "  }\n  const scroller = root.querySelector('[data-rv-root]');"
        )
        part_js = part_js.replace(
            "window.__fxb = { runCount, resetCount, reduce };",
            "window.__fxb = { reduce };"
        )

    wrap_cls = "fxpart fxa" if is_a else "fxpart fxb"
    part_attr = 'data-part="a"' if is_a else 'data-part="b"'

    h3_idx = card_html.find("<h3>")
    clean_card = (card_html[:h3_idx].strip() + "</article>") if h3_idx > 0 else card_html

    body_html = (
        f'<section class="{wrap_cls}" {part_attr} style="width:100%;height:100%;margin:0;padding:0;">'
        f'<div class="fxgrid" style="display:block;width:100%;height:100%;margin:0;padding:0;">'
        f'{clean_card}</div></section>'
    )

    dark_adapt_css = """
html[data-theme="dark"] .fxa,
html[data-theme="dark"] .fxb {
  --bg: #0f131b;
  --surf: #151b26;
  --ink: #eef2f8;
  --mut: #94a0b5;
  --line: rgba(255,255,255,0.10);
  background: #0f131b !important;
}
html[data-theme="light"] .fxa,
html[data-theme="light"] .fxb {
  background: #f3efe6 !important;
}
.fxcard {
  width: 100% !important;
  height: 100% !important;
  border: 0 !important;
  border-radius: 0 !important;
  padding: 14px !important;
  margin: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.fxcard .stage {
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  border-radius: 14px !important;
}
"""
    return _wrap_page(pattern_id, title, part_css + dark_adapt_css, body_html, part_js, bridge_js)


def extract_all(out_dir: pathlib.Path, patterns_by_id: dict) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    bridge_js = BRIDGE_PATH.read_text(encoding="utf-8")
    count = 0
    for pid, (kind, key) in SPECIMEN_MAP.items():
        p = patterns_by_id.get(pid, {})
        title = f"{p.get('name_cn', pid)} — {p.get('name_en', pid)}"
        if kind == "ep26":
            html = _build_ep26(pid, key, title, bridge_js)
        elif kind == "ep27":
            html = _build_ep27(pid, key, title, bridge_js)
        elif kind == "ep28":
            html = _build_ep28(pid, key, title, bridge_js)
        elif kind == "ep29":
            html = _build_ep29(pid, key, title, bridge_js)
        elif kind == "ep30":
            html = _build_ep30(pid, key, title, bridge_js)
        elif kind == "ep31":
            html = _build_ep31(pid, key, title, bridge_js)
        elif kind == "anim":
            html = _build_anim(pid, key, title, bridge_js)
        else:
            raise ValueError(f"Unknown specimen kind {kind}")
        (out_dir / f"{pid}.html").write_text(html, encoding="utf-8")
        count += 1
    return count
