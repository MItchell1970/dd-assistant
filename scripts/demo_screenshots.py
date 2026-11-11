"""Images of the demo for the README and the home page, with Playwright and the Edge installed on this PC.

1. Start the demo:   $env:DD_DEMO=1; streamlit run app.py --server.port 8599
2. In another terminal:   pip install playwright   (once; not a requirement of the app)
                          python scripts\\demo_screenshots.py [http://localhost:8599]
Saves in docs/images/: demo-home.png, demo-overview.png, demo-net-debt.png, demo-memo.png, demo-tour.gif (TAP →
net debt → a red flag with its page → the Excel) and social-preview.png (1280×640, for GitHub's Social preview).
"""
from __future__ import annotations

import html
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "images"
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8599"


def ready(page) -> None:
    page.wait_for_selector("[data-testid='stApp']")
    page.wait_for_function("!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60_000)
    page.wait_for_timeout(3500)


def frame(page, clip=None) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")


def gif(frames: list[tuple[Image.Image, int]], path: Path, width: int = 1000) -> None:
    """Frames with their duration in ms, resized to one width, saved as a looping GIF."""
    size = (width, round(frames[0][0].height * width / frames[0][0].width))
    shots = [f.resize(size, Image.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f, _ in frames]
    shots[0].save(path, save_all=True, append_images=shots[1:], duration=[d for _, d in frames], loop=0,
                  optimize=True)


def social_preview(browser) -> None:
    from dd_assistant.demo import CASE_BY_SLUG, TAGLINE
    tap = CASE_BY_SLUG["tap"]
    page = browser.new_page(viewport={"width": 1280, "height": 640})
    page.set_content(f"""<html><body style="margin:0;font-family:'Source Sans Pro','Segoe UI',sans-serif">
      <div style="width:1280px;height:640px;box-sizing:border-box;padding:72px 84px;background:#0b3d91;color:#fff;
                  display:flex;flex-direction:column;justify-content:space-between">
        <div><div style="font-size:26px;letter-spacing:.12em;opacity:.8">LIVE DEMO · PUBLISHED ACCOUNTS</div>
             <div style="font-size:84px;font-weight:700;margin-top:10px">DD Assistant</div>
             <div style="font-size:34px;margin-top:8px;max-width:1050px">{html.escape(TAGLINE)}.</div></div>
        <div style="display:flex;align-items:flex-end;gap:28px">
          <div style="font-size:96px;font-weight:800;line-height:1">{html.escape(tap.big)}</div>
          <div style="font-size:30px;padding-bottom:12px">TAP Air Portugal: {html.escape(tap.big_label)}<br>
               <span style="opacity:.75">FY2025 · every figure traced to its source</span></div></div>
      </div></body></html>""")
    page.screenshot(path=OUT / "social-preview.png")
    page.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        frames = []
        page.goto(URL)
        ready(page)
        page.screenshot(path=OUT / "demo-home.png")   # not a GIF frame: the home page shows the GIF itself

        page.goto(f"{URL}/?company=tap")
        ready(page)
        page.screenshot(path=OUT / "demo-overview.png")
        frames.append((frame(page), 3000))
        chart = page.locator("[data-testid='stVegaLiteChart']").first
        chart.scroll_into_view_if_needed()
        page.wait_for_timeout(1200)
        chart.locator("xpath=../../..").screenshot(path=OUT / "demo-net-debt.png")
        frames.append((frame(page), 3500))

        page.get_by_role("button", name="Take the 60-second tour").click()
        dialog = page.get_by_role("dialog")
        for step in range(5):
            dialog.wait_for()
            page.wait_for_timeout(1500)
            if step in (2, 3, 4):
                frames.append((frame(page), 4000 if step == 3 else 3000))
            if step < 4:
                dialog.get_by_role("button", name="Next").click()
        frames.append((Image.open(OUT / "databook-net-debt.png").convert("RGB").resize(frames[0][0].size), 4000))
        dialog.get_by_role("button", name="Finish").click()
        page.wait_for_timeout(1500)

        page.get_by_role("tab", name="Memo").click()
        page.wait_for_timeout(1500)
        page.screenshot(path=OUT / "demo-memo.png")
        gif(frames, OUT / "demo-tour.gif")
        social_preview(browser)
        browser.close()
    print("saved", ", ".join(sorted(x.name for x in OUT.glob("*") if x.name.startswith(("demo-", "social")))))


if __name__ == "__main__":
    main()
