# Manual estimate against the agent — messy Duriva data room (FICTITIOUS)

Run on 23 November 2026. Data room: `data/Duriva_messy_data_room` (52 files). The total is within the public ranges for this work: 8 to 15 hours of data preparation per engagement (Middle Market Growth, article by QoEAgent) and 8 to 12 hours per deal (F4 Fund, profile of Blitsy); both come from sellers of QoE tools. The split by task is this project's estimate (no public source gives minutes per task), low end, one experienced associate in Excel, to be reviewed by Bernardo; fixed before the agent's run: docs/examples/duriva-messy/manual_estimate.md.

| Task | Units | Manual (min) | Agent step | Agent (s) |
|---|---|---|---|---|
| Open and normalise the monthly ERP exports | 35 files × 3 min | 105 | Read the ledger | 0.10 |
| Rebuild the missing month and link the renamed account | 2 issues × 15 min | 30 | Read the ledger | 0.10 |
| Map the chart of accounts to the template lines | 36 accounts × 2 min | 72 | Map the accounts | 0.01 |
| Tie the mapped trial balances to the annual accounts | 3 years × 20 min | 60 | Read the annual accounts and tie | 0.23 |
| Proof of cash, two banks | 72 bank-months × 2 min | 144 | Proof of cash | 0.01 |
| Receipts against revenue + VAT − change in receivables | 36 months × 1.5 min | 54 | Proof of cash | 0.01 |
| Supplier listings against the ledger | 2 year-ends × 10 min | 20 | Proof of cash | 0.01 |
| Monthly working capital, LTM and a peg reference | 1 table × 45 min | 45 | Analysis and databook | 0.49 |
| Analytical tests (red flags) with their sources | 1 rulebook × 90 min | 90 | Analysis and databook | 0.49 |
| **Total** | | **620 min (10.3 h)** | | **1.8 s + human review (to be timed)** |

**Manual (estimated): 620 min · Agent: 1.8 s + human review (to be timed).** The agent's seconds per step are shared where one step does several tasks (the proof of cash does tasks 5 to 7). The human review — deciding the two Low accounts and reading the Medium one, the three differences and the findings — is timed by a person and is not assumed here; once timed, the total is shown.

**Public references** (for the whole of the work, not by task; both from sellers of QoE tools): 8 to 15 hours of data preparation per engagement ([Middle Market Growth (ACG), article by QoEAgent](https://middlemarketgrowth.org/qoeagent-ai-qoe-data-problem/)); 8 to 12 hours per deal for data cleanup and account mapping ([F4 Fund, profile of the start-up Blitsy](https://f4.fund/startups/blitsy-c4a996)). The 620 minutes (10.3 h) are within both ranges; the split by task is this project's estimate.

**Databook:** databook.xlsx, recalculated by Excel: 25 of 25 totals equal the Python values.
