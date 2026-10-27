"""DD Assistant — preliminary financial due diligence for M&A.

Layers (always kept separate):
    1. extract       -> reads the company's own statements (Excel or PDF) into the standard model
       input_loader  -> the standard model, and the reader for the Excel DD template
       units         -> currency and display scale (€1,415k, $134,661m)
    2. metrics       -> computes the metrics and the reading checks (deterministic)
    3. rules         -> compares each metric with a threshold and raises the red flags
       sectors       -> sector calibration, benchmarks and sector lens
       deal          -> quality of earnings, net debt and working capital bridges
    4. report        -> writes the Excel and CSV
    5. ai_memo       -> the Claude API writes the memo and request list (no calculations, no new findings)
       memo_check    -> checks the memo without AI: sourced figures, findings, questions, no recommendations
pipeline runs layers 1–3 in one call for the app (app.py), the command line and the Claude Code skill
(.claude/skills/due-diligence), which only wire the layers together.
"""

__version__ = "0.4.0"
