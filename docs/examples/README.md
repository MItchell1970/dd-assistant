# Example — Corticeira Amorim, FY2024

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
