"""Screenshots of the demo for the README, with Playwright and the Edge installed on this PC.

1. Start the demo:   $env:DD_DEMO=1; streamlit run app.py --server.port 8599
2. In another terminal:   pip install playwright   (once; not a requirement of the app)
                          python scripts\\demo_screenshots.py [http://localhost:8599]
Saves docs/images/demo-*.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8599"


def wait_ready(page) -> None:
    page.wait_for_selector("[data-testid='stApp']")
    page.wait_for_function("!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60_000)
    page.wait_for_timeout(1500)


def tab(page, name: str) -> None:
    page.get_by_role("tab", name=name).click()
    page.wait_for_timeout(1200)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        page.goto(URL)
        wait_ready(page)
        page.screenshot(path=OUT / "demo-home.png")

        page.goto(f"{URL}/?company=tap")
        wait_ready(page)
        page.screenshot(path=OUT / "demo-overview.png")
        tab(page, "Deal view")
        bridges = page.locator("table.dd-br")            # quality of earnings, net debt, working capital
        bridges.nth(1).scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        bridges.nth(1).screenshot(path=OUT / "demo-net-debt.png")
        tab(page, "Memo")
        page.screenshot(path=OUT / "demo-memo.png")
        browser.close()
    print("saved", ", ".join(sorted(x.name for x in OUT.glob("demo-*.png"))))


if __name__ == "__main__":
    main()
