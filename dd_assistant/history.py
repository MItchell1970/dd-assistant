"""Three years from two annual reports, and the restatements between them.

An annual report gives two years. A financial due diligence works on three, so the prior year's report is added:
its earlier year (FY23) joins the two years of the latest report (FY24, FY25).

Both reports give the middle year: once as first published, once as the comparative of the following report. They
are compared line by line. The policy is fixed and visible: **the latest report's comparative is used**, never a
silent mix; a difference above the tolerance is recorded as a restatement, with both sources (rule R30).
"""
from __future__ import annotations

from dataclasses import replace

from .extract import FIELDS, Extraction
from .input_loader import BalanceItem, CompanyData, Named

TOLERANCE = 1.0      # EUR thousands: rounding of the source
POLICY = "the comparative of the latest report is used; the figure as first published is shown next to it"
_LABEL = {f.key: f.label for f in FIELDS}


def _derived(source: str) -> bool:
    """A line computed as a total less the lines identified: it follows the detail of each file, not the accounts."""
    return "less the lines identified" in (source or "")


def restatements(latest: CompanyData, prior: CompanyData, tolerance: float = TOLERANCE) -> list[dict]:
    """Lines read directly in both reports whose value for the same year differs by more than the tolerance."""
    out = []
    for year in sorted(set(latest.years) & set(prior.years)):
        for key in latest.lines:
            new, old = latest.v(key, year), prior.v(key, year)
            if new is None or old is None or abs(new - old) <= tolerance:
                continue
            if _derived(latest.sources.get(key, "")) or _derived(prior.sources.get(key, "")):
                continue
            out.append({"key": key, "line": _LABEL.get(key, key), "year": year, "as_first_published": old,
                        "as_restated": new, "difference": new - old, "source_first": prior.sources.get(key, ""),
                        "source_latest": latest.sources.get(key, "")})
    return sorted(out, key=lambda r: -abs(r["difference"]))


def _merge_named(latest: list[Named], prior: list[Named], years: list[int]) -> list[Named]:
    old = {n.name: n for n in prior}
    out = [Named(n.name, {**{y: old[n.name].values.get(y) for y in years if n.name in old}, **n.values})
           for n in latest]
    return out + [Named(n.name, {y: n.values.get(y) for y in years}) for n in prior
                  if n.name not in {x.name for x in latest} and any(n.values.get(y) for y in years)]


def _merge_items(latest: list[BalanceItem], prior: list[BalanceItem], years: list[int], tag) -> list[BalanceItem]:
    """Debt-like and cash-like items: the earlier year joins the same category and section when each report has
    exactly one such line; otherwise the prior line is kept on its own, so the earlier year never loses an item."""
    key = lambda b: (b.category, b.kind, b.nature)
    used: set[int] = set()
    out = []
    for b in latest:
        same = [o for o in prior if key(o) == key(b) and id(o) not in used]
        named = [o for o in same if o.label.strip().lower() == b.label.strip().lower()]
        alone = len([x for x in latest if key(x) == key(b)]) == 1 and len(same) == 1
        match = named[0] if named else same[0] if alone else None
        if match is not None:
            used.add(id(match))
            b = replace(b, values={**{y: match.values.get(y) for y in years}, **b.values})
        out.append(b)
    return out + [replace(b, values={y: b.values.get(y) for y in years}, source=tag(b.source)) for b in prior
                  if id(b) not in used and any(b.values.get(y) for y in years)]


def add_prior_report(latest: Extraction, prior: Extraction, prior_name: str = "prior report") -> Extraction:
    """The latest report with the earlier years of the prior one. Overlapping years keep the latest figures."""
    new, old = latest.data, prior.data
    if new.currency != old.currency:
        raise ValueError(f"The two reports are in different currencies ({new.currency}, {old.currency}).")
    extra = [y for y in old.years if y < min(new.years)]
    if not extra:
        return latest
    tag = lambda s: f"{prior_name} › {s}" if s else prior_name
    lines = {k: dict(v) for k, v in new.lines.items()}
    sources = dict(new.sources)
    prior_sources = {}
    for key, values in old.lines.items():
        got = {y: values.get(y) for y in extra if values.get(y) is not None}
        if not got:
            continue
        lines.setdefault(key, {}).update(got)
        prior_sources[key] = tag(old.sources.get(key, ""))
        sources.setdefault(key, prior_sources[key])
    data = replace(new, years=sorted(extra + new.years), lines=lines, sources=sources,
                   clients=_merge_named(new.clients, old.clients, extra),
                   adjustments=_merge_named(new.adjustments, old.adjustments, extra),
                   other_clients={**{y: old.other_clients.get(y) for y in extra if y in old.other_clients},
                                  **new.other_clients},
                   balance_items=_merge_items(new.balance_items, old.balance_items, extra, tag),
                   prior_sources=prior_sources, prior_report=prior_name, prior_years=extra,
                   restatements=restatements(new, old), overlap_years=sorted(set(new.years) & set(old.years)))
    old_items = {row["key"]: row for row in prior.items}
    cols = [f"FY{str(y)[2:]}" for y in extra]
    items = [{**{k: v for k, v in row.items() if not k.startswith("FY")},
              **{c: old_items.get(row["key"], {}).get(c) for c in cols},
              **{k: v for k, v in row.items() if k.startswith("FY")}} for row in latest.items]
    text = (f"{latest.source_text}\n\n## Prior report '{prior_name}' (earlier years: "
            f"{', '.join('FY' + str(y)[2:] for y in extra)}; for the years both reports give, {POLICY})\n"
            f"{prior.source_text}")
    files = latest.files + [{**f, "File": f"{f.get('File', prior_name)} (prior report)"} for f in prior.files]
    return replace(latest, data=data, items=items, source_text=text, files=files,
                   method=latest.method + f"; earlier years from the prior report ({prior_name})")
