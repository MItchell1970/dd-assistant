"""Captures of the local app finding a listed company (1440 px): docs/images/esef-search.png and esef-result.png.

The app must be running (streamlit run app.py, port 8501). The report is taken from output/esef_cache/ when it is
already there; otherwise the click downloads it (run only with Bernardo's OK).

    python scripts\\esef_screenshots.py "Schneider Electric"
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"


def main(company: str = "Schneider Electric", url: str = "http://localhost:8501") -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(url)
        box = page.get_by_label("Company name or LEI")
        box.wait_for(timeout=60_000)
        box.fill(company)
        box.press("Enter")
        page.get_by_role("button", name="Search").first.click()
        get = page.get_by_role("button", name="Download and analyse")
        get.wait_for(timeout=120_000)
        page.wait_for_timeout(1500)
        page.locator("[data-testid='stSidebarContent']").evaluate("e => e.scrollTop = 0")   # the search box in view
        page.wait_for_timeout(500)
        page.screenshot(path=str(IMAGES / "esef-search.png"))
        get.click()
        page.get_by_text("ESEF data quality").first.wait_for(timeout=180_000)
        page.wait_for_timeout(3000)
        title = page.locator(".dd-title").first.inner_text()
        if company.split()[0].lower() not in title.lower():
            raise SystemExit(f"The page shows {title!r}, not {company!r}")
        page.screenshot(path=str(IMAGES / "esef-result.png"))
        browser.close()
    print(f"Saved esef-search.png and esef-result.png in {IMAGES} ({title})")


if __name__ == "__main__":
    main(*sys.argv[1:])
