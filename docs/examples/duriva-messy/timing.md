# Manual estimate against the agent — messy Duriva data room (FICTITIOUS)

Run on 22 November 2026. Data room: `data/Duriva_messy_data_room` (52 files). Hypothesis of this project, per task (no public study gives minutes per task for a first-pass financial due diligence); low end, one experienced associate in Excel; to be reviewed by Bernardo. Fixed before the agent's run: docs/examples/duriva-messy/manual_estimate.md.

| Task | Units | Manual (min) | Agent step | Agent (s) |
|---|---|---|---|---|
| Open and normalise the monthly ERP exports | 35 files × 3 min | 105 | Read the ledger | 0.09 |
| Rebuild the missing month and link the renamed account | 2 issues × 15 min | 30 | Read the ledger | 0.09 |
| Map the chart of accounts to the template lines | 36 accounts × 2 min | 72 | Map the accounts | 0.00 |
| Tie the mapped trial balances to the annual accounts | 3 years × 20 min | 60 | Read the annual accounts and tie | 0.19 |
| Proof of cash, two banks | 72 bank-months × 2 min | 144 | Proof of cash | 0.01 |
| Receipts against revenue + VAT − change in receivables | 36 months × 1.5 min | 54 | Proof of cash | 0.01 |
| Supplier listings against the ledger | 2 year-ends × 10 min | 20 | Proof of cash | 0.01 |
| Monthly working capital, LTM and a peg reference | 1 table × 45 min | 45 | Analysis and databook | 0.46 |
| Analytical tests (red flags) with their sources | 1 rulebook × 90 min | 90 | Analysis and databook | 0.46 |
| **Total** | | **620 min (10.3 h)** | | **1.2 s** |

**Agent:** agent 1.2 s + reviewer not yet timed. The agent's seconds per step are shared where one step does several tasks (the proof of cash does tasks 5 to 7). The reviewer's time — deciding the two Low accounts and reading the Medium one, the three differences and the findings — is timed by a person and is not assumed here.

**Databook:** databook.xlsx, recalculated by Excel: 25 of 25 totals equal the Python values.
