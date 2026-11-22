"""Captures of the local app on the messy Duriva data room (FICTITIOUS), 1440 px wide: docs/images/messy-mapping.png,
messy-proof-of-cash.png and messy-time.png. The app must be running (streamlit run app.py, port 8501).

    python scripts\\messy_screenshots.py
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

IMAGES = Path(__file__).resolve().parents[1] / "docs" / "images"
SHOTS = [("Mapping", "messy-mapping.png"), ("Proof of cash", "messy-proof-of-cash.png"),
         ("Time: manual vs agent", "messy-time.png")]


def main(url: str = "http://localhost:8501") -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 1300})
        page.goto(url)
        page.get_by_text("Duriva — messy data room", exact=False).first.wait_for(timeout=90_000)
        page.get_by_text("Duriva — messy data room", exact=False).first.click()
        page.get_by_text("FICTITIOUS, synthetic test data", exact=False).first.wait_for(timeout=120_000)
        for tab, name in SHOTS:
            page.get_by_role("tab", name=tab).first.click()
            page.wait_for_timeout(2500)
            page.evaluate("window.scrollTo(0, 0)")
            page.locator("[data-testid='stSidebarContent']").evaluate("e => e.scrollTop = 0")
            assert "Duriva" in page.inner_text("body")
            page.screenshot(path=str(IMAGES / name))
        browser.close()
    print("saved", ", ".join(n for _, n in SHOTS))


if __name__ == "__main__":
    main()
