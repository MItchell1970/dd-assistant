"""DD Assistant — preliminary financial due diligence for M&A.

Layers (always kept separate):
    1. extract       -> reads the company's own statements (Excel or PDF) into the standard model
       input_loader  -> the standard model, and the reader for the Excel DD template
    2. metrics       -> computes the metrics (deterministic)
    3. rules         -> compares each metric with a threshold and raises the red flags
    4. report        -> writes the red flag table (Excel and CSV)
    5. ai_memo       -> the Claude API writes the memo and request list (no calculations, no new findings)
       memo_check    -> checks the memo without AI: sourced figures, findings, questions, no recommendations
The app (app.py, Streamlit) only wires these layers together.
"""

__version__ = "0.3.0"
