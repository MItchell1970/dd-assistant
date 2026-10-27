# Example — Apple Inc., FY2024

`Apple_FY2024_memo.md` was written by Claude Code running the `due-diligence` skill on `data/Apple_FY2024_published.xlsx` (the condensed statements Apple published with its Q4 FY2024 results). No API key and no prompt engineering beyond `docs/ai_memo_prompt.md`.

What happened:

1. The engine read a US GAAP income statement by function in USD millions, with quarters beside the full year. It rebuilt EBITDA as operating income plus D&A from the cash flow statement ($134,661m) and passed its six reading checks.
2. It raised four findings: receivables and inventories growing ahead of activity, restricted cash in the cash flow statement, and missing documents. It also found current and non-current marketable securities and deferred revenue as candidates for net debt.
3. Claude wrote the memo from the material file only. `memo_check.py` then checked every figure against that material: 74 checked, none without a source, no warnings (`Apple_FY2024_memo_check.md`).

To reproduce:

```powershell
python -m dd_assistant data\Apple_FY2024_published.xlsx --json --material
python -m dd_assistant data\Apple_FY2024_published.xlsx --check-memo docs\examples\Apple_FY2024_memo.md
```

This is an illustration on public figures, not advice on Apple's securities.
