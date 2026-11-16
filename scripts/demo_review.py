"""Review captures for docs/FASE5_DESIGN.md (section 6), with the layout criteria measured in the browser:
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
                    parts = {"band": page.evaluate(BOTTOM, ".band"), "kpis": page.evaluate(BOTTOM, ".kpi"),
                             "chips": page.evaluate(BOTTOM, "[class*='st-key-chip'] button"),
                             "top5": page.evaluate(BOTTOM, ".row:not(.h)")}
                    ok = all(0 < v <= h for v in parts.values())
                    results.append(f"1 Summary without scroll ({name}): {'met' if ok else 'FAILED'} {parts}")
                else:
                    first = page.evaluate(BOTTOM, ".kpi:first-child")
                    score = page.evaluate(BOTTOM, ".band")
                    ok = not wide and 0 < first <= h and 0 < score <= h
                    results.append(f"2 Phone ({name}): {'met' if ok else 'FAILED'} horizontal scroll={wide}, "
                                   f"score bottom={score:.0f}, first KPI bottom={first:.0f}")
                if name == "tap":
                    for view in VIEWS:
                        page.locator("[data-testid='stButtonGroup'] button", has_text=view).first.click()
                        page.wait_for_timeout(2500)
                        page.set_viewport_size({"width": w, "height": 3600})
                        page.wait_for_timeout(1500)
                        page.screenshot(path=OUT / f"tool-tap-{view.lower()}-{size}.png")
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
