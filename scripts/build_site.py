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


def fy(year: int) -> str:
    return f"FY{str(year)[2:]}"


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
:root{--bg:#0d1117;--surface:#161b22;--ink:#e6edf3;--text:#e6edf3;--muted:#8b949e;--line:#30363d;--navy:#e6edf3;
--accent:#8b949e;--accent-soft:#161b22;--down:#8b949e;--chip:#161b22;--high:#f85149;--medium:#e6edf3;--low:#8b949e;
--red:#f85149;--green:#3fb950;
--serif:"Source Serif 4",Georgia,"Times New Roman",serif;--sans:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
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
.deal{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:28px;margin:0 0 28px}
.deal + .bridges{margin-bottom:28px}
.big small{font-size:1.2rem;color:var(--muted)}
.small{font-size:.85rem}
.bars{display:grid;gap:8px;margin:18px 0 12px}
.bar{display:grid;grid-template-columns:150px minmax(0,1fr) 44px;gap:10px;align-items:center;font-size:.85rem}
.bar i{display:block;height:8px;border-radius:4px;background:var(--red);min-width:2px}
.bar b{font-weight:600;text-align:right;font-variant-numeric:tabular-nums}
table.top{width:100%;border-collapse:collapse;font-size:.9rem}
table.top th{text-align:left;color:var(--muted);font-weight:500;font-size:.78rem;padding:6px 8px;border-bottom:1px solid var(--line)}
table.top td{padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}
table.top td span{display:block;color:var(--muted);font-size:.78rem}
table.top .n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.grid{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0}
.grid span{font-size:.75rem;padding:3px 7px;border-radius:4px;border:1px solid var(--line);font-variant-numeric:tabular-nums}
.grid .on{color:var(--ink)}.grid .off{color:var(--muted)}
details{margin-top:10px;color:var(--muted)}summary{cursor:pointer;font-size:.85rem}
.stats.three{grid-template-columns:repeat(3,minmax(0,1fr));margin:14px 0}
@media (max-width:900px){.deal{grid-template-columns:minmax(0,1fr)}}
@media (max-width:600px){.bar{grid-template-columns:110px minmax(0,1fr) 40px}.stats.three{grid-template-columns:repeat(3,minmax(0,1fr))}}
.band{display:flex;gap:24px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:16px 20px;margin-top:24px}
.band .s{font:600 3rem/1 var(--sans);color:var(--ink);white-space:nowrap}.band .s span,.score span{font-size:1rem;color:var(--muted);font-weight:400}
.band .l{font-weight:600;color:var(--ink);margin:0}
.band .c{font-size:.82rem;color:var(--muted);margin:2px 0 0}
.score{font:600 2.6rem/1 var(--sans);color:var(--ink);margin-top:14px}
.kv{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--line);padding-top:10px;margin:14px 0 8px;font-size:.9rem;color:var(--muted)}.kv b{color:var(--ink);font-variant-numeric:tabular-nums}
.action{font:600 1.5rem/1.3 var(--serif);color:var(--ink);margin:6px 0 12px}
p.action{font-size:1.05rem}
.limits{color:var(--muted);font-size:.82rem;margin-top:24px}
.issues3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.issue-card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:16px}
.issue-card .k{font-size:.8rem;color:var(--muted);margin:0 0 6px}.issue-card h3{font-size:1.1rem;margin:0 0 8px}
.issue-card .m{font-size:.8rem;color:var(--muted);margin:0}
section.tight{padding:28px 0;border-bottom:none}section.hero.tight{padding:32px 0 8px}
.grid{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}
.grid span{font-size:.75rem;padding:3px 7px;border-radius:6px;border:1px solid var(--line);color:var(--muted)}
.grid .on{color:var(--ink)}.small{font-size:.85rem}
.cases{grid-template-columns:repeat(3,minmax(0,1fr))}.case{display:block;padding:24px}
@media (max-width:900px){.issues3,.cases{grid-template-columns:minmax(0,1fr)}}
@media (max-width:600px){.band{flex-direction:column;align-items:flex-start;gap:8px}}
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
.bridges .wide{grid-column:1/-1}
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
/* Phase 6: colour with a meaning (red worse, green better, amber Medium only), the hero, verification */
:root{--amber:#d29922;--blue:#58a6ff}
.hero6{display:grid;grid-template-columns:190px minmax(0,1fr) 190px;gap:24px;align-items:center;border:1px solid;
border-radius:12px;padding:18px 22px;margin-top:20px}
.hero6 .big6{font:700 3.4rem/1 var(--sans);white-space:nowrap}.hero6 .big6 span{font-size:1rem;color:var(--muted);font-weight:400}
.hero6 .word{font-weight:600;margin:6px 0 0}.hero6 .lab{font-size:.8rem;color:var(--muted);margin:4px 0 0}.hero6 .lab b{color:var(--ink)}.hero6 .info{display:block;cursor:help;text-decoration:underline dotted}
.sbar{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--line)}
.sbar i{display:block;height:100%;border-right:2px solid var(--surface)}
.segs{display:flex;flex-wrap:wrap;gap:2px 14px;font-size:.8rem;color:var(--muted);margin-top:8px}.segs b{color:var(--ink)}
.plain6{font-size:.9rem;margin:8px 0 0;line-height:1.5}
.hero6 details{color:var(--blue);font-size:.82rem;margin-top:6px}
.hero6 .pts{display:grid;grid-template-columns:minmax(0,1fr) auto 40px;gap:2px 12px;color:var(--ink);font-size:.8rem;margin-top:6px}
.hero6 .pts span:nth-child(3n){text-align:right}.hero6 .f{color:var(--muted);font-size:.78rem;margin-top:6px}
.close6{margin-top:8px;font-size:.85rem}.close6 b{color:var(--green)}.close6 ol{margin:2px 0 0;padding-left:18px;color:var(--muted)}.close6 li span{color:var(--ink)}
.cnt6{display:flex;flex-direction:column;gap:6px}
.cnt6 span{font-size:.85rem;padding:3px 10px;border-radius:6px;border:1px solid;white-space:nowrap}
.issue-card{border-left:3px solid}
.inprice6{display:grid;grid-template-columns:minmax(0,1fr) 110px;gap:12px;align-items:center;padding:8px 14px;
border-left:3px solid var(--muted);border-radius:6px;background:#8b949e14;margin:0 0 6px}
.inprice6 .n{text-align:right;color:var(--muted);font-weight:600;white-space:nowrap}.inprice6 .why{display:block;font-size:.8rem;color:var(--muted)}
.legend6{display:flex;flex-wrap:wrap;gap:4px 18px;font-size:.8rem;color:var(--muted);margin:8px 0}
.grid .on{color:var(--ink);border-color:var(--muted)}.grid .na{opacity:.55}
.vgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
.vstat{background:var(--surface);border:1px solid var(--line);border-top:3px solid var(--muted);border-radius:10px;padding:18px}
.vstat .n{font:700 3rem/1 var(--sans);color:var(--ink);letter-spacing:-.02em}
.vstat .t{color:var(--ink);font-weight:600;margin:10px 0 6px;line-height:1.35}
.vstat code{display:block;color:var(--muted);font-size:.75rem;word-break:break-word}
.vstat .miss{font-size:.8rem;margin:4px 0 0}.vstat .miss a{color:var(--red)}
.how3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:20px}
.how3 div{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px}
.how3 b{display:block;color:var(--ink);margin-bottom:4px}.how3 p{margin:0;color:var(--muted);font-size:.88rem}
.case .sbar{margin:12px 0 4px}
@media (max-width:900px){.vgrid{grid-template-columns:1fr 1fr}.how3{grid-template-columns:1fr}
.hero6{grid-template-columns:1fr;gap:14px}.cnt6{flex-direction:row;flex-wrap:wrap}}
@media (max-width:600px){.vstat .n{font-size:2.2rem}}
"""


# ---------------------------------------------------------------- pieces
def minus(text: str) -> str:
    """A typographic minus for negative amounts (-€43m → −€43m)."""
    return text.replace("-€", "−€")


def bridges(c, a) -> dict:
    """The bridges of a company (dd_assistant/charts.py: one generator for the site, the app and the slides)."""
    from dd_assistant import charts
    return charts.all_bridges(a)


def chart(b, money) -> str:
    from dd_assistant import charts
    return charts.svg(b, money)


def downloads(slug: str) -> str:
    return '<div class="dl">' + "".join(
        f'<a href="files/{slug}/{name}" download><b>{E(label)}</b><span>{E(what)}</span></a>'
        for name, label, what in DOWNLOADS) + "</div>"


def page(title: str, description: str, body: str, path: str = "") -> str:
    from dd_assistant.charts import CSS as CHART_CSS
    url = SITE_URL + path
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0d1117">
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
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23161b22'/%3E%3Cpath d='M9 17l5 5 9-11' stroke='%233fb950' stroke-width='3.2' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<style>{CSS}{CHART_CSS}</style>
</head>
<body>
<header class="top"><div class="wrap"><a class="brand" href="index.html">{NAME}</a>
<nav><a href="index.html#cases">Cases</a><a href="index.html#verified">Verification</a><a class="cta" href="{DEMO_URL}">Open the tool</a></nav></div></header>
<main>
{body}
</main>
<footer><div class="wrap"><span>{E(NAME)} · preliminary analysis on published accounts, not an opinion.</span>
<span><a href="{{github}}">GitHub</a> · <a href="{{linkedin}}">LinkedIn</a></span></div></footer>
</body>
</html>
"""


# ---------------------------------------------------------------- pages (docs/FASE6_DESIGN.md: the site shows conclusions)
SHAPE = {"High": "▲", "Medium": "●", "Low": "○"}
SEV = {"High": "var(--red)", "Medium": "var(--amber)", "Low": "var(--muted)"}
SEV_HEX = {"High": "#f85149", "Medium": "#d29922", "Low": "#8b949e"}
TONE_HEX = {"red": "#f85149", "amber": "#d29922", "green": "#3fb950"}
TAG = {"Net debt item": "Debt-like", "To assess": "To assess", "Working capital item": "Working capital"}
GITHUB_DETECTION = "https://github.com/MItchell1970/dd-assistant/blob/main/docs/DETECTION.md"


def short_name(c) -> str:
    return c.company.split()[0]


def fmt_points(x: float) -> str:
    from dd_assistant.ai_memo import fmt_value
    return fmt_value(x)


def score_bar(s, colour: str) -> str:
    """The score split by area: one segment per area, widths in score points (they add up to the score)."""
    segs = sorted([(k, v) for k, v in s.by_area.items() if v], key=lambda x: -x[1])
    shades = ("ff", "cc", "99", "77", "55")
    return '<div class="sbar">' + "".join(f'<i style="width:{v:.1f}%;background:{colour}{shades[k % 5]}" '
                                          f'title="{E(area)}"></i>' for k, (area, v) in enumerate(segs)) + "</div>"


def hero(c, a, layer) -> str:
    """The same hero as the tool: the score in the colour of its band, where its points come from, the counts."""
    from dd_assistant import deal_layer as dl
    s, cov = layer.score, layer.coverage
    word, tone = s.band
    colour = TONE_HEX[tone]
    segs = sorted([(k, v) for k, v in s.by_area.items() if v], key=lambda x: -x[1])
    labels = "".join(f"<span>{E(k)} <b>{fmt_points(v)}</b></span>" for k, v in segs)
    pts = "".join(f"<span>{E(k)} · {E(s.titles.get(k, k))}</span><span>{E(why)}</span><span>{fmt_points(p)}</span>"
                  for k, _, why, p in s.lines)
    counts = "".join(f'<span style="color:{SEV_HEX[x]};border-color:{SEV_HEX[x]}66;background:{SEV_HEX[x]}14">'
                     f"{s.counts.get(x, 0)} {SHAPE[x]} {x}</span>" for x in SHAPE)
    counts += f'<span style="color:var(--muted);border-color:var(--line)">{len(cov.run)} / {cov.total} rules run</span>'
    return (f'<div class="hero6" style="border-color:{colour}66;background:{colour}14">'
            f'<div><div class="big6" style="color:{colour}">{s.score}<span> / 100</span></div>'
            f'<p class="word" style="color:{colour}">{E(word)}</p><p class="lab"><b>{E(s.label)}</b> · '
            f'{E(dl.SCORE_LEGEND.split(" (")[0])}<span class="info" title="{E(dl.SCORE_NOTE)}">ⓘ not a '
            f'recommendation</span></p></div>'
            f'<div>{score_bar(s, colour)}<div class="segs">{labels}</div><p class="plain6">{E(dl.SCORE_PLAIN)}</p>'
            f'{closing(s)}'
            f'<details><summary>How the score is built: every point, by issue</summary><div class="pts">{pts}'
            f'<span><b>Total</b></span><span>{fmt_points(s.points)} points ÷ 30 × 100</span><span><b>{s.score}</b>'
            f'</span></div><p class="f">{E(s.formula)}</p></details></div>'
            f'<div class="cnt6">{counts}</div></div>')


def closing(s) -> str:
    from dd_assistant import deal_layer as dl
    if not s.closers:
        return ""
    items = "".join(f"<li>{E(k)} · {E(t)} <span>−{fmt_points(p)} pts</span></li>" for k, t, p in s.closers)
    return f'<div class="close6"><b>{E(dl.closing_text(s))}</b><ol>{items}</ol></div>'


def legend() -> str:
    plain = {"High": "could change price or terms", "Medium": "answer before signing", "Low": "note it"}
    return ('<div class="legend6">' + "".join(f'<span><span style="color:{SEV[x]}">{SHAPE[x]} {x}</span> · {plain[x]}'
                                              f"</span>" for x in SHAPE)
            + "<span>Debt-like · To assess: balance sheet items, no rule fired, no severity</span></div>")


def issue_card(d, a) -> str:
    """Signature visual 3: one deal issue, its amount, the evidence state and what a deal team does about it."""
    from dd_assistant import deal_layer as dl
    colour = SEV_HEX.get(d.severity, "#8b949e")
    mark = (f'<span style="color:{SEV[d.severity]}" title="{E(d.severity)}">{SHAPE[d.severity]}</span> {E(d.key)}'
            if d.severity else E(TAG.get(d.kind, d.kind)))
    ev = "explained" if d.evidence.startswith("explained") else "partly" if d.evidence.startswith("partly") else "open"
    ev_colour = {"explained": "var(--green)", "partly": "var(--amber)", "open": "var(--red)"}[ev]
    return (f'<article class="issue-card" style="border-left-color:{colour};background:{colour}14">'
            f'<p class="k">{mark} · {E(d.area or "")}</p>'
            f'<h3>{E(dl.issue_title(d, a.money))}</h3>'
            f'<p class="m">{E(d.protection)} · <span style="color:{ev_colour}">evidence {E(d.evidence)}</span></p>'
            '</article>')


def in_price(a) -> str:
    from dd_assistant import deal_layer as dl
    items = dl.in_price(a)
    if not items:
        return ""
    return ('<p class="eyebrow" style="margin-top:28px">Already in the price · shown, not scored</p>' + "".join(
        f'<div class="inprice6"><span>{E(p.label)}<span class="why">{E(p.why)}</span></span>'
        f'<span class="n">{E(minus(a.money.fmt(p.amount)))}</span></div>' for p in items))


def coverage_grid(a, layer) -> str:
    """Signature visual 2: the rules run, blocked (with the document that unlocks each) and not applicable."""
    from dd_assistant import deal_layer as dl
    cov = layer.coverage
    marks = []
    for r in a.results:
        status, doc = cov.status(r.rule.id)
        cls = "on" if status.startswith("run") else "na" if status.startswith("not") else ""
        marks.append(f'<span class="{cls}" title="{E(r.rule.name)}'
                     f'{": " + E(doc) if doc else ""}">{E(status.split()[-1])} {r.rule.id}</span>')
    return (f'<h2 class="action">{E(dl.coverage_title(cov))}</h2><p class="muted small">{E(dl.MODE_LINE)}</p>'
            '<div class="legend6"><span>✓ run</span><span>□ blocked: a document is '
            'missing</span><span>– not applicable</span></div>'
            f'<div class="grid">{"".join(marks)}</div>')


def verification_stats() -> list[tuple[str, str, str, str]]:
    """Eight figures, each counted now by the code: (figure, what it is, the command or file that proves it, miss)."""
    from dd_assistant import demo
    v, d = demo.verification(), demo.detection()
    share = round(100 * v["sourced"] / v["lines"]) if v["lines"] else 0
    missed = d.get("scored", 0) - d.get("detected", 0)
    return [
        (str(v["tests"]), "automated tests, all passing", "python -m unittest", ""),
        (str(v["rules"]), "rules, each with its threshold, source and plain-language reason",
         "python -m dd_assistant --rules", ""),
        (f"{share}%", f"of the {v['lines']} lines read carry their source cell, page or tag", "CompanyData.sources", ""),
        (str(v["figures"]), f"memo figures checked against the material, {v['unmatched']} without a source",
         "docs/examples/*/memo_check.md", ""),
        (f"{v['checks_passed']} of {v['checks']}", "published subtotals rebuilt from the lines read",
         "tests/test_real_companies.py", ""),
        (f"{d.get('detected', 0)} of {d.get('scored', 0)}", "planted distortions detected, one at a time",
         "docs/DETECTION.md", f"{missed} missed: TAP, M18 (published)" if missed else ""),
        (str(v["clean_alarms"]), "false alarms on the clean company (Velmora)", "tests/test_clean_company.py", ""),
        (f"{v['controls_ok']} of {v['controls']}", "databook totals: Excel recalculated = Python",
         "databook Checks sheet · tests/test_databook.py", ""),
    ]


def verification_grid() -> str:
    return '<div class="vgrid">' + "".join(
        f'<div class="vstat"><div class="n">{E(n)}</div><p class="t">{E(t)}</p><code>{E(proof)}</code>'
        + (f'<p class="miss"><a href="{GITHUB_DETECTION}">{E(miss)}</a></p>' if miss else "") + "</div>"
        for n, t, proof, miss in verification_stats()) + "</div>"


def index(cases: list) -> str:
    from dd_assistant import charts, demo
    from dd_assistant import deal_layer as dl
    cards, tap = [], None
    for c, a in cases:
        layer = dl.build(a)
        b = charts.net_debt(a, company=short_name(c))
        B = a.view.bs_years[-1]
        word, tone = layer.score.band
        colour = TONE_HEX[tone]
        if c.slug == "tap":
            tap = layer.score
        cards.append(f"""<article class="case" data-check="{c.slug}" style="border-top:3px solid {colour}">
<p class="co">{E(c.company)}</p>
<p class="muted small" style="margin:10px 0 0">{E(layer.score.label)} · higher = more to clarify</p>
<div class="score" style="color:{colour};margin-top:4px">{layer.score.score}<span> / 100</span></div>
<p class="small" style="color:{colour};margin:4px 0 0">{E(word)}</p>{score_bar(layer.score, colour)}
<p class="kv"><span>Adjusted net debt, {E(fy(B))}</span><b>{E(a.money.fmt(a.view.net_debt_adjusted[B]).replace("-€", "−€"))}</b></p>
<p class="action">{E(b.title) if b else ""}</p>
<a class="more" href="{PAGES[c.slug]}">The case →</a>
</article>""")
    limits = " · ".join(demo.LIMITS)
    example = (f"TAP: {fmt_points(tap.points)} points from {len(tap.lines)} open issues of FY25 = {tap.score} / 100."
               if tap else "")
    body = f"""<section class="hero"><div class="wrap">
<p class="eyebrow">Financial due diligence · European companies · euros</p>
<h1>{NAME}</h1>
<p class="lede">{E(demo.TAGLINE)}.</p>
<p class="by">{E(demo.BUILT_BY)}.</p>
<div class="btns"><a class="btn primary" href="{DEMO_URL}">Open the tool</a><a class="btn" href="#cases">The three cases</a></div>
<p class="hint">The tool may take a few seconds to wake up.</p>
</div></section>
<section id="cases"><div class="wrap">
<p class="eyebrow">Three real companies, published accounts FY2023 to FY2025</p>
<div class="cases">{"".join(cards)}</div>
<div class="how3">
<div><b>1 · Each open issue gets points</b><p>Severity (High 3, Medium 2, Low 1) × materiality (material 1, not quantifiable 0.75, below 0.5) × evidence (open 1, partly explained by a note 0.75, explained 0.5).</p></div>
<div><b>2 · Only the latest year counts</b><p>A finding of an earlier year only is historical: kept, not scored. Items a buyer prices anyway (leases, the peg) sit apart.</p></div>
<div><b>3 · 30 points = 100</b><p>Ten open, material High findings. 0 = nothing open. A to-do meter for the diligence, not a grade for the company. {E(example)}</p></div>
</div>
</div></section>
<section id="verified"><div class="wrap">
<p class="eyebrow">How it is verified · every figure counted by the code when this page was built</p>
{verification_grid()}
<p class="limits">Limits: {E(limits)}.</p>
</div></section>"""
    return page(f"{NAME}: financial due diligence on published accounts",
                f"{demo.TAGLINE}. Three real European companies, every figure traced to its source.", body)


def company(c, a) -> str:
    from dd_assistant import charts
    from dd_assistant import deal_layer as dl
    layer = dl.build(a)
    b = charts.net_debt(a, company=short_name(c))
    top3 = "".join(issue_card(d, a) for d in layer.top[:3])
    L = a.view.pl_years[-1]
    body = f"""<section class="hero tight"><div class="wrap" data-check="{c.slug}">
<a class="back" href="index.html#cases">← All cases</a>
<p class="eyebrow">{E(a.sector.name)} · {E(c.accounts)}</p>
<h1>{E(c.company)}</h1>
{hero(c, a, layer)}
</div></section>
<section class="tight" data-check="{c.slug}"><div class="wrap">
<p class="eyebrow">Top 3 deal issues · {fy(L)}, by amount at stake</p>
{legend()}
<div class="issues3">{top3}</div>
{in_price(a)}
</div></section>
<section class="tight" data-check="{c.slug}"><div class="wrap">
{charts.svg(b, a.money) if b else ""}
</div></section>
<section class="tight" data-check="{c.slug}"><div class="wrap">
{coverage_grid(a, layer)}
<div class="btns"><a class="btn primary" href="{DEMO_URL}/?company={c.slug}">Open {E(short_name(c))} in the tool</a></div>
<p class="hint">Findings with their evidence, the valuation impact, open items and downloads are in the tool.</p>
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
