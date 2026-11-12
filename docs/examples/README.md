# Examples

## The demo companies, FY2025

The online demo (`DD_DEMO=1`) reads these folders. Each holds what Claude Code produced with the `due-diligence` skill on the published consolidated accounts, with no API key:

| Folder | Company | Memo check |
| --- | --- | --- |
| `tap/` | TAP Air Portugal | passed: 142 figures, none without a source, no warning |
| `toyota-caetano/` | Toyota Caetano Portugal | passed: 134 figures, none without a source, no warning |
| `corticeira-amorim/` | Corticeira Amorim | passed: 139 figures, none without a source, no warning |

In each folder:

- `memo.md`: the two-page memo, the request list and the notes to improve the template;
- `memo_check.md`: the result of the automatic checker (`memo_check.py`, no AI);
- `databook.xlsx`: the databook, recalculated by Excel, whose totals equal the engine;
- `red_flag_report.pptx` and `.pdf`: the Red Flag Report in nine slides, with native (editable) charts;
- `case_note.md`: one page to read before an interview — context, three talking points, limits.

`tests/test_demo.py` checks that the stored memo still passes the checker, that the stored check is current, and that the memo, the databook and the app quote the same figures. To regenerate the databooks and the checks after a change to the engine:

```powershell
python scripts\demo_examples.py
```

The memos are illustrations on public figures, not advice on the companies' securities.

## Earlier example — Corticeira Amorim, FY2024

`Corticeira_Amorim_FY2024_memo.md` was written by Claude Code running the `due-diligence` skill on `data/Corticeira_Amorim_2024_published.xlsx`, the consolidated statements the group published in its 2024 annual report. It used no API key and no prompt beyond `docs/ai_memo_prompt.md`.

What happened:

1. The engine read the statements, in English and in EUR thousands, with a direct-method cash flow statement. It rebuilt the published EBITDA (€157,566k) and operating profit, and passed its four reading checks. It suggested Portugal from the legal form (S.G.P.S.) and materials and packaging from the name.
2. It raised five findings:
   - other income inside EBITDA;
   - weak cash conversion in FY23;
   - short-dated debt;
   - cash in the cash flow statement net of overdrafts;
   - missing documents.

   It also found post-employment benefits and income tax payable as debt-like items, and other financial liabilities and provisions to assess.
3. Claude wrote the memo from the material file only. The first check found one figure without a source: a gross margin rounded to 52.9% where the material gives 52.8%. Claude corrected it, and the second check passed: 74 figures checked, none without a source, no warnings (`Corticeira_Amorim_FY2024_memo_check.md`).

To reproduce:

```powershell
python -m dd_assistant data\Corticeira_Amorim_2024_published.xlsx --json --material
python -m dd_assistant data\Corticeira_Amorim_2024_published.xlsx --check-memo docs\examples\Corticeira_Amorim_FY2024_memo.md
```

This is an illustration on public figures, not advice on the company's securities.
