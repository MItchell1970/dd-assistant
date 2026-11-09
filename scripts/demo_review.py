"""Review captures of the demo at desktop (1440×900) and phone (375×812) width: the home page and the three
companies, full page. For looking at the layout after each change, not for the README.

1. Start the demo:   $env:DD_DEMO=1; streamlit run app.py --server.port 8599
2. python scripts\\demo_review.py <output folder> [http://localhost:8599]
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "review")
URL = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8599"
PAGES = {"home": "", "tap": "?company=tap", "toyota": "?company=toyota-caetano", "amorim": "?company=corticeira-amorim"}
SIZES = {"desktop": (1440, 900), "phone": (375, 812)}
TALL = 3600   # Streamlit scrolls inside the page: a tall viewport shows the whole page in one capture


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        for size, (w, h) in SIZES.items():
            page = browser.new_page(viewport={"width": w, "height": h}, is_mobile=size == "phone")
            for name, query in PAGES.items():
                page.goto(f"{URL}/{query}")
                page.wait_for_selector("[data-testid='stApp']")
                page.wait_for_function("!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60_000)
                page.wait_for_timeout(4000)   # let every element finish drawing
                wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                page.screenshot(path=OUT / f"{name}-{size}.png")
                page.set_viewport_size({"width": w, "height": TALL})
                page.wait_for_timeout(2500)
                page.screenshot(path=OUT / f"{name}-{size}-full.png")
                page.set_viewport_size({"width": w, "height": h})
                print(f"{name}-{size}.png" + ("  HORIZONTAL SCROLL" if wide else ""))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
