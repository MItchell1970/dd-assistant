# DD Assistant — preliminary financial due diligence for M&A

Upload a target's financial data room as received: Excel or PDF, with the income statement by nature (SNC, IFRS) or by function (US GAAP, UK), in EUR, USD, GBP or BRL. No template to fill in. In seconds the agent:

- reads every line of the income statement, balance sheet and cash flow statement, keeps the cell or page it came from, and **checks its own reading** against the subtotals the company published;
- builds the **deal view**, the numbers a deal team asks for first:
  - quality of earnings: reported → management-adjusted → diligence-adjusted EBITDA;
  - net debt: financial debt, then the debt-like and cash-like items it finds in the balance sheet;
  - net working capital, with an indicative peg reference;
- runs **20 red flag rules**, with thresholds calibrated for the **sector**. Each finding gives evidence with its source, what to investigate, the question for management and the document to request;
- puts the company next to **sector benchmarks** of European listed peers and adds the **sector lens**: the questions a specialist in that industry would ask.

An AI layer, the Claude API or Claude Code itself, then writes a two-page memo and the information request list. It does no calculations and creates no findings, and a deterministic checker verifies every figure it writes.

> Sample data: **Duriva** (fictitious distributor with planted issues), **Velmora** (fictitious clean company, to measure false alarms) and the published FY2024 accounts of **Toyota Caetano Portugal**, **Corticeira Amorim** and **Apple**.

## Why

Much of the first pass in a due diligence is mechanical: reading the statements, cross-checking them, computing ratios, building the EBITDA and net debt bridges, spotting movements and drafting the request list. This tool does that part in seconds, with every number traceable to its cell. The judgement stays with the analyst: accepting a management adjustment, treating an item as debt-like, confirming the sector.

## How it works

| Layer | File | What it does |
|---|---|---|
| Read | `extract.py` | Maps the company's own statements to a standard model: a Portuguese/English dictionary for Excel (figures read from the cells, each with its reference), Claude vision for PDFs (figures as printed; units and signs converted by code). Detects currency and unit, P&L by nature or by function, stops at operating profit, keeps the full year when quarters sit beside it, and flags debt-like and cash-like lines |
| Metrics | `metrics.py` | Growth, concentration, margins, quality of earnings, DSO/DIO/DPO, cash conversion, net debt, covenant headroom, consistency checks, and **reading checks** (gross profit, EBITDA, operating profit rebuilt against the published subtotals) |
| Rules | `rules.py` | 20 rules with explicit thresholds; a sector may change a few of them, always with the reason shown next to the finding |
| Deal view | `deal.py` | Quality of earnings, net debt and working capital bridges; benchmarks; illustrative value at stake at a multiple the user enters |
| Sectors | `sectors.py` | 15 sectors: calibration, Damodaran benchmarks (Europe, January 2026), sector lens and the keywords that suggest the sector from the data room |
| Report | `report.py` | Excel (red flags, deal view, sector, reading checks, metrics, source data) and CSV, with the reviewer's status and comments |
| AI memo | `ai_memo.py` + `docs/ai_memo_prompt.md` | Groups the findings into themes anchored on the deal view, tests management's narrative against the numbers, applies the sector lens, writes the memo and request list |
| Check | `memo_check.py` | Verifies, without AI, that every figure in the memo exists in the material, every finding is covered, every question has a request and there is no investment recommendation |
| Pipeline | `pipeline.py` | The whole analysis in one call, for the app, the command line and the skill; JSON export |
| App | `app.py` | Upload → deal view → red flags → sector → source data → download → memo |

The calculations are deterministic and auditable:

- `tests/test_parity.py` confirms the Python gives exactly the same numbers as the formulas of the reference Excel template;
- `tests/test_extract.py` confirms that reading the raw data rooms gives exactly the same figures as the hand-filled templates;
- `tests/test_real_companies.py` confirms the agent rebuilds the published EBITDA of three real groups exactly.

## The agent (Claude Code skill)

`.claude/skills/due-diligence/SKILL.md` turns Claude Code into a due diligence agent that uses this engine as its tools. Open Claude Code in this folder and ask, for example, *"run a due diligence on data/Apple_FY2024_published.xlsx"*. The agent:

1. runs the engine and **checks the reading first**. If a check fails, it finds the line in the file and proposes the correction;
2. confirms the sector and currency, and briefs the deal view and the findings;
3. asks you to accept or reject each management adjustment. These are judgement calls, so they stay with you;
4. writes the memo itself, with no API key, following the same prompt;
5. runs the checker and **fixes its own errors until the memo passes**.

That loop is what makes it an agent rather than a script: it acts with tools, observes the result, decides the next step and verifies its own output against a deterministic check. See `docs/examples/` for a memo it wrote on Apple: 74 figures checked, none without a source.

## Install (Windows, PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest -v
```

On Windows ARM PCs, use the **x64** Python: Streamlit depends on `pyarrow`, which has no Windows ARM64 build yet.

## Use

```powershell
# the app (runs on this computer only)
streamlit run app.py

# red flags, deal view and sector analysis, saved to output\ (Excel and CSV)
python -m dd_assistant data\Duriva_data_room.xlsx
python -m dd_assistant data\Apple_FY2024_published.xlsx --sector hardware
python -m dd_assistant --sectors                        # the 15 sectors and their calibrated thresholds

# the reviewer's decisions, corrections and documents received
python -m dd_assistant data\Duriva_data_room.xlsx --adjustment "Custos de arranque=Accepted" --set orend:2025=60 --received "AR ageing"

# JSON and the AI material (free), the memo with the Claude API (paid), or the check of a memo written elsewhere
python -m dd_assistant data\Duriva_data_room.xlsx --json --material
python -m dd_assistant data\Duriva_data_room.xlsx --memo
python -m dd_assistant data\Duriva_data_room.xlsx --check-memo memo.md
```

The memo with the API uses Claude Opus 5.5 and costs roughly USD 0.20–0.50 per company; the actual cost is shown at the end. The exact text sent to the AI is saved in `output\*_ai_material.md` for audit. Reading a PDF also uses the Claude API, roughly USD 0.10–0.40 per document, and always shows the extracted figures for review before they are used.

## Results

**Real companies (published FY2024 accounts, copied into Excel as printed):** the agent rebuilds each group's own EBITDA exactly:

| Company | Statements | EBITDA rebuilt as | EBITDA |
|---|---|---|---|
| Toyota Caetano Portugal | Portuguese, in euros | operating result + D&A | €74,634k |
| Corticeira Amorim | English, in EUR thousands | operating profit before depreciation | €157,566k |
| Apple | US GAAP by function, in USD millions | operating income + D&A from the cash flow statement | $134,661m |

All three balance sheets reconcile and all reading checks pass. The findings are ones a reviewer would recognise:

- Toyota: material other income within EBITDA, negative operating cash flow in FY23 and short-term debt concentration;
- Amorim: cash in the cash flow statement net of bank overdrafts;
- Apple: receivables and inventories growing ahead of activity, and restricted cash in the cash flow statement.

The deal view finds the debt-like items on the face of the balance sheet: Toyota's pension obligations and income tax payable, Amorim's post-employment benefits, Apple's marketable securities as cash-like items.

**Duriva:** 15 findings (10 high severity). Management-adjusted EBITDA is €1,870k. Diligence-adjusted EBITDA is €1,165k until the adjustments are supported: the €250k disposal gain inside other income is removed. Other findings:

- concentration on the largest customer (23.8%);
- a one-off sale presented as organic growth;
- cash conversion of 20.5%;
- 55% of debt due within 12 months;
- a cash flow statement that does not reconcile to the balance sheet.

**Velmora (clean company):** no analytical findings, with the general thresholds and with those of its sector (distribution). Velmora was designed by someone who knows the rules, so it is a sanity check; the published accounts above are the stronger test.

## Scope

This is a preliminary **financial** due diligence on annual statements. It does not cover:

- legal, tax, commercial, IT or HR due diligence;
- contract review;
- valuation.

Monthly, LTM and budget figures are not in annual accounts. The request list asks for them, and the working capital peg reference is labelled indicative for that reason. Sector benchmarks come from European listed groups and are orientation, never a finding on their own. Every threshold, calibration and benchmark is visible in the app, the Excel and `python -m dd_assistant --sectors`.

## Sources

- Toyota Caetano Portugal, Corticeira Amorim and Apple statements: each file's *Source* sheet gives the URL and pages.
- Sector benchmarks: Damodaran Online (NYU Stern), European industry datasets, January 2026. Regenerate them with `scripts/sector_benchmarks.py`.
