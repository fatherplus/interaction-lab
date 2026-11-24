# Display font provenance

Face: **Bricolage Grotesque** (Google Fonts, SIL Open Font License).
Chosen for optical-size character fitting the "optics bench" world; not a training-data default display face.

Pipeline (reproducible):
1. Fetch Latin variable WOFF2 (opsz 12..96, wght 300..800) from Google Fonts `css2` API with a modern UA → `bricolage-latin.woff2` (~77KB).
2. Instantiate + subset with fontTools: pin `opsz=48`, restrict `wght` to 500–800, subset to ASCII + `· ° × – — ← → − ✦`, keep kern/liga/tnum → `bricolage-display.woff2` (~21KB).
3. base64 → `font.b64`, inlined via `@@FONT@@` in `src/index.html` and `src/chrome.css` at build (zero external requests).

Used only for brand / big numerals / English (display voice). Chinese uses the system CJK stack; monospace readouts use the system mono stack (data/measurement only).

Rebuild subset example:
```python
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.subset import Subsetter, Options
f = TTFont("bricolage-latin.woff2")
instancer.instantiateVariableFont(f, {"opsz": 48, "wght": (500, 800)}, inplace=True)
opt = Options(); opt.flavor = "woff2"; opt.layout_features = ["kern", "liga", "tnum"]
ss = Subsetter(options=opt)
ss.populate(unicodes=[*range(0x20, 0x7F), 0xB7, 0xB0, 0xD7, 0x2013, 0x2014, 0x2190, 0x2192, 0x2212, 0x2726])
ss.subset(f); f.save("bricolage-display.woff2")
```