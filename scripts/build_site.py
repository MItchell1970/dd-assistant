"""The static site for GitHub Pages: site/index.html and one page per demo company (tap.html, toyota.html,
amorim.html), built from the engine and docs/examples. Every figure on the pages comes from the engine or the stored
examples (tests/test_site.py checks each one against the memo material).

    python scripts/build_site.py            # the pages and the files they link to
    python scripts/build_site.py --assets   # only copy the downloads and images (standard library, no engine)
    python scripts/build_site.py --screenshot   # also docs/images/site-home.png for the README (Playwright)

The downloads and images are copied, not committed twice: site/files and site/img are in .gitignore, and the
Pages workflow runs this script with --assets before publishing.
"""
from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
NAME = "DD Assistant"
SITE_URL = "https://mitchell1970.github.io/dd-assistant/"
DEMO_URL = "https://dd-assistant-tickmark.streamlit.app"
PAGES = {"tap": "tap.html", "toyota-caetano": "toyota.html", "corticeira-amorim": "amorim.html"}
MAIN_BRIDGE = {"tap": "net debt", "toyota-caetano": "ebitda", "corticeira-amorim": "cash"}
DOWNLOADS = (("databook.xlsx", "Databook", "Excel · live formulas, every source cell"),
             ("red_flag_report.pdf", "Red flag report", "PDF · slides for the deal team"),
             ("memo.md", "Memo and request list", "Markdown · every figure checked by code"))
IMAGES = ("demo-tour.gif", "social-preview.png")
FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&"
         "family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap")
E = html.escape


def copy_assets() -> None:
    for slug in PAGES:
        folder = SITE / "files" / slug
        folder.mkdir(parents=True, exist_ok=True)
        for name, *_ in DOWNLOADS:
            shutil.copy2(ROOT / "docs" / "examples" / slug / name, folder / name)
    (SITE / "img").mkdir(parents=True, exist_ok=True)
    for name in IMAGES:
        shutil.copy2(ROOT / "docs" / "images" / name, SITE / "img" / name)


# ---------------------------------------------------------------- style (inlined in each page)
CSS = """
:root{--bg:#fbfaf7;--surface:#fff;--ink:#13233f;--text:#2c3546;--muted:#5f6878;--line:#e4e1da;--navy:#13294b;
--accent:#b4611a;--accent-soft:#f5e9da;--down:#aab4c3;--chip:#eef0f3;--high:#b42318;--medium:#a15c07;--low:#5f6878;
--serif:"Source Serif 4",Georgia,"Times New Roman",serif;--sans:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d131e;--surface:#141c2a;--ink:#edf1f7;
--text:#cdd3dd;--muted:#959eae;--line:#273145;--navy:#9fb7e0;--accent:#e39a57;--accent-soft:#2b2117;--down:#4b5669;
--chip:#1d2637;--high:#f18c84;--medium:#e8b45e;--low:#959eae}}
:root[data-theme="dark"]{--bg:#0d131e;--surface:#141c2a;--ink:#edf1f7;--text:#cdd3dd;--muted:#959eae;--line:#273145;
--navy:#9fb7e0;--accent:#e39a57;--accent-soft:#2b2117;--down:#4b5669;--chip:#1d2637;--high:#f18c84;--medium:#e8b45e;
--low:#959eae}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font:400 16px/1.6 var(--sans);
font-variant-numeric:tabular-nums lining-nums;overflow-x:hidden}
a{color:var(--navy);text-underline-offset:3px}
a:hover{color:var(--accent)}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
header.top{border-bottom:1px solid var(--line)}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;height:60px}
.brand{font:600 1.05rem/1 var(--serif);color:var(--ink);text-decoration:none;letter-spacing:.01em}
nav a{color:var(--muted);text-decoration:none;font-size:.9rem;margin-left:22px}
nav a:hover{color:var(--ink)}
nav a.cta{color:var(--ink);font-weight:600}
h1,h2,h3{font-family:var(--serif);color:var(--ink);font-weight:600;letter-spacing:-.01em}
h1{font-size:clamp(2.1rem,5.2vw,3.4rem);line-height:1.08;margin:0 0 18px}
h2{font-size:clamp(1.5rem,3vw,2rem);line-height:1.2;margin:0 0 8px}
h3{font-size:1.25rem;line-height:1.3;margin:0}
.eyebrow{font-size:.75rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 14px}
.lede{font-size:1.2rem;line-height:1.55;color:var(--text);max-width:40em;margin:0}
.by{color:var(--muted);font-size:.92rem;margin:18px 0 0}
section{padding:72px 0;border-bottom:1px solid var(--line)}
section.hero{padding:80px 0 56px}
.sub{color:var(--muted);max-width:44em;margin:0 0 36px}
.btns{display:flex;flex-wrap:wrap;gap:12px;margin-top:30px}
.btn{display:inline-block;padding:11px 18px;border-radius:8px;font-weight:600;font-size:.95rem;text-decoration:none;
border:1px solid var(--line);color:var(--ink);background:var(--surface)}
.btn.primary{background:var(--navy);border-color:var(--navy);color:var(--bg)}
.btn.primary:hover{color:var(--bg);opacity:.92}
.btn:hover{border-color:var(--ink)}
.hint{display:block;color:var(--muted);font-size:.82rem;margin-top:8px}
figure{margin:0}
.demo{margin-top:48px;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--surface)}
.demo img{display:block;width:100%;height:auto}
.demo figcaption{padding:10px 16px;color:var(--muted);font-size:.85rem;border-top:1px solid var(--line)}
.cases{display:grid;gap:28px}
.case{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:32px;
display:grid;grid-template-columns:minmax(0,4fr) minmax(0,7fr);gap:40px}
.case .co{font:600 1.35rem/1.25 var(--serif);color:var(--ink);margin:0}
.case .acc{color:var(--muted);font-size:.85rem;margin:4px 0 22px}
.big{font:600 clamp(2.6rem,6vw,3.6rem)/1 var(--serif);color:var(--ink);letter-spacing:-.02em}
.big-label{color:var(--muted);font-size:.9rem;margin:8px 0 18px}
.headline{margin:0 0 22px}
.more{font-weight:600;font-size:.92rem}
.chart-title{font-size:.95rem;color:var(--ink);font-weight:600;margin:0 0 14px}
.chart-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}
svg.bridge{display:block;width:100%;height:auto;overflow:visible}
svg.bridge text{font-family:var(--sans);fill:var(--text);font-variant-numeric:tabular-nums}
svg.bridge text.val{font-size:12px;font-weight:500;fill:var(--ink)}
svg.bridge text.val.t{font-weight:600}
svg.bridge text.lbl{font-size:12px;fill:var(--muted)}
svg.bridge text.axis{font-size:11px;fill:var(--muted)}
svg.bridge rect.t{fill:var(--navy)}
svg.bridge rect.up{fill:var(--accent)}
svg.bridge rect.down{fill:var(--down)}
svg.bridge line.link{stroke:var(--muted);stroke-width:1;opacity:.55;shape-rendering:crispEdges}
svg.bridge line.zero{stroke:var(--muted);stroke-width:1;opacity:.6;shape-rendering:crispEdges}
.note{color:var(--muted);font-size:.78rem;margin:8px 0 0}
.legend{display:flex;flex-wrap:wrap;gap:14px;color:var(--muted);font-size:.78rem;margin-top:10px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.dl{display:flex;flex-wrap:wrap;gap:10px;margin-top:24px}
.dl a{display:block;flex:1 1 180px;border:1px solid var(--line);border-radius:10px;padding:12px 14px;text-decoration:none;
color:var(--ink);background:var(--bg)}
.dl a:hover{border-color:var(--ink)}
.dl b{display:block;font-weight:600;font-size:.92rem}
.dl span{display:block;color:var(--muted);font-size:.78rem;margin-top:2px}
.steps{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:24px;
counter-reset:s}
.steps li{counter-increment:s;border-top:2px solid var(--ink);padding-top:14px}
.steps li::before{content:counter(s,decimal-leading-zero);font:600 .85rem/1 var(--serif);color:var(--accent);display:block;
margin-bottom:10px}
.steps b{display:block;color:var(--ink);font-weight:600;margin-bottom:4px}
.steps span{color:var(--muted);font-size:.9rem;line-height:1.5}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px}
.stat .n{font:600 2.4rem/1 var(--serif);color:var(--ink);letter-spacing:-.02em}
.stat .t{color:var(--ink);font-weight:600;margin:10px 0 4px}
.stat p{color:var(--muted);font-size:.88rem;margin:0}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:40px}
ul.plain{margin:0;padding-left:18px}
ul.plain li{margin:0 0 8px}
.muted{color:var(--muted)}
.insights{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}
.insight{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:22px}
.insight h3{font-size:1.1rem;margin-bottom:10px}
.insight p{margin:0 0 10px;font-size:.92rem}
.insight .q{color:var(--muted);font-style:italic;margin:0}
.issues{border-top:1px solid var(--line)}
.issue{display:grid;grid-template-columns:150px minmax(0,1fr);gap:24px;padding:20px 0;border-bottom:1px solid var(--line)}
.issue .amt{font:600 1.5rem/1.1 var(--serif);color:var(--ink)}
.issue .al{color:var(--muted);font-size:.78rem;margin-top:4px}
.issue .h{font-weight:600;color:var(--ink);margin:0 0 4px}
.issue p{margin:0 0 6px;font-size:.92rem}
.issue .imp{color:var(--accent);font-weight:600;font-size:.85rem}
.tag{display:inline-block;font-size:.7rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;
border-radius:4px;background:var(--chip);color:var(--muted);margin-right:6px;vertical-align:2px}
.tag.High{color:var(--high)} .tag.Medium{color:var(--medium)}
.bridges{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:24px}
.panel.wide{grid-column:1/-1}
.context{border-left:3px solid var(--accent);padding:4px 0 4px 16px;color:var(--muted);font-size:.9rem;margin:28px 0 0;
max-width:44em}
.back{display:inline-block;color:var(--muted);text-decoration:none;font-size:.9rem;margin-bottom:28px}
footer{padding:40px 0 56px;color:var(--muted);font-size:.85rem}
footer .wrap{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px}
@media (max-width:900px){.case{grid-template-columns:minmax(0,1fr);gap:28px}.steps{grid-template-columns:1fr 1fr}
.stats{grid-template-columns:1fr 1fr}.insights{grid-template-columns:1fr}.bridges{grid-template-columns:minmax(0,1fr)}}
@media (max-width:600px){.wrap{padding:0 16px}nav a:not(.cta){display:none}section{padding:52px 0}
section.hero{padding:52px 0 40px}.case{padding:22px 18px}.steps{grid-template-columns:1fr}.cols{grid-template-columns:1fr}
.stats{grid-template-columns:1fr 1fr;gap:28px 18px}.stat .n{font-size:2rem}.issue{grid-template-columns:1fr;gap:6px}
.lede{font-size:1.08rem}.panel{padding:18px 14px}.dl a{flex-basis:100%}}
"""


# ---------------------------------------------------------------- pieces
def minus(text: str) -> str:
    """A typographic minus for negative amounts (-€43m → −€43m)."""
    return text.replace("-€", "−€")


SHORT = {  # short names under the columns (the full name stays in the column's title and aria-label)
    "Reported EBITDA": "Reported EBITDA", "Change in net working capital": "Working capital",
    "Tax, interest and other operating items": "Tax & interest",
    "Working capital, tax and other operating items": "WC, tax & interest", "Operating cash flow": "Operating cash flow",
    "Capex": "Capex", "Proceeds from asset disposals": "Disposals", "Free cash flow": "Free cash flow",
    "Lease payments": "Lease payments", "Lease payments (cash flow statement)": "Lease payments",
    "Free cash flow after leases": "FCF after leases", "EBITDA before IFRS 16": "EBITDA pre-IFRS 16",
    "Borrowings less cash": "Net debt (ex-leases)", "Post-employment benefit obligations": "Pensions",
    "Lease liabilities": "Leases", "Income tax payable": "Tax payable", "Adjusted net debt": "Adjusted net debt",
    "Diligence-adjusted EBITDA": "Adjusted EBITDA"}


def _two_lines(text: str, width: int = 11) -> list[str]:
    """A short name on at most two lines of about `width` characters (the rest is cut with an ellipsis)."""
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    if len(lines[-1]) > width + 3:
        lines[-1] = lines[-1][:width + 2].rstrip() + "\u2026"
    return lines


def bridge_svg(steps: list, money, title: str) -> str:
    """A bridge as the vertical waterfall of a deal report: totals as full columns from the baseline, items as
    floating columns (increase / decrease), the value on each column with an explicit sign on the items, short names
    underneath, thin connectors in the gaps. The SVG scales with its viewBox but never below the width at which its
    smallest text is 11 px; below that the chart slides sideways. The steps come from the engine (deal.py); this
    only places them, and notes when the rounded items do not add up to the rounded total."""
    if len(steps) < 2:
        return ""
    from dd_assistant.units import _round
    rows, level = [], 0.0
    for label, value, kind in steps:
        start, end = (0.0, value) if kind == "total" else (level, level + value)
        level = end
        rows.append((label, value, kind, start, end))
    lo = min([0.0] + [min(s, e) for *_, s, e in rows])
    hi = max([0.0] + [max(s, e) for *_, s, e in rows])
    span = (hi - lo) or 1.0
    LEFT, SLOT, BAR, TOP, PLOT, BELOW, LINE = 26, 70, 40, 30, 190, 24, 14
    W, H = LEFT + len(rows) * SLOT + 6, TOP + PLOT + BELOW + 2 * LINE + 8
    y = lambda v: TOP + (hi - v) / span * PLOT
    out = [f'<div class="chart-scroll"><svg class="bridge" viewBox="0 0 {W} {H}" '
           f'style="min-width:{W * 11 / 12:.0f}px;max-width:{W * 1.25:.0f}px" role="group" aria-label="{E(title)}">']
    if lo < 0:
        out.append(f'<line class="zero" x1="{LEFT - 4}" x2="{W}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>'
                   f'<text class="axis" data-nocheck="1" x="{LEFT - 8}" y="{y(0) + 4:.1f}" text-anchor="end">0</text>')
    for i, (label, value, kind, start, end) in enumerate(rows):
        x = LEFT + i * SLOT + (SLOT - BAR) / 2
        cls = "t" if kind == "total" else "up" if value > 0 else "down"
        text = minus(money.fmt(value) if kind == "total" else ("+" if value > 0 else "") + money.fmt(value))
        top, bottom = y(max(start, end)), y(min(start, end))
        ty = bottom + 15 if value < 0 else top - 7      # a negative total or a decrease: the value under its column
        cx = x + BAR / 2
        name = f"{label}: {text}"
        names = "".join(f'<tspan x="{cx:.1f}" dy="{0 if k == 0 else LINE}">{E(s)}</tspan>'
                        for k, s in enumerate(_two_lines(SHORT.get(label, label))))
        out.append(f'<g role="img" aria-label="{E(name)}"><title>{E(name)}</title>'
                   f'<rect class="{cls}" x="{x:.1f}" y="{top:.1f}" width="{BAR}" height="{max(bottom - top, 1.5):.1f}"/>'
                   f'<text class="val {cls}" x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle">{E(text)}</text>'
                   f'<text class="lbl" x="{cx:.1f}" y="{TOP + PLOT + BELOW + LINE - 2}" text-anchor="middle">{names}</text></g>')
        if i < len(rows) - 1:
            out.append(f'<line class="link" x1="{x + BAR:.1f}" x2="{x + SLOT:.1f}" y1="{y(end):.1f}" y2="{y(end):.1f}"/>')
    out.append("</svg></div>")
    # rounding: the items as shown, added to the total before them, against the next total as shown
    r = lambda v: _round(v / 1000 if money.millions else v)
    running, diff = None, 0
    for label, value, kind, *_ in rows:
        if kind == "total":
            if running is not None and r(value) != running:
                diff = max(diff, abs(r(value) - running))
            running = r(value)
        elif running is not None:
            running += r(value)
    if diff:
        unit = "m" if money.millions else "k"
        out.append(f'<p class="note" data-nocheck="1">Differences of {money.symbol}{diff}{unit} are due to '
                   "rounding.</p>")
    return "".join(out)


LEGEND = ('<div class="legend"><span><i style="background:var(--navy)"></i>Total</span>'
          '<span><i style="background:var(--accent)"></i>Increase</span>'
          '<span><i style="background:var(--down)"></i>Decrease</span></div>')


def bridges(c, a) -> dict[str, tuple[str, list]]:
    """The bridges of a company, each as (title, steps), from the engine."""
    from dd_assistant.deal import cash_steps, ifrs16_steps, net_debt_steps, qoe_steps
    from dd_assistant.rules import fy
    L, B, unit = a.data.years[-1], a.view.bs_years[-1], a.money.unit
    qoe = qoe_steps(a.view, L)
    ebitda = (f"EBITDA bridge, {fy(L)}", qoe) if len(qoe) > 2 else \
        (f"EBITDA and the lease payments, {fy(L)}", ifrs16_steps(a.view, a.data, L))
    out = {"ebitda": ebitda,
           "net debt": (f"Net debt bridge, {fy(B)}", net_debt_steps(a.view, B)),
           "cash": (f"From EBITDA to free cash flow, {fy(L)}", cash_steps(a.view, a.data, a.metrics, L))}
    unit = f"{a.money.symbol}{'m' if a.money.millions else 'k'}"
    return {k: (f"{t} ({unit})", s) for k, (t, s) in out.items() if len(s) >= 2}


def downloads(slug: str) -> str:
    return '<div class="dl">' + "".join(
        f'<a href="files/{slug}/{name}" download><b>{E(label)}</b><span>{E(what)}</span></a>'
        for name, label, what in DOWNLOADS) + "</div>"


def page(title: str, description: str, body: str, path: str = "") -> str:
    url = SITE_URL + path
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#fbfaf7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0d131e" media="(prefers-color-scheme: dark)">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}img/social-preview.png">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="640">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%2313294b'/%3E%3Cpath d='M9 17l5 5 9-11' stroke='%23e39a57' stroke-width='3.2' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap"><a class="brand" href="index.html">{NAME}</a>
<nav><a href="index.html#cases">Cases</a><a href="index.html#how">How it works</a><a href="index.html#verified">Verification</a><a class="cta" href="{DEMO_URL}">Interactive demo</a></nav></div></header>
<main>
{body}
</main>
<footer><div class="wrap"><span>{E(NAME)} · preliminary analysis on published accounts, not an opinion.</span>
<span><a href="{{github}}">GitHub</a> · <a href="{{linkedin}}">LinkedIn</a></span></div></footer>
</body>
</html>
"""


# ---------------------------------------------------------------- pages
def index(cases: list) -> str:
    from dd_assistant import demo
    v, d = demo.verification(), demo.detection()
    cards = []
    for c, a in cases:
        title, steps = bridges(c, a)[MAIN_BRIDGE[c.slug]]
        cards.append(f"""<article class="case" data-check="{c.slug}">
<div><p class="co">{E(c.company)}</p><p class="acc">{E(c.accounts)}</p>
<div class="big">{E(c.big)}</div><p class="big-label">{E(c.big_label)}</p>
<p class="headline">{E(c.headline)}</p>
<a class="more" href="{PAGES[c.slug]}">Key issues and all bridges →</a></div>
<div><p class="chart-title">{E(title)}</p>{bridge_svg(steps, a.money, title)}{LEGEND}{downloads(c.slug)}</div>
</article>""")
    steps = "".join(f"<li><b>{E(t)}</b><span>{E(s)}</span></li>" for _, t, s in demo.PROCESS)
    limits = "".join(f"<li>{E(x)}.</li>" for x in demo.LIMITS)
    unmeasured = "".join(f"<li>{E(x)}</li>" for x in demo.NOT_MEASURED)
    body = f"""<section class="hero"><div class="wrap">
<p class="eyebrow">Financial due diligence · European companies · euros</p>
<h1>{NAME}</h1>
<p class="lede">{E(demo.TAGLINE)}.</p>
<p class="by">{E(demo.BUILT_BY)}.</p>
<div class="btns"><a class="btn primary" href="#cases">See the three cases</a><a class="btn" href="{DEMO_URL}">Interactive demo</a><a class="btn" href="{demo.GITHUB}">Code on GitHub</a></div>
<figure class="demo"><img src="img/demo-tour.gif" width="1000" height="625" alt="The interactive demo: the reading checks, the key insight, the net debt bridge, a red flag with its source and the databook">
<figcaption>The interactive demo on TAP Air Portugal: reading checks, key insight, net debt bridge, a red flag with its source.</figcaption></figure>
</div></section>
<section id="cases"><div class="wrap">
<p class="eyebrow">Three real companies</p><h2>Published accounts, read end to end</h2>
<p class="sub">Consolidated accounts for FY2023 to FY2025, read line by line from the annual reports. The figures below come from the engine; the memos were written beforehand and checked by code against the same material.</p>
<div class="cases">{''.join(cards)}</div>
</div></section>
<section id="how"><div class="wrap">
<p class="eyebrow">How it works</p><h2>Five steps, the order a deal team follows</h2>
<p class="sub">The code does every calculation and raises every finding. AI only writes the memo, and a checker rejects any figure it cannot trace.</p>
<ol class="steps">{steps}</ol>
</div></section>
<section id="verified"><div class="wrap">
<p class="eyebrow">How it is verified</p><h2>Evidence before conclusions</h2>
<p class="sub">Counted when this page was built, from the same code and data.</p>
<div class="stats">
<div class="stat"><div class="n">{v['tests']}</div><p class="t">automated tests</p><p>Including parity with the reference spreadsheet and zero red flags on a clean test company.</p></div>
<div class="stat"><div class="n">{v['checks_passed']} of {v['checks']}</div><p class="t">published subtotals rebuilt</p><p>Gross margin, EBITDA and operating profit rebuilt from the lines read, before any figure is trusted.</p></div>
<div class="stat"><div class="n">{d.get('detected', 0)} of {d.get('scored', 0)}</div><p class="t">planted distortions detected</p><p>The miss: 20 extra days of supplier credit at TAP, hidden by a real fall of 96 days in its payables and below its materiality. Published, not tuned away.</p></div>
<div class="stat"><div class="n">{v['figures']}</div><p class="t">memo figures checked</p><p>Each figure in the three memos traced to the material for the year it cites; {v['unmatched']} without a source.</p></div>
</div>
</div></section>
<section id="limits"><div class="wrap cols">
<div><p class="eyebrow">Limits</p><h2>What it does not do</h2><ul class="plain">{limits}</ul></div>
<div><p class="eyebrow">Not measured</p><h2>What is not proven yet</h2><ul class="plain">{unmeasured}</ul></div>
</div></section>
<section id="demo"><div class="wrap">
<p class="eyebrow">Try it</p><h2>Open the interactive demo</h2>
<p class="sub">The same engine on the same three companies: change the reviewer's decisions, follow any figure to its cell, download the databook. Nothing is uploaded and no AI is called.</p>
<div class="btns"><span><a class="btn primary" href="{DEMO_URL}">Interactive demo</a><span class="hint">May take a few seconds to wake up.</span></span>
<a class="btn" href="{demo.GITHUB}">GitHub</a><a class="btn" href="{demo.LINKEDIN}">LinkedIn</a></div>
</div></section>"""
    return page(f"{NAME}: financial due diligence on published accounts",
                f"{demo.TAGLINE}. Three real European companies, every figure traced to its source.", body)


def company(c, a) -> str:
    from dd_assistant import demo
    from dd_assistant.rules import fy
    fired = {r.rule.id for r in a.findings}
    insights = "".join(f'<article class="insight"><h3>{E(i["title"])}</h3><p>{E(i["number"][:1].upper() + i["number"][1:])}</p>'
                       f'<p>{E(i["why"][:1].upper() + i["why"][1:])}</p><p class="q">“{E(i["question"])}”</p></article>'
                       for i in demo.insights(c))
    rows = []
    for i in a.issues[:8]:
        amount = minus(a.money.fmt(i.amount)) if i.amount is not None else "Not quantified"
        label = (f"{i.amount_label}, {fy(i.year)}" if i.key in fired and i.amount is not None else
                 "not quantifiable from the accounts" if i.amount is None else i.amount_label)
        head = (f'<span class="tag {E(i.severity)}">{E(i.severity)}</span>{E(i.key)} · {E(i.title)}' if i.key in fired
                else f'<span class="tag">{E(i.kind)}</span>{E(i.title)}')
        plain = next(r.rule.plain for r in a.findings if r.rule.id == i.key) if i.key in fired else i.treatment
        state = (f" Evidence: {i.evidence_state}" + (f" by {i.evidence_note}" if i.evidence_note else "") + "."
                 if i.evidence_state else "")
        rows.append(f'<div class="issue"><div><div class="amt">{E(amount)}</div><div class="al">{E(label)}</div></div>'
                    f'<div><p class="h">{head}</p><p>{E(plain)}{E(state)}</p>'
                    f'<p class="imp">{E(i.implication)}</p></div></div>')
    more = len(a.issues) - len(rows)
    panels = "".join(f'<div class="panel{" wide" if k == "cash" else ""}"><p class="chart-title">{E(t)}</p>'
                     f"{bridge_svg(s, a.money, t)}</div>" for k, (t, s) in bridges(c, a).items())
    context = (f'<p class="context">Outside context, not used by the engine or the memo: {E(c.context)} '
               f'<a href="{c.context_source[1]}">{E(c.context_source[0])}</a></p>' if c.context else "")
    body = f"""<section class="hero"><div class="wrap">
<a class="back" href="index.html#cases">← All cases</a>
<div data-check="{c.slug}">
<p class="eyebrow">Case · {E(a.sector.name)}</p>
<h1>{E(c.company)}</h1>
<p class="lede">{E(c.headline)}</p>
<p class="by">{E(c.accounts)} · {E(c.pages)}</p>
<div class="btns"><a class="btn primary" href="{DEMO_URL}/?company={c.slug}">Open in the interactive demo</a><a class="btn" href="#downloads">Downloads</a></div>
</div>{context}
</div></section>
<section data-check="{c.slug}"><div class="wrap">
<p class="eyebrow">Key insights</p><h2>Three points for the first call</h2>
<p class="sub">Each with the figure, why it matters in a deal and the question for management.</p>
<div class="insights">{insights}</div>
</div></section>
<section data-check="{c.slug}"><div class="wrap">
<p class="eyebrow">Key issues</p><h2>By amount at stake</h2>
<p class="sub">Findings and net debt items in one list, ordered by the euros behind them, each with what a deal team typically does about it.</p>
<div class="issues">{''.join(rows)}</div>
<p class="muted">{f"And {more} more in the databook." if more > 0 else ""}</p>
</div></section>
<section data-check="{c.slug}"><div class="wrap">
<p class="eyebrow">Bridges</p><h2>EBITDA, net debt and cash</h2>
<p class="sub">Each step computed by the engine from the published lines; the databook holds the same bridges with live formulas.</p>
<div class="bridges">{panels}</div>{LEGEND}
</div></section>
<section id="downloads"><div class="wrap">
<p class="eyebrow">Downloads</p><h2>The deliverables</h2>
{downloads(c.slug)}
</div></section>"""
    return page(f"{c.company}: {NAME}", c.headline, body, PAGES[c.slug])


def render() -> dict[str, str]:
    """The pages, by file name (also used by the test that the stored site is current)."""
    from dd_assistant import demo
    cases = [(c, demo.analysis(c)) for c in demo.CASES]
    pages = {"index.html": index(cases)} | {PAGES[c.slug]: company(c, a) for c, a in cases}
    return {k: v.replace("{github}", demo.GITHUB).replace("{linkedin}", demo.LINKEDIN) for k, v in pages.items()}


def build() -> list[Path]:
    SITE.mkdir(exist_ok=True)
    out = []
    for name, text in render().items():
        (SITE / name).write_text(text, encoding="utf-8", newline="\n")
        out.append(SITE / name)
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    return out


def screenshot() -> Path:
    """docs/images/site-home.png: the top of the home page at 1440 px, light theme, for the README (Playwright with
    the Edge of this PC; not a requirement of the site)."""
    from playwright.sync_api import sync_playwright
    out = ROOT / "docs" / "images" / "site-home.png"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1.5,
                                color_scheme="light")
        page.goto((SITE / "index.html").as_uri(), wait_until="networkidle")
        page.wait_for_timeout(800)
        page.screenshot(path=str(out))
        browser.close()
    return out


if __name__ == "__main__":
    copy_assets()
    if "--assets" not in sys.argv:
        sys.path.insert(0, str(ROOT))
        for p in build():
            print(p.relative_to(ROOT))
    if "--screenshot" in sys.argv:
        print(screenshot().relative_to(ROOT))
