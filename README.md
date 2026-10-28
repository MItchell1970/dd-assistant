# DD Assistant — preliminary financial due diligence for European companies

Drop a target's data room as the seller sends it — a folder of Excel statements, PDFs and Word documents — and get, in seconds, the first pass of a financial due diligence. It is built for the European market:

- euros only;
- statements in the national formats: Portuguese SNC, Spanish PGC, French PCG, German HGB, Italian civil code, and IFRS in English.

The focus is M&A, buy-side or vendor due diligence. The same analysis also serves a lender's credit review or a health check with no transaction.

What the agent does:

- **Reads the whole data room.** Excel files are read together as one set of statements, every figure keeping its file and cell. PDFs, Word and text documents (management report, audit report, contracts) are read as text for the memo, free and on your computer, and the key-document checklist is ticked from what is there. Statements that exist only as a PDF are read by Claude, on request.
- **Reads ESEF filings.** Every listed company in the EU files its annual report in iXBRL (ESEF), with each figure tagged with its IFRS meaning. Drop the report package (.zip, from [filings.xbrl.org](https://filings.xbrl.org) or the company's website) and every line is read from its tag, exact and free: the company's own lines are understood through their ESEF anchoring to IFRS, and each figure keeps its tag as its source (`ifrs-full:Revenue`).
- **Understands every line.** "Vendas e serviços prestados", "Importe neto de la cifra de negocios", "Chiffre d'affaires", "Umsatzerlöse", "Ricavi delle vendite" and "Revenue" are all revenue. It handles European number, date and unit formats (1.234,5 · 31.12.2024 · TEUR · miles de euros), income statements by nature or by function, and subtotals placed before or after their lines.
- **Checks its own reading.** It rebuilds gross profit, EBITDA and operating profit from the lines it read and compares them with what the company published. A mismatch means a line is missing, and the agent says so.
- **Builds the deal view**, the numbers a deal team asks for first:
  - quality of earnings: reported → management-adjusted → diligence-adjusted EBITDA;
  - net debt, with the debt-like and cash-like items it finds: pensions, TFR, tax payable, leases, shareholder loans, marketable securities;
  - net working capital, with an indicative peg reference.
- **Runs 26 rules**, each explained in plain words with the practice it comes from. Each finding gives evidence with its source, what to investigate, the question for management and the document to request.
  - Thresholds are calibrated for 15 sectors, always with the reason shown.
  - Severity follows size and persistence where it matters: other income inside EBITDA (R04) is measured against EBITDA and is High above a quarter of it; weak cash conversion (R10) is High only when the years analysed together convert less than 70%, since one weak year is often working capital timing.
  - The country of the target, suggested from its legal form (S.G.P.S., S.L., SAS, GmbH, S.p.A.…), sets the accounting framework and the statutory tax rate.
  - The company is compared with European listed peers in its sector, and each sector adds the questions a specialist would ask.

An AI layer — the Claude API, or Claude Code itself with no API key — then writes a two-page memo and the information request list. It does no calculations and creates no findings, and a deterministic checker verifies every figure it writes.

> Sample data:
> - **Duriva**, a fictitious distributor with planted issues, as a data room of five documents;
> - **Velmora**, a fictitious clean company, used to measure false alarms;
> - the published FY2024 accounts of **Toyota Caetano Portugal** and **Corticeira Amorim**;
> - tested on **EDP**'s FY2025 ESEF filing (not included: 96 MB; download it from filings.xbrl.org).

## Why

Much of the first pass in a due diligence is mechanical:
- reading the statements and cross-checking them;
- computing ratios;
- building the EBITDA and net debt bridges;
- spotting movements;
- drafting the request list.

This tool does that part in seconds, with every number traceable to its file and cell. The judgement stays with the analyst: accepting a management adjustment, treating an item as debt-like, confirming the sector, the country and the purpose.

## The rules, in plain words

The full rulebook is in the app (Rulebook tab) and in `python -m dd_assistant --rules`.

| Workstream | Rules | What they check, in plain words |
|---|---|---|
| Revenue quality | R01, R02, R16 | One customer too big; growth from customers who may not stay; a customer listing that does not add up |
| Quality of earnings | R03–R06, R19, R26 | Margin shifts; one-off income inside EBITDA; management add-backs; "non-recurring" costs that recur; disposal gains; own work capitalised |
| Net working capital | R07–R09, R23 | Customers paying later; stock building up; suppliers paid later at year-end |
| Cash flow | R10, R24 | EBITDA not turning into cash; investment below depreciation |
| Net debt and credit | R11, R13, R17, R20, R21, R22 | Debt due soon; cash defined differently; debt missing from the schedule; covenant headroom; high leverage; low interest cover |
| Information quality | R12, R14, R15, R18 | Statements that do not tie; missing documents |
| Tax | R25 | Effective tax rate far from the country's statutory rate |

These are the standard checks of financial due diligence (the Big Four transaction services workstreams), private equity and bank credit. R01–R20 match the reference Excel template exactly; R21–R26 go beyond it.

## How it works

| Layer | File | What it does |
|---|---|---|
| Data room | `dataroom.py` | Reads every document at once: merges the Excel files, extracts the text of PDFs and Word files, ticks the document checklist |
| ESEF | `esef.py` | Reads an ESEF report package: tagged facts of the consolidated statements, in the company's order, own lines through their anchoring, euros only |
| Read | `extract.py` | Maps the statements to a standard model with a six-language dictionary. Detects the unit (euros only), the European formats and the P&L presentation; stops at operating profit; flags debt-like and cash-like lines |
| Metrics | `metrics.py` | Growth, concentration, margins, quality of earnings, DSO/DIO/DPO, cash conversion, net debt, leverage, interest cover, capex/D&A, effective tax rate, consistency checks and reading checks |
| Rules | `rules.py` | 26 rules with explicit thresholds, plain-language explanations and their practice |
| Context | `europe.py`, `sectors.py` | 10 European countries (framework, tax rate, legal forms) and 15 sectors (calibration, Damodaran Europe benchmarks, sector lens) |
| Deal view | `deal.py` | Quality of earnings, net debt and working capital bridges; benchmarks; illustrative value at stake |
| Report | `report.py` | Excel (red flags, deal view, sector, reading checks, metrics, source data) and CSV, with the reviewer's status |
| AI memo | `ai_memo.py` + `docs/ai_memo_prompt.md` | Writes the memo and request list for the chosen purpose; no calculations, no new findings |
| Check | `memo_check.py` | Verifies, without AI, every figure, every finding, every question and the absence of investment recommendations |
| Pipeline | `pipeline.py` | The whole analysis in one call, for the app, the command line and the skill; JSON export |
| App | `app.py` | Drop the data room → overview → deal view → red flags → sector → data room → rulebook → memo |

The calculations are deterministic and auditable. The tests (`python -m unittest`) confirm that:
- the Python gives exactly the numbers of the reference Excel template;
- reading the raw data room gives the figures of the hand-filled template, whether it is one workbook or five documents;
- the agent rebuilds the published EBITDA of two real groups exactly;
- it reads Spanish, French, German and Italian statutory accounts correctly;
- it reads an ESEF report package from its tags: precise figures over rounded ones, no segment or half-year figure, the company's own lines through their anchors;
- it raises no false alarm on a clean company.

## The agent (Claude Code skill)

`.claude/skills/due-diligence/SKILL.md` turns Claude Code into a due diligence agent that uses this engine as its tools. Open Claude Code in this folder and ask, for example, *"run a due diligence on data/Duriva_data_room"*. The agent:

1. runs the engine and checks the reading first. If a check fails, it finds the line and proposes the correction;
2. confirms the purpose, the country and the sector, and briefs the findings in plain words;
3. asks you to accept or reject each management adjustment;
4. writes the memo itself, with no API key;
5. runs the checker and fixes its own errors until the memo passes.

On Corticeira Amorim the first check caught a rounded figure and the second passed: see `docs/examples/`.

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
# the app (runs on this computer only): drop the data room's files
streamlit run app.py

# a whole data room folder, or files, saved to output\ (Excel and CSV)
python -m dd_assistant data\Duriva_data_room
python -m dd_assistant data\Corticeira_Amorim_2024_published.xlsx --country PT --sector materials

# a listed company's ESEF annual report package (.zip from filings.xbrl.org)
python -m dd_assistant 529900CLC3WDMGI9VH80-2025-12-31.zip

# purpose: buy (default), sell (vendor due diligence), lend (credit review), review (health check)
python -m dd_assistant data\Duriva_data_room --purpose lend

# the reviewer's decisions, corrections and documents received
python -m dd_assistant data\Duriva_data_room --adjustment "Custos de arranque=Accepted" --set orend:2025=60 --received "AR ageing"

# the rulebook, the sectors, JSON and the AI material (free), the memo with the API (paid), the memo check
python -m dd_assistant --rules
python -m dd_assistant --sectors
python -m dd_assistant data\Duriva_data_room --json --material
python -m dd_assistant data\Duriva_data_room --memo
python -m dd_assistant data\Duriva_data_room --check-memo memo.md
```

Costs:
- the memo with the API uses Claude Opus 5.5 and costs roughly USD 0.20–0.50 per company; the actual cost is shown at the end;
- reading statements from a PDF also uses the Claude API, roughly USD 0.10–0.40 per document, and always shows the extracted figures for review;
- every other document is read locally, at no cost.

## Results

**Real companies (published FY2024 accounts, copied into Excel as printed):**

| Company | Statements | EBITDA rebuilt as | EBITDA |
|---|---|---|---|
| Toyota Caetano Portugal | Portuguese SNC layout, in euros | operating result + D&A | €74,634k |
| Corticeira Amorim | IFRS in English, EUR thousands | operating profit before depreciation | €157,566k |

Both balance sheets reconcile and all reading checks pass. The findings are ones a reviewer would recognise:

- Toyota: material other income, negative operating cash flow in FY23, short-term debt, and capex below depreciation in both years;
- Amorim: cash in the cash flow statement net of bank overdrafts, and short-dated debt.

The deal view finds pensions and income tax payable as debt-like items in both groups.

**Duriva** (five documents): 15 findings, identical to the single-workbook version. Management-adjusted EBITDA is €1,870k. Diligence-adjusted EBITDA is €1,165k until the adjustments are supported: the €250k disposal gain inside other income is removed. Other findings include:

- a 23.8% customer concentration;
- a one-off sale presented as growth;
- cash conversion of 20.5%;
- 55% of debt due within 12 months.

**Velmora (clean company):** no analytical findings, with the general thresholds, with its sector's and with the 26 rules.

**EDP (ESEF FY2025, read from the tags):** operating profit rebuilt to the thousand euros in both years (€2,999,414k in FY25, €2,261,983k in FY24), with the share of joint ventures inside it as EDP presents it. The country (Portugal) comes from the report itself and the sector is suggested as energy & utilities. Six findings: material other income (EDP's gains on asset rotation sit there), cash conversion of 67% in FY25, leverage of 3.6x, interest cover of 2.6x, an effective tax rate of 36.7% in FY24 and the documents a listed report does not contain. Tax equity partnerships in North America and collateral deposits are shown as items to assess in net debt.

**Spanish, French, German and Italian accounts:** each format is read correctly, operating profit is rebuilt exactly, the balance sheet balances and no false alarm is raised (`tests/test_europe.py`).

## Scope

This is a preliminary **financial** due diligence on annual statements in euros. It does not cover:

- legal, tax, commercial, IT or HR due diligence;
- contract review;
- valuation;
- statements in other currencies (an ESEF report in another currency is refused too).

Monthly, LTM and budget figures are not in annual accounts. The request list asks for them, and the working capital peg reference is labelled indicative for that reason. Sector benchmarks come from European listed groups and are orientation, never a finding on their own. Every threshold, calibration and benchmark is visible in the app, the Excel and `--rules` / `--sectors`.

## Sources

- Toyota Caetano Portugal and Corticeira Amorim statements: each file's *Source* sheet gives the URL and pages.
- Sector benchmarks: Damodaran Online (NYU Stern), European industry datasets, January 2026; regenerate them with `scripts/sector_benchmarks.py`.
- Statutory tax rates: headline 2024 rates with usual local surcharges (`dd_assistant/europe.py`), for a plausibility test only.
