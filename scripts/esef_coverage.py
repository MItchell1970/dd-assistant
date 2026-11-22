"""Listed companies found by name and analysed from their ESEF report: docs/examples/esef_coverage.md.

Uses the internet (GLEIF, filings.xbrl.org) and downloads each company's latest report package: run it only with
Bernardo's OK. --fresh downloads into a new temporary folder, so the times include the download.

    python scripts\\esef_coverage.py --fresh
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dd_assistant import registry  # noqa: E402
from dd_assistant.dataroom import read_data_room  # noqa: E402
from dd_assistant.deal_layer import coverage  # noqa: E402
from dd_assistant.esef_quality import not_analysed  # noqa: E402
from dd_assistant.extract import ExtractionError  # noqa: E402
from dd_assistant.pipeline import analyse  # noqa: E402
from dd_assistant.rules import fy  # noqa: E402

# (name typed, sector a reviewer would choose, why it is in the list)
COMPANIES = [
    ("Jeronimo Martins", "consumer_retail", "retail, Portugal"),
    ("Schneider Electric", "manufacturing", "industrial, France"),
    ("Iberdrola", "energy", "energy, Spain"),
    ("Siemens Aktiengesellschaft", "manufacturing", "industrial, Germany: is it on filings.xbrl.org?"),
]
OUT = ROOT / "docs" / "examples" / "esef_coverage.md"
# what the first run (22 November 2026, before the reader was fixed) found: kept, so the fixes stay visible
FIRST_RUN = [
    "## First run, before the fixes",
    "",
    "- **Jerónimo Martins:** *Reading check failed*: operating profit off by €1m. The report is in EUR millions and "
    "the check allowed half a thousand per line. Fixed in the check: when every line is a whole million, the "
    "rounding allowed is half a million per line (the same rule as for thousands). The company name was also missing: "
    "its tag sits inside a note, and is now found by the opening tag.",
    "- **Schneider Electric:** *Not analysed*: no income statement or balance sheet found. Its taxonomy files use the "
    "linkbase as default namespace (no `link:` prefix). Fixed: prefixes are read from the namespaces. Then the "
    "balance sheet came in two parts (assets; equity and liabilities) and only the first was read; D&A were in two "
    "company concepts named exactly like IFRS ones; restructuring and goodwill impairment sat between EBITA and "
    "operating profit. Fixed in general, not for this company: the second part completes the first, a concept named "
    "like an IFRS one is read as it, both lines go to 'other expenses (incl. write-downs)'. Before the D&A fix the "
    "checks passed with EBITDA equal to operating profit: the quality warning now fails when no D&A is found.",
    "- **Iberdrola:** *Not analysed*: the package is a `.xbri` (XBRL Report Package 1.0), not a `.zip`. Fixed. Then "
    "*Reading check failed* (operating profit off by €8,416m): its own cost concepts are defined as credits "
    "(`xbrli:balance=\"credit\"`), so costs came with the sign of a gain. Fixed: the balance of the company's own "
    "concepts is read from its schema; two IFRS concepts (taxes other than income tax, other gains and losses) and "
    "two Spanish labels were added to the dictionary.",
    "- **Siemens:** not on filings.xbrl.org (German issuers file with the Bundesanzeiger). Not fixable here.",
    "",
]


def run(name: str, sector: str, cache: Path) -> dict:
    row = {"query": name, "sector": sector}
    t0 = time.perf_counter()
    try:
        found = registry.search(name)
    except registry.RegistryError as e:
        return {**row, "quality": not_analysed(str(e)).text(), "search": time.perf_counter() - t0}
    row["search"] = time.perf_counter() - t0
    if not found:
        return {**row, "quality": not_analysed(f"No company matching '{name}' has an ESEF report on "
                                               "filings.xbrl.org.").text()}
    f = found[0].filings[0]
    row.update(company=found[0].name, lei=f.lei, year=f.year, country=f.country,
               size=f"{f.size / 1024 ** 2:,.1f} MB" if f.size else "?", url=f.url)
    t1 = time.perf_counter()
    try:
        got = registry.download(f, cache=cache)
    except registry.RegistryError as e:
        return {**row, "quality": not_analysed(str(e)).text(), "download": time.perf_counter() - t1}
    row.update(download=time.perf_counter() - t1, sha=got.note)
    t2 = time.perf_counter()
    try:
        ext = read_data_room([(got.path.name, got.path.read_bytes())])
        a = analyse(ext, sector)
    except ExtractionError as e:
        return {**row, "quality": not_analysed(str(e)).text(), "analysis": time.perf_counter() - t2}
    row["analysis"] = time.perf_counter() - t2
    v, L, B = a.view, a.data.pl_years[-1], a.view.bs_years[-1]
    row.update(quality=a.quality.text(), rules=coverage(a).text, suggested=a.suggested.name,
               checks=f"{sum(c['OK'] for c in a.checks)} of {len(a.checks)}",
               findings=", ".join(f"{r.rule.id} {r.rule.severity}" for r in a.findings) or "none",
               missing=", ".join(m for m in a.ext.missing if not m.startswith(("Debt schedule", "Covenant"))) or "—",
               ebitda=a.money.fmt(v.ebitda[L]), net_debt=a.money.fmt(v.net_debt_adjusted[B]), fy=fy(L))
    return row


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fresh", action="store_true", help="download into a new temporary folder (times include it)")
    args = p.parse_args()
    cache = Path(tempfile.mkdtemp()) if args.fresh else registry.CACHE
    rows = []
    for name, sector, why in COMPANIES:
        print(f"{name}...", flush=True)
        rows.append({**run(name, sector, cache), "why": why})
        time.sleep(2)                                  # filings.xbrl.org limits the requests per minute
    stamp = time.strftime("%d %B %Y")
    lines = [
        "# ESEF coverage: listed companies found by name",
        "",
        f"Generated by `scripts/esef_coverage.py{' --fresh' if args.fresh else ''}` on {stamp}. Each company was "
        "searched by the name typed (GLEIF gives the LEI, filings.xbrl.org the reports), its most recent ESEF report "
        "package downloaded and analysed with the sector a reviewer would choose. No Claude API call. A company that "
        "could not be analysed stays in the table with the reason.",
        "",
        "| Typed | Company · LEI | Report | ESEF data quality | Rules | Reading checks | Findings | Time (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        times = " · ".join(f"{k} {r[k]:.1f}" for k in ("search", "download", "analysis") if k in r)
        total = sum(r.get(k, 0) for k in ("search", "download", "analysis"))
        report = (f"FY{r['year']}, filed in {r['country']}, {r['size']}" if "year" in r else "—")
        lines.append(f"| {r['query']} ({r['why']}) | {r.get('company', '—')} · {r.get('lei', '—')} | {report} | "
                     f"{r['quality'].removeprefix('ESEF data quality: ')} | {r.get('rules', '—')} | "
                     f"{r.get('checks', '—')} | {r.get('findings', '—')} | {times} · **total {total:.1f}** |")
    lines += ["", "## Detail", ""]
    tail = FIRST_RUN
    for r in rows:
        if "ebitda" not in r:
            continue
        lines += [f"**{r['company']}** ({r['fy']}): EBITDA {r['ebitda']}, adjusted net debt {r['net_debt']}. "
                  f"Sector chosen: `{r['sector']}` (suggested by the engine: {r['suggested']}). Lines not found: "
                  f"{r['missing']}. Package: {r['url']} ({r['sha']}).", ""]
    OUT.write_text("\n".join(lines + tail) + "\n", encoding="utf-8")
    print(f"Written: {OUT}")


if __name__ == "__main__":
    main()
