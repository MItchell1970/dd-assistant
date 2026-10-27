"""Command line.

Usage:
    python -m dd_assistant data/Duriva_data_room.xlsx              # red flags from the company's own financials
    python -m dd_assistant data/Duriva_data_room.xlsx --memo       # ... plus the AI memo (Claude API)
    python -m dd_assistant data/Duriva_data_room.xlsx --check-memo memo.md
    python -m dd_assistant data/DD_template_modulo1.xlsx --data-room data/Duriva_data_room.xlsx --memo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .extract import ExtractionError, data_room_text, read_financials
from .metrics import compute_metrics
from .report import summary, write_csv, write_excel
from .rules import alerts, evaluate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Due Diligence Assistant — red flags from a company's financial statements.")
    p.add_argument("financials", help="The company's financial statements (Excel or PDF), or a completed DD template")
    p.add_argument("--out", default="output", help="Folder for the results (default: output)")
    p.add_argument("--memo", action="store_true", help="Also write the memo and request list with the Claude API")
    p.add_argument("--data-room", help="Data room (Excel) for the memo when the input is a DD template")
    p.add_argument("--check-memo", metavar="MEMO", help="Check a memo already written (e.g. in claude.ai)")
    args = p.parse_args(argv)

    path = Path(args.financials)
    for f in [path] + [Path(x) for x in (args.data_room, args.check_memo) if x]:
        if not f.exists():
            print(f"File not found: {f}", file=sys.stderr)
            return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # correct characters in the Windows console

    if path.suffix.lower() == ".pdf":
        from .ai_memo import load_env
        load_env()   # reading a PDF uses the Claude API
    try:
        with open(path, "rb") as fh:
            ext = read_financials(fh, path.name)
    except ExtractionError as e:
        print(str(e), file=sys.stderr)
        return 1
    data = ext.data
    metrics = compute_metrics(data)
    results = evaluate(data, metrics)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    write_excel(results, metrics, data.years, out / f"{stem}_red_flags.xlsx", items=ext.items)
    write_csv(results, out / f"{stem}_red_flags.csv")

    print(f"{ext.company} · read with: {ext.method}")
    if ext.missing:
        print(f"Line items not found: {', '.join(ext.missing)}")
    print(summary(results))
    print(f"\nResults saved to: {out.resolve()}")

    source_text = data_room_text(args.data_room) if args.data_room else ext.source_text
    rc = _memo(data, metrics, results, source_text, out, path) if args.memo else 0
    if args.check_memo:
        rc = max(rc, _check(data, metrics, results, source_text, Path(args.check_memo), out, path))
    return rc


def _verify(memo_text: str, material: str, results, report_file: Path) -> bool:
    """Run the checker, print the result and save it next to the memo."""
    from .memo_check import check_memo, report

    check = check_memo(memo_text, material, [r.rule.id for r in alerts(results)])
    text = report(check)
    report_file.write_text(text + "\n", encoding="utf-8")
    print(f"\n{text}\nCheck saved to: {report_file.resolve()}")
    return check.ok


def _check(data, metrics, results, source_text, memo_path: Path, out: Path, financials: Path) -> int:
    """Check a memo already written against the material the program would send to the AI."""
    from .ai_memo import build_material

    material = build_material(data, metrics, results, source_text, name=financials.name)
    ok = _verify(memo_path.read_text(encoding="utf-8"), material, results, out / f"{memo_path.stem}_check.md")
    return 0 if ok else 1


def _memo(data, metrics, results, source_text, out: Path, financials: Path) -> int:
    """Layer 5: send the material to the Claude API and save the memo (and the material, for audit)."""
    import anthropic   # only needed for the memo
    from .ai_memo import MODEL, MemoError, build_material, load_env, write_memo

    material = build_material(data, metrics, results, source_text, name=financials.name)
    material_file = out / f"{financials.stem}_ai_material.md"
    material_file.write_text(material, encoding="utf-8")
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
    print(f"Material sent to the AI: {material_file.resolve()}")
    print(f"{memo.model} · {memo.input_tokens:,} input tokens, {memo.output_tokens:,} output tokens "
          f"· estimated cost ≈ USD {memo.cost_usd:.2f}")
    if memo.truncated:
        print("Warning: the answer stopped at the token limit and may be incomplete.", file=sys.stderr)
    _verify(memo.text, material, results, out / f"{financials.stem}_memo_check.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
