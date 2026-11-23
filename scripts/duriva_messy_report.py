"""The messy Duriva data room run end to end (FICTITIOUS, synthetic test data): docs/examples/duriva-messy/.

  - mapping_decisions.json: the decisions on the Low accounts used for this example (recorded with who and why);
  - databook.xlsx: recalculated by Excel when this PC has it;
  - timing.md: the manual estimate (fixed before the run) and the agent's measured time, side by side;
  - coverage.md: the rules run on the annual accounts alone (as for a listed company) and on the whole data room.

    python scripts\\duriva_messy_report.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dd_assistant import deal_layer as dl  # noqa: E402
from dd_assistant.databook import control_results, recalculate, write_databook  # noqa: E402
from dd_assistant.dataroom import files_in, read_data_room  # noqa: E402
from dd_assistant.pipeline import analyse  # noqa: E402
from dd_assistant.timing import MANUAL, PUBLIC, SOURCE, AgentTime, comparison, manual_minutes  # noqa: E402

ROOM = ROOT / "data" / "Duriva_messy_data_room"
OUT = ROOT / "docs" / "examples" / "duriva-messy"
WHO = "Claude Code, for this example; to be confirmed by Bernardo"
DECISIONS = {"MSC990": {"key": "ogast", "reason": "'Diversos': small recurring operating costs, debit balance in every "
                                                  "month, no other line fits; other expenses", "who": WHO},
             "SUS999": {"key": "exclude", "reason": "Transit account, nil at every month-end: nothing to map", "who": WHO}}


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mapping_decisions.json").write_text(json.dumps(DECISIONS, indent=1, ensure_ascii=False), encoding="utf-8")
    t0 = time.perf_counter()
    files = files_in([ROOM])
    ext = read_data_room(files, mapping_decisions=DECISIONS)
    t1 = time.perf_counter()
    a = analyse(ext)
    path = OUT / "databook.xlsx"
    write_databook(a, path)
    t2 = time.perf_counter()
    steps = {"Load the files": (t1 - t0) - sum(ext.ledger_room.timing.values())}
    steps.update(ext.ledger_room.timing)
    steps["Analysis and databook"] = t2 - t1
    agent = AgentTime(steps, None)
    recalculated = recalculate(path)
    controls = control_results(path) if recalculated else []
    ok = sum(str(c[4]).startswith("OK") for c in controls)

    lines = ["# Manual estimate against the agent — messy Duriva data room (FICTITIOUS)", "",
             f"Run on {datetime.now():%d %B %Y}. Data room: `data/Duriva_messy_data_room` "
             f"({len(files)} files). {SOURCE}", "",
             "| Task | Units | Manual (min) | Agent step | Agent (s) |", "|---|---|---|---|---|"]
    for t in MANUAL:
        lines.append(f"| {t.name} | {t.count:g} {t.units} × {t.minutes_per_unit:g} min | {t.minutes:.0f} | "
                     f"{t.agent_step} | {steps.get(t.agent_step, 0):.2f} |")
    lines += [f"| **Total** | | **{manual_minutes():.0f} min ({manual_minutes() / 60:.1f} h)** | | "
              f"**{agent.seconds:.1f} s + human review (to be timed)** |", "",
              f"**{comparison(agent)}.** The agent's seconds per step are shared where one step does several tasks "
              "(the proof of cash does tasks 5 to 7). The human review — deciding the two Low accounts and reading "
              "the Medium one, the three differences and the findings — is timed by a person and is not assumed here; "
              "once timed, the total is shown.", "",
              "**Public references** (for the whole of the work, not by task; both from sellers of QoE tools): "
              + "; ".join(f"{what} ([{who}]({url}))" for what, who, url, *_ in PUBLIC)
              + f". The {manual_minutes():.0f} minutes ({manual_minutes() / 60:.1f} h) are within both ranges; the "
                "split by task is this project's estimate.",
              "", f"**Databook:** {path.name}, " + (f"recalculated by Excel: {ok} of {len(controls)} totals equal the "
                                                    "Python values." if recalculated else "not recalculated here.")]
    (OUT / "timing.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    annual = analyse(read_data_room([f for f in files if f[0].startswith("Contas anuais e mapas/01")]))
    before, after = dl.coverage(annual), dl.coverage(a)
    from dd_assistant import demo
    tap = dl.coverage(demo.analysis(demo.CASE_BY_SLUG["tap"]))
    rows = ["# Rules run — annual accounts alone against the whole messy data room (FICTITIOUS)", "",
            "Before: the three annual statements only, as a listed company publishes them. After: the whole data room "
            "(ledger by month, bank statements, supplier listings, sales by customer, management adjustments, debt "
            "schedule).", "",
            f"**Before:** {before.text}. **After:** {after.text}. For reference, a listed company on its published "
            f"accounts (TAP Air Portugal FY2025): {tap.text}, with "
            + ", ".join(rid for rid, *_ in tap.blocked) + " blocked and "
            + ", ".join(rid for rid, *_ in tap.not_applicable) + " not applicable.", "",
            "| Rule | Before | After | What unblocks it |", "|---|---|---|---|"]
    for r in a.results:
        b, _ = before.status(r.rule.id)
        n, _ = after.status(r.rule.id)
        if b != n:
            why = next((doc for rid, _, doc in before.blocked if rid == r.rule.id), "")
            rows.append(f"| {r.rule.id} · {r.rule.name} | {b} | {n} | {why} |")
    (OUT / "coverage.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"timing: {comparison(agent)}; coverage {before.text} -> {after.text}; "
          f"databook {ok} of {len(controls)} controls OK")


if __name__ == "__main__":
    run()
