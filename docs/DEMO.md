# Three-minute demo

For an interview or a screen recording. Data: **Duriva**, a fictitious distributor with planted issues (synthetic: say so on screen), then **Toyota Caetano Portugal**, real published accounts. Before you start: `streamlit run app.py`, and close any other app windows.

| Time | On screen | What to say |
|---|---|---|
| 0:00–0:20 | The app, sample "Duriva — data room in 5 documents" | "This is a first-pass financial due diligence. I drop the data room as a seller sends it: four Excel files and a management report in PDF. Duriva is a fictitious company I use as a test case, with issues planted on purpose." |
| 0:20–0:45 | Overview: "Start here", reading step green | "Before any finding, the tool checks its own reading: it rebuilds EBITDA and operating profit from the lines it read and compares them with what the company published. Here all subtotals match, so the numbers can be trusted." |
| 0:45–1:15 | Overview: "Where it goes wrong", then the Red flags tab, one finding opened (R19) | "Fifteen findings, ordered by what moves the price. A €250k gain on selling assets sits inside EBITDA. Each finding shows the evidence with its source cell, the question for management and the document to request. The thresholds come from transaction services, private equity and credit practice, and each rule is explained in plain words." |
| 1:15–1:45 | Deal view: QoE bridge, management adjustments set to "Under review" | "The quality of earnings bridge: management presents €1,870k of EBITDA. Until each adjustment is supported, it stays out: diligence-adjusted EBITDA is €1,165k. The decisions are mine, not the tool's." |
| 1:45–2:15 | Deal view: Price, choose "Completion accounts", EV 10,000 | "Nothing is priced until I choose the mechanism of the SPA. With completion accounts and an EV of €10m, equity is €7.1m: EV, less net debt, plus the gap between working capital at closing and the peg. The peg here is only an indicative average of year-ends, and the tool says so." |
| 2:15–2:40 | Red flags tab: "Download databook"; open it in Excel on the Net Debt sheet | "The databook is the Excel a deal team works in. Blue figures come from the data room, black ones are formulas. I decide only in the yellow cells, and the totals follow. Excel recalculated it and every total equals the Python value." |
| 2:40–3:00 | Sidebar: sample "Toyota Caetano Portugal" | "On real accounts, Toyota Caetano's published statements, it rebuilds EBITDA to the euro. It also flags what a reviewer found by hand: D&A growing 65% against 9% for fixed assets, and other current liabilities at 22% of revenue. The AI only writes the memo, and a checker without AI verifies every figure it cites, for the right year." |

## Questions to expect, and short answers

- **Where do the rules come from?** From the workstreams of a financial due diligence (quality of earnings, working capital, net debt, cash flow, information quality) plus credit metrics. Each rule shows its threshold, its rationale and the practice it comes from (`python -m dd_assistant --rules`).
- **How do you know it read the accounts right?** The reading checks: subtotals rebuilt from the lines it read must equal the published ones. On EDP's ESEF filing, operating profit matches to the thousand euros in both years.
- **What does the AI do?** It writes the memo and the request list from the findings. It does no arithmetic and creates no findings; a deterministic checker rejects any figure that is not in the material, or that is cited for another year.
- **What can it not do?** No legal, tax or commercial due diligence; no valuation; no monthly data, so no LTM and no negotiated peg; leakage is a screening register, not a legal view. The open gaps are in `docs/GAPS.md`.
- **What did you build, and what did AI build?** I designed the scope, the method, the rules and thresholds, the deal and price bridges, and checked the results against published accounts. The code was written with Claude Code from my specifications, and every change runs against the test suite.

## Checklist before recording

- [ ] `python -m unittest` passes.
- [ ] The app restarted after the last change (Ctrl+C, then `streamlit run app.py`).
- [ ] "Synthetic data" said when Duriva is on screen.
- [ ] No client data, no API key and no personal files visible.
