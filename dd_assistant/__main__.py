"""Command line.

Usage:
    python -m dd_assistant data/Duriva_data_room.xlsx              # red flags and deal view, saved to output/
    python -m dd_assistant data/Duriva_data_room                   # a whole data room folder (Excel, PDF, Word)
    python -m dd_assistant data/Corticeira_Amorim_2024_published.xlsx --sector materials
    python -m dd_assistant data/Duriva_data_room.xlsx --adjustment "Custos de arranque=Accepted" --json
    python -m dd_assistant data/Duriva_data_room.xlsx --material   # the material for the AI memo (free)
    python -m dd_assistant data/Duriva_data_room.xlsx --memo       # ... plus the AI memo (Claude API)
    python -m dd_assistant data/Duriva_data_room.xlsx --check-memo memo.md
    python -m dd_assistant data/Duriva_data_room.xlsx --purpose lend    # a credit review instead of M&A
    python -m dd_assistant --sectors                               # the sectors and their calibrated thresholds
    python -m dd_assistant --rules                                 # the rulebook, in plain words
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import europe, sectors
from .deal import ADJUSTMENT_STATES
from .dataroom import NeedsPdfReading, files_in, read_data_room
from .extract import FIELD_BY_KEY, ExtractionError, data_room_text
from .pipeline import PURPOSES, Analysis, analyse, to_dict
from .report import summary, write_csv, write_excel
from .rules import RULES, fy


def _edits(values: list[str]) -> dict[str, dict[int, float]]:
    """'orend:2025=60' or 'orend:FY25=60' -> {'orend': {2025: 60.0}} (amounts in thousands)."""
    out: dict[str, dict[int, float]] = {}
    for item in values:
        m = re.fullmatch(r"(\w+):(?:FY)?(\d{2}|\d{4})=(-?[\d.]+)", item.strip(), re.I)
        if not m or m.group(1) not in FIELD_BY_KEY:
            raise ValueError(f"--set {item!r}: use KEY:YEAR=VALUE with a key from the review table (e.g. orend:2025=60)")
        year = int(m.group(2)) + (2000 if len(m.group(2)) == 2 else 0)
        out.setdefault(m.group(1), {})[year] = float(m.group(3))
    return out


def _decisions(values: list[str], names: list[str]) -> dict[str, str]:
    """'Custos de arranque=Accepted' -> {'Custos de arranque das novas instalações': 'Accepted'} (name prefix)."""
    out = {}
    for item in values:
        label, _, status = item.rpartition("=")
        status = next((s for s in ADJUSTMENT_STATES if s.lower() == status.strip().lower()), None)
        match = [n for n in names if n.lower().startswith(label.strip().lower())]
        if not status or len(match) != 1:
            raise ValueError(f"--adjustment {item!r}: use NAME=Accepted|Rejected|Under review with a name that "
                             f"matches one adjustment: {', '.join(names) or 'none presented'}")
        out[match[0]] = status
    return out


def _print_sectors() -> None:
    for s in sectors.SECTORS:
        cal = "; ".join(f"{rid} → {lim:g}" for rid, (lim, _) in s.calibration.items()) or "general thresholds"
        print(f"{s.key:<16} {s.name:<38} {cal}")


def _print_rules() -> None:
    for r in RULES:
        print(f"{r.id} · {r.name} [{r.area}; {r.severity}; threshold {r.limit_text()}]"
              f"{'' if r.in_template else ' — beyond the template'}\n  {r.plain}\n  Practice: {r.practice}\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Due Diligence Assistant — red flags and deal view from a company's "
                                            "financial statements.")
    p.add_argument("financials", nargs="*", help="The data room: files or folders (Excel, PDF, Word, text, an ESEF "
                                                 "report package .zip), or a completed DD template")
    p.add_argument("--read-pdf", metavar="PDF", help="Read the financial statements from this PDF with Claude (paid), "
                                                     "when the data room has no Excel statements")
    p.add_argument("--out", default="output", help="Folder for the results (default: output)")
    p.add_argument("--sector", choices=list(sectors.SECTOR_BY_KEY), help="Sector (default: suggested from the file)")
    p.add_argument("--country", choices=list(europe.COUNTRY_BY_CODE),
                   help="Country of the target (default: suggested from the legal form and the language)")
    p.add_argument("--purpose", choices=list(PURPOSES), default="buy",
                   help="buy (M&A buy-side, default), sell (vendor due diligence), lend (credit review), "
                        "review (health check, no transaction)")
    p.add_argument("--set", action="append", default=[], metavar="KEY:YEAR=VALUE",
                   help="Correct a figure read from the file, in thousands (repeatable)")
    p.add_argument("--adjustment", action="append", default=[], metavar="NAME=STATUS",
                   help="Decision on a management adjustment: Accepted, Rejected or Under review (repeatable)")
    p.add_argument("--received", action="append", default=[], metavar="DOCUMENT",
                   help="A key document received outside the file, e.g. 'AR ageing' (repeatable)")
    p.add_argument("--json", action="store_true", help="Also save the whole analysis as JSON (for the Claude skill)")
    p.add_argument("--material", action="store_true", help="Also save the material for the AI memo (no API call)")
    p.add_argument("--memo", action="store_true", help="Also write the memo and request list with the Claude API")
    p.add_argument("--data-room", help="Data room (Excel) for the memo when the input is a DD template")
    p.add_argument("--check-memo", metavar="MEMO", help="Check a memo already written (e.g. in claude.ai)")
    p.add_argument("--sectors", action="store_true", help="List the sectors and their calibrated thresholds")
    p.add_argument("--rules", action="store_true", help="Print the rulebook in plain words")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # correct characters in the Windows console
    if args.sectors or args.rules:
        _print_sectors() if args.sectors else _print_rules()
        return 0
    if not args.financials:
        p.error("the data room is required: one or more files, or a folder")

    paths = [Path(x) for x in args.financials]
    for f in paths + [Path(x) for x in (args.data_room, args.check_memo) if x]:
        if not f.exists():
            print(f"File not found: {f}", file=sys.stderr)
            return 1
    path = paths[0] if len(paths) == 1 else Path(paths[0].parent.name or "data_room")   # names the outputs
    if args.read_pdf:
        from .ai_memo import load_env
        load_env()   # reading a PDF's statements uses the Claude API
    try:
        ext = read_data_room(files_in(paths), read_pdf=args.read_pdf)
        if args.data_room:
            ext.source_text = data_room_text(args.data_room)
        docs = [(name, ok or any(name.lower().startswith(r.lower()) for r in args.received))
                for name, ok in ext.data.documents]
        a = analyse(ext, args.sector, args.country, _edits(args.set), docs,
                    _decisions(args.adjustment, [x.name for x in ext.data.adjustments]), purpose=args.purpose)
    except NeedsPdfReading as e:
        print(f"{e} Run again with --read-pdf \"{e.pdfs[0]}\" (uses the Claude API).", file=sys.stderr)
        return 1
    except (ExtractionError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    write_excel(a.results, a.metrics, a.data.years, out / f"{stem}_red_flags.xlsx", items=ext.items, analysis=a)
    write_csv(a.results, out / f"{stem}_red_flags.csv")
    _print(a)
    if args.json:
        (out / f"{stem}_analysis.json").write_text(json.dumps(to_dict(a), indent=1, ensure_ascii=False, default=str),
                                                   encoding="utf-8")
    if args.material or args.memo or args.check_memo:
        _material(a, out, path)
    print(f"\nResults saved to: {out.resolve()}")

    rc = _memo(a, out, path) if args.memo else 0
    if args.check_memo:
        rc = max(rc, _check(a, Path(args.check_memo), out, path))
    return rc


def _print(a: Analysis) -> None:
    m, v, L = a.money, a.view, a.view.pl_years[-1]
    B = v.bs_years[-1]
    print(f"{a.ext.company} · read with: {a.ext.method}")
    how = f"suggested from: {', '.join(a.suggested_from)}" if a.sector is a.suggested and a.suggested_from else \
        "chosen" if a.sector is not a.suggested else "no keyword found"
    print(f"Sector: {a.sector.name} ({how}; change with --sector, list with --sectors)")
    print(f"Country: {a.country.name + ' — ' + a.country.framework if a.country else 'not set'}"
          + (f" (from {a.country_why})" if a.country and a.country is a.country_suggested and a.country_why else "")
          + f" · Purpose: {PURPOSES[a.purpose]}")
    if a.ext.missing:
        print(f"Line items not found: {', '.join(a.ext.missing)}")
    failed = [c for c in a.checks if not c["OK"]]
    print(f"Reading checks: {len(a.checks) - len(failed)} of {len(a.checks)} passed"
          + "".join(f"\n  NOT OK: {c['Check']} {fy(c['Year'])} (difference {m.fmt(c['Difference'])})" for c in failed))
    print()
    print(summary(a.results))
    print(f"\nDeal view ({fy(L)}): reported EBITDA {m.fmt(v.ebitda[L])}"
          + (f" · management-adjusted {m.fmt(v.ebitda_mgmt[L])}" if v.ebitda_mgmt else "")
          + f" · diligence-adjusted {m.fmt(v.ebitda_dd[L])}")
    print(f"Net debt ({fy(B)}): reported {m.fmt(v.net_debt_reported[B])} · adjusted {m.fmt(v.net_debt_adjusted[B])}"
          f" · NWC {m.fmt(v.nwc_values[B])}" + (f" (average of the year-ends {m.fmt(v.nwc_average)})"
                                                if len(v.bs_years) > 1 else ""))


def _material(a: Analysis, out: Path, financials: Path) -> Path:
    from .ai_memo import build_material

    material = build_material(a.data, a.metrics, a.results, a.ext.source_text, name=financials.name, analysis=a)
    f = out / f"{financials.stem}_ai_material.md"
    f.write_text(material, encoding="utf-8")
    print(f"Material for the AI memo: {f.resolve()}")
    return f


def _verify(memo_text: str, material: str, a: Analysis, report_file: Path) -> bool:
    """Run the checker, print the result and save it next to the memo."""
    from .memo_check import check_memo, report

    check = check_memo(memo_text, material, [r.rule.id for r in a.findings])
    text = report(check)
    report_file.write_text(text + "\n", encoding="utf-8")
    print(f"\n{text}\nCheck saved to: {report_file.resolve()}")
    return check.ok


def _check(a: Analysis, memo_path: Path, out: Path, financials: Path) -> int:
    """Check a memo already written against the material the program would send to the AI."""
    material = (out / f"{financials.stem}_ai_material.md").read_text(encoding="utf-8")
    ok = _verify(memo_path.read_text(encoding="utf-8"), material, a, out / f"{memo_path.stem}_check.md")
    return 0 if ok else 1


def _memo(a: Analysis, out: Path, financials: Path) -> int:
    """Layer 5: send the material to the Claude API and save the memo (the material is saved for audit)."""
    import anthropic   # only needed for the memo
    from .ai_memo import MODEL, MemoError, load_env, write_memo

    material = (out / f"{financials.stem}_ai_material.md").read_text(encoding="utf-8")
    load_env()
    print(f"\nWriting the memo with {MODEL} (this can take a few minutes; the model thinks first)...\n")
    try:
        memo = write_memo(material, on_text=lambda t: print(t, end="", flush=True))
    except anthropic.AuthenticationError:
        print("\nThe Claude API key is invalid. Check ANTHROPIC_API_KEY in the .env file.", file=sys.stderr)
        return 1
    except anthropic.RateLimitError:
        print("\nRate limit reached. Wait a minute and try again.", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as e:
        print(f"\nClaude API error ({e.status_code}): {e.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("\nCannot reach the Claude API. Check the internet connection.", file=sys.stderr)
        return 1
    except MemoError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1
    except anthropic.AnthropicError as e:
        print(f"\nCould not call the Claude API: {e}", file=sys.stderr)
        return 1

    memo_file = out / f"{financials.stem}_memo.md"
    memo_file.write_text(memo.text, encoding="utf-8")
    print(f"\n\nMemo saved to: {memo_file.resolve()}")
    print(f"{memo.model} · {memo.input_tokens:,} input tokens, {memo.output_tokens:,} output tokens "
          f"· estimated cost ≈ USD {memo.cost_usd:.2f}")
    if memo.truncated:
        print("Warning: the answer stopped at the token limit and may be incomplete.", file=sys.stderr)
    _verify(memo.text, material, a, out / f"{financials.stem}_memo_check.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
