"""DD Assistant — preliminary financial due diligence for M&A.

Layers (always kept separate):
    1. dataroom      -> reads the whole data room: Excel files merged, PDF/Word text for the memo, checklist
       extract       -> reads the statements (six European formats, euros only, or PDF) into the standard model
       input_loader  -> the standard model, and the reader for the Excel DD template
       units         -> display scale (€1,415k, €939m)
    2. metrics       -> computes the metrics and the reading checks (deterministic)
    3. rules         -> compares each metric with a threshold and raises the red flags
       sectors       -> sector calibration, benchmarks and sector lens
       europe        -> the target's country: accounting framework, statutory tax rate
       deal          -> quality of earnings, net debt and working capital bridges
    4. report        -> writes the Excel and CSV
    5. ai_memo       -> the Claude API writes the memo and request list (no calculations, no new findings)
       memo_check    -> checks the memo without AI: sourced figures, findings, questions, no recommendations
pipeline runs layers 1–3 in one call for the app (app.py), the command line and the Claude Code skill
(.claude/skills/due-diligence), which only wire the layers together.
"""

__version__ = "0.5.0"
