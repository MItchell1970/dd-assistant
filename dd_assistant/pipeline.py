"""The whole analysis in one call: what the app, the command line and the Claude skill run.

read (extract or the data room) → reviewer's corrections → country, metrics and reading checks →
rules calibrated for the sector → deal view → sector benchmarks. No AI: every number is deterministic
and traceable. The purpose (M&A buy-side by default) only frames how the memo is written.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from . import europe, sectors
from .deal import DealView, benchmark_rows, deal_view
from .extract import Extraction, apply_edits
from .input_loader import CompanyData, Named
from .metrics import ALL_LABELS, Metrics, compute_metrics, reading_checks
from .rules import RuleResult, alerts, evaluate, fy
from .units import Money

# Why the review is done: the focus is M&A, but the same analysis serves a lender or an owner.
PURPOSES = {"buy": "M&A — buy-side due diligence", "sell": "M&A — vendor due diligence (sell-side)",
            "lend": "Lending — credit review", "review": "Financial health check (no transaction)"}


@dataclass
class Analysis:
    ext: Extraction
    data: CompanyData
    metrics: Metrics
    results: list[RuleResult]
    findings: list[RuleResult]
    checks: list[dict]
    view: DealView
    sector: sectors.Sector
    suggested: sectors.Sector
    suggested_from: list[str]
    money: Money
    benchmarks: list[dict]
    decisions: dict[str, str] = field(default_factory=dict)
    country: europe.Country | None = None
    country_suggested: europe.Country | None = None
    country_why: str = ""
    purpose: str = "buy"

    @property
    def checks_ok(self) -> bool:
        return all(c["OK"] for c in self.checks)


def analyse(ext: Extraction, sector: str | sectors.Sector | None = None, country: str | None = None,
            edits: dict[str, dict[int, float | None]] | None = None, documents: list[tuple[str, bool]] | None = None,
            decisions: dict[str, str] | None = None, analyst: list[Named] | None = None,
            include: dict[int, bool] | None = None, purpose: str = "buy") -> Analysis:
    """sector, country: None = the ones suggested from the data room. The reviewer's inputs: corrected figures
    (edits), documents received, decisions on management adjustments, own adjustments and net debt items to
    include."""
    if purpose not in PURPOSES:
        raise ValueError(f"Unknown purpose '{purpose}'. Options: {', '.join(PURPOSES)}")
    suggested, words = sectors.suggest(ext.source_text, ext.company)
    s = sectors.get(sector) if sector else suggested
    c_suggested, c_why = europe.suggest(ext.source_text, ext.company)
    if country and not europe.get(country):
        raise ValueError(f"Unknown country '{country}'. Options: {', '.join(europe.COUNTRY_BY_CODE)}")
    c = europe.get(country) if country else c_suggested
    data = apply_edits(ext.data, edits) if edits else ext.data
    if documents is not None:
        data = replace(data, documents=documents)
    data = replace(data, country=c.code if c else data.country)
    c = europe.get(data.country)
    m = compute_metrics(data)
    results = evaluate(data, m, sector=s)
    view = deal_view(data, m, decisions, analyst, include)
    return Analysis(ext, data, m, results, alerts(results), reading_checks(data), view, s, suggested, words,
                    Money.for_data(data), benchmark_rows(data, m, view, s), dict(decisions or {}), c, c_suggested,
                    c_why, purpose)


def to_dict(a: Analysis) -> dict:
    """Everything the analysis found, as plain data (JSON for the Claude skill). Amounts in thousands."""
    years = lambda values: {fy(y): v for y, v in sorted(values.items())}
    lines = lambda block: [{"label": l.label, "style": l.style, "unit": l.unit, "values": years(l.values),
                            "source": l.source, "note": l.note} for l in block]
    d = a.data
    return {
        "company": a.ext.company,
        "read_with": a.ext.method,
        "amounts": f"{d.currency} thousands (shown in the app as {a.money.unit})",
        "income_statement_format": d.pl_format,
        "purpose": PURPOSES[a.purpose],
        "country": {"code": d.country, "name": a.country.name if a.country else "not set",
                    "framework": a.country.framework if a.country else "",
                    "statutory_tax_rate": a.country.tax_rate if a.country else None,
                    "suggested_from": a.country_why},
        "years": [fy(y) for y in d.years],
        "sector": {"key": a.sector.key, "name": a.sector.name, "suggested": a.suggested.key,
                   "suggested_from": a.suggested_from,
                   "peers": f"{a.sector.benchmarks['industry']} — {sectors.BENCHMARK_SOURCE}"},
        "reading_checks": [{**c, "Year": fy(c["Year"])} for c in a.checks],
        "reading_checks_ok": a.checks_ok,
        "lines_not_found": a.ext.missing,
        "lines_not_used": a.ext.unmapped,
        "findings": [{"id": r.rule.id, "name": r.rule.name, "plain_words": r.rule.plain, "area": r.rule.area,
                      "severity": r.rule.severity,
                      "years": r.years_text, "evidence": r.evidence, "test": r.rule.test,
                      "threshold": r.rule.limit_text(), "calibration": r.rule.calibration,
                      "what_to_investigate": r.rule.focus, "question": r.rule.question, "request": r.rule.request}
                     for r in a.findings],
        "near_misses": [{"id": r.rule.id, "name": r.rule.name, "threshold": r.rule.limit_text(),
                         "values": {fy(y): v for y, v in r.values.items()}} for r in a.results if not r.alert
                        and any(isinstance(v, (int, float)) for v in r.values.values())],
        "deal_view": {"quality_of_earnings": lines(a.view.qoe), "net_debt": lines(a.view.net_debt),
                      "net_working_capital": lines(a.view.nwc)},
        "management_adjustments": [{"name": x.name, "values": years(x.values),
                                    "status": a.decisions.get(x.name, "Under review")} for x in d.adjustments],
        "balance_sheet_items": [{"category": b.category, "label": b.label, "nature": b.nature, "kind": b.kind,
                                 "included": b.include, "values": years(b.values), "source": b.source}
                                for b in d.balance_items],
        "benchmarks": [{k: v for k, v in b.items() if k != "key"} for b in a.benchmarks],
        "sector_lens": [{"area": i.area, "question": i.question, "request": i.request} for i in a.sector.lens],
        "documents_received": dict(d.documents),
        "metrics": {ALL_LABELS[k]: years(v) for k, v in a.metrics.items() if v},
    }
