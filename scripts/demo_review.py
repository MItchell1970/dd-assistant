"""Review captures for docs/FASE6_DESIGN.md (section 7), with the layout criteria measured in the browser:
the tool (demo mode of app.py) for the three companies and its four views on TAP, and the static site.

1. Start the tool:   $env:DD_DEMO=1; streamlit run app.py --server.port 8599
2. Serve the site:   python -m http.server 8765 -d site
3. python scripts\\demo_review.py <output folder> [tool URL] [site URL]

Prints one line per capture and the criteria: 1 (Summary at 1440×900 without scroll), 2 (375 px: no horizontal
scroll, score and first KPI on the first screen) and 9 (company page of the site within 3 screens at 1440 px).
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "review")
TOOL = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8599"
SITE = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8765"
COMPANIES = {"tap": "tap", "toyota": "toyota-caetano", "amorim": "corticeira-amorim"}
SIZES = {"desktop": (1440, 900), "phone": (375, 812)}
VIEWS = ("Findings", "Impact", "Evidence")

BOTTOM = """(sel) => { const els = [...document.querySelectorAll(sel)];
  return els.length ? Math.max(...els.map(e => e.getBoundingClientRect().bottom)) : -1 }"""


def ready(page) -> None:
    page.wait_for_selector("[data-testid='stApp']")
    page.wait_for_function("!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=90_000)
    page.wait_for_timeout(3000)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        for size, (w, h) in SIZES.items():
            page = browser.new_page(viewport={"width": w, "height": h}, is_mobile=size == "phone")
            for name, slug in COMPANIES.items():
                page.goto(f"{TOOL}/?company={slug}")
                ready(page)
                wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                page.screenshot(path=OUT / f"tool-{name}-{size}.png")
                if size == "desktop":
                    parts = {"hero": page.evaluate(BOTTOM, ".hero"), "kpis": page.evaluate(BOTTOM, ".kpi"),
                             "chips": page.evaluate(BOTTOM, "[class*='st-key-chip'] button"),
                             "top5": page.evaluate(BOTTOM, ".row:not(.h)")}
                    ok = all(0 < v <= h for v in parts.values())
                    results.append(f"2 Summary without scroll ({name}): {'met' if ok else 'FAILED'} {parts}")
                    top = page.evaluate("Math.min(...[...document.querySelectorAll('[data-testid=stButtonGroup], "
                                        ".brand')].map(e => e.getBoundingClientRect().top))")
                    bar = page.evaluate("(() => { const h = document.querySelector('[data-testid=stHeader]'); "
                                        "return !!h && getComputedStyle(h).display !== 'none' })()")
                    results.append(f"1 Top readable ({name}): {'met' if top <= 32 and not bar else 'FAILED'} "
                                   f"(first control at {top:.0f} px, Streamlit bar visible={bar})")
                else:
                    first = page.evaluate(BOTTOM, ".kpi:first-child")
                    score = page.evaluate("document.querySelector('.hero .big').getBoundingClientRect().top")
                    ok = not wide and 0 < score <= 320
                    results.append(f"2 Phone ({name}): {'met' if ok else 'FAILED'} horizontal scroll={wide}, "
                                   f"score top={score:.0f} (criterion: within 320 px)")
                if name == "tap":
                    for view in VIEWS:
                        page.locator("[data-testid='stButtonGroup'] button", has_text=view).first.click()
                        page.wait_for_timeout(2500)
                        page.set_viewport_size({"width": w, "height": 3600})
                        page.wait_for_timeout(1500)
                        if view == "Impact" and size == "desktop":
                            ratio = page.evaluate("Math.min(...[...document.querySelectorAll('.ddc-wide svg')]"
                                                  ".map(s => s.getBoundingClientRect().width / "
                                                  "s.closest('.ddc').getBoundingClientRect().width))")
                            results.append(f"8 Bridges fill the card: {'met' if ratio >= .9 else 'FAILED'} "
                                           f"(narrowest {ratio:.0%} of its card)")
                        page.screenshot(path=OUT / f"tool-tap-{view.lower()}-{size}.png")
                        if view == "Impact":         # the multiple moves numbers: 6x and 10x
                            slider = page.locator("[data-testid='stSlider'] input[type='range']").first
                            texts = {}
                            for label, key, n in (("6x", "ArrowLeft", 4), ("10x", "ArrowRight", 8)):
                                slider.focus()
                                for _ in range(n):
                                    slider.press(key)
                                page.wait_for_timeout(2500)
                                texts[label] = page.evaluate("[...document.querySelectorAll('.kpi .v')].map(e => "
                                                             "e.innerText).join(' | ')")
                                page.screenshot(path=OUT / f"tool-tap-impact-{label}-{size}.png")
                            moved = texts["6x"] != texts["10x"]
                            results.append(f"4 Multiple moves numbers ({size}): {'met' if moved else 'FAILED'} "
                                           f"6x: {texts['6x']} · 10x: {texts['10x']}")
                        if view == "Evidence":       # chips stay inside their cards
                            out = page.evaluate("[...document.querySelectorAll('[class*=st-key-moment]')].reduce("
                                                "(n, c) => n + [...c.querySelectorAll('.tag')].filter(t => "
                                                "t.getBoundingClientRect().right > c.getBoundingClientRect().right + 1)"
                                                ".length, 0)")
                            results.append(f"5 Evidence chips inside their cards ({size}): "
                                           f"{'met' if out == 0 else 'FAILED'} ({out} outside)")
                        page.set_viewport_size({"width": w, "height": h})
                    page.locator("[data-testid='stButtonGroup'] button", has_text="Summary").first.click()
                print(f"tool-{name}-{size}.png" + ("  HORIZONTAL SCROLL" if wide else ""))
            for name in ("index", "tap"):
                page.goto(f"{SITE}/{name}.html", wait_until="networkidle")
                page.wait_for_timeout(800)
                wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                height = page.evaluate("document.documentElement.scrollHeight")
                page.screenshot(path=OUT / f"site-{name}-{size}.png", full_page=True)
                if name == "tap" and size == "desktop":
                    results.append(f"9 Company page within 3 screens: {'met' if height <= 3 * h else 'FAILED'} "
                                   f"({height} px)")
                if size == "phone":
                    results.append(f"2 Site {name} at 375 px: {'met' if not wide else 'FAILED'} (horizontal scroll="
                                   f"{wide})")
                print(f"site-{name}-{size}.png" + ("  HORIZONTAL SCROLL" if wide else ""))
            page.close()
        browser.close()
    print("\n".join(results))


if __name__ == "__main__":
    main()
