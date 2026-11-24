---
name: interaction-lab
description: Query Interaction Lab via the `ilab` CLI (or HTTP endpoints) to discover proven, high-craft UI/UX interaction patterns by category or symptom, then implement them faithfully using exact CSS motion tokens, explicit state machines, and anti-pattern guardrails. Use whenever designing or coding UI interactions, micro-feedback, navigation, drag-and-drop, scroll choreography, dashboards, or visual surfaces.
---

# Interaction Lab — AI-Native UI/UX Skill

Never invent generic `transition: all 0.5s ease` animations from scratch. Whenever you design or build an interactive UI element, consult **Interaction Lab** first to retrieve exact motion tokens, explicit state machines, anti-pattern guardrails (`DO NOT`), and verified reference code.

## Mandatory 3-Step Workflow

### Step 1 — Browse by Category or Search by UI Symptom
Run the `ilab` CLI (or `curl` the server directly if `ilab` is not installed):

```bash
# List the 6 interaction intent categories
ilab categories

# List patterns inside a specific category
ilab list feedback-receipts
ilab list direct-manipulation
ilab list navigation-focus
ilab list scroll-rhythm
ilab list spatial-hierarchy
ilab list surface-optics

# Search by Chinese or English symptom / component name
ilab search "按钮没反馈"
ilab search "毛玻璃拖拽"
ilab search "3D 透视"
ilab search "skeleton"
```

*(HTTP fallback if CLI is unavailable: `curl -s $ILAB_URL/llms.txt`, `curl -s $ILAB_URL/api/categories`, `curl -s "$ILAB_URL/api/search?q=..."`)*

### Step 2 — Pull the Exact Blueprint
Once you select the best matching `<slug>`, fetch its complete engineering blueprint:

```bash
# Fetch Token Contract + State Machine + DO NOT Guardrails + Minimal Runnable Skeleton + Self-Check
ilab get <slug>

# Optional: fetch the full high-craft standalone visual reference HTML
ilab get <slug> --raw-html
```

*(HTTP fallback: `curl -s $ILAB_URL/patterns/<slug>.md` or `$ILAB_URL/specimens/<slug>.html`)*

### Step 3 — Implement Without Cutting Corners
1. **Copy the exact CSS Token Contract verbatim** (timings, `cubic-bezier(...)` curves, scale ratios, blur radii). Do NOT degrade them to generic `ease` or `0.5s`.
2. **Implement EVERY state** in the State Machine table (`idle`, `pressed`, `sending`, `done`, `hover`, `yield`, etc.), including re-entry locks where specified.
3. **Obey EVERY `DO NOT` guardrail** listed in the blueprint.
4. **Apply universal motion hygiene**:
   - Animate only GPU-composited properties (`transform`, `opacity`, `stroke-dashoffset`, color). Never animate `width`, `height`, `top`, `left`, or `margin`.
   - Always set `font-variant-numeric: tabular-nums` on dynamic numbers, counters, prices, and dates.
   - Always include `@media (prefers-reduced-motion: reduce)` fallbacks.
5. **Run the blueprint's Self-Check checklist** before finalizing your response.
