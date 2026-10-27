"""Layer 5 — AI: writes the memo, the information request list and notes for the template (Claude API).

The AI does no calculations and creates no findings. It receives what layers 1–4 have
already produced (findings with evidence and source, the rule catalogue, the metrics, the
source figures) plus the full text of the data room, and follows docs/ai_memo_prompt.md
(the system prompt).

The Claude API key comes from the ANTHROPIC_API_KEY environment variable or the .env file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import anthropic

from .extract import FIELDS, data_room_text  # noqa: F401  (data_room_text re-exported for callers)
from .input_loader import CompanyData
from .metrics import LABELS, Metrics
from .report import Reviews, fmt_value
from .rules import RuleResult, alerts, fy

ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILE = ROOT / "docs" / "ai_memo_prompt.md"

MODEL = "claude-opus-5-5"
MAX_TOKENS = 64000      # streaming, so no timeout risk; the memo stays well below this
EFFORT = "high"         # analytical work (Opus 5.5 defaults to "medium")
# Price per million tokens for Claude Opus 5.5 (October 2026), only to estimate the cost.
PRICE_IN, PRICE_OUT = 4.00, 20.00

_EXTRA_LABELS = {"map_tot": "Debt schedule — total outstanding", "map_cur": "Debt schedule — due within 12 months",
                 "cov_lim": "Covenant — maximum net debt / EBITDA"}


class MemoError(Exception):
    """The call ran but did not return a memo (refused, or no API key)."""


@dataclass
class Memo:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    truncated: bool     # True if the answer stopped at the token limit

    @property
    def cost_usd(self) -> float:
        """Estimate at Opus 5.5 prices (a fallback model, if it answered, may be priced differently)."""
        return (self.input_tokens * PRICE_IN + self.output_tokens * PRICE_OUT) / 1_000_000


def load_env(path: Path = ROOT / ".env") -> None:
    """Read KEY=value lines from a .env file without overriding variables that already exist."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value:   # an empty key (copied from .env.example) does not count
                os.environ.setdefault(key.strip(), value)


def system_prompt() -> str:
    """The prompt in docs/ai_memo_prompt.md from '## Role' onwards (the header is a note for people)."""
    text = PROMPT_FILE.read_text(encoding="utf-8")
    start = text.find("## Role")
    return text[start:] if start >= 0 else text


# ---------------------------------------------------------------- material sent to the AI
def _row(cells) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _table(head: list, rows: list[list]) -> list[str]:
    return [_row(head), _row(["---"] * len(head))] + [_row(r) for r in rows]


def _alerts_section(results: list[RuleResult], reviews: Reviews) -> list[str]:
    out = ["## 1. Red flags (findings that fired, in catalogue order)"]
    al = alerts(results)
    if not al:
        out.append("No rule fired.")
    for i, r in enumerate(al, 1):
        rule = r.rule
        status, comment = reviews.get(rule.id, ("Pending", ""))
        out += ["",
                f"### {i}. {rule.id} · {rule.name} — {rule.area}; severity {rule.severity}; years {r.years_text}",
                f"- Evidence (with source): {r.evidence}",
                f"- Test and threshold: {rule.test}. Rule: {rule.rule_text()}",
                f"- What to investigate: {rule.focus}",
                f"- Why it matters: {rule.rationale}",
                f"- Model question for management: {rule.question}",
                f"- Document to request: {rule.request}",
                f"- Reviewer status: {status}" + (f" — {comment}" if comment else "")]
    return out


def _rules_section(results: list[RuleResult]) -> list[str]:
    years = sorted(results[0].values)
    rows = [[r.rule.id, r.rule.name, r.rule.limit_text()]
            + [f"{fmt_value(r.values[y])} ({r.fires[y]})" for y in years] + ["Yes" if r.alert else "No"]
            for r in results]
    head = ["Rule", "Name", "Threshold"] + [f"{fy(y)} (fires?)" for y in years] + ["Finding"]
    return ["## 2. Rule catalogue (every rule: value per year and whether it fired)"] + _table(head, rows)


def _metrics_section(metrics: Metrics, years: list[int]) -> list[str]:
    rows = [[label] + [fmt_value(metrics[key].get(y)) for y in years] for key, label in LABELS.items()]
    return ["## 3. Metrics (calculated by the template)"] + _table(["Metric"] + [fy(y) for y in years], rows)


def _input_section(d: CompanyData) -> list[str]:
    ys = d.years
    vals = lambda values: [fmt_value(values.get(y)) for y in ys]
    labels = {f.key: f.label for f in FIELDS} | _EXTRA_LABELS
    rows = [[label] + vals(d.lines[key]) + [d.sources.get(key, "")] for key, label in labels.items() if key in d.lines]
    rows += [[f"Sales to customer: {c.name}"] + vals(c.values) + [d.clients_source if i == 0 else ""]
             for i, c in enumerate(d.clients)]
    if d.other_clients:
        rows.append(["Sales to other customers"] + vals(d.other_clients) + [""])
    rows += [[f"Management EBITDA adjustment: {a.name}"] + vals(a.values) + [d.adjustments_source if i == 0 else ""]
             for i, a in enumerate(d.adjustments)]
    docs = "; ".join(f"{name}: {'Yes' if ok else 'No'}" for name, ok in d.documents)
    return (["## 4. Input (source figures, EUR thousands, with data room reference)"]
            + _table(["Line item"] + [fy(y) for y in ys] + ["Source"], rows)
            + ["", f"Key documents received: {docs}"])


def build_material(d: CompanyData, metrics: Metrics, results: list[RuleResult], source_text: str,
                   reviews: Reviews | None = None, name: str = "") -> str:
    """The text sent to the AI: the four layers of the analysis plus the data room. Saved for audit."""
    parts = [f"# Material for the preliminary analysis{' — ' + name if name else ''}", "",
             "Reading notes: amounts in EUR thousands; percentages as decimals (0.238 = 23.8%); margin changes and "
             "growth gaps in percentage points; DSO, DIO and DPO in days; 'n/a' = not available. Data room "
             "references use the form Sheet!Cell (e.g. DRE!D5) or a page number.", ""]
    parts += _alerts_section(results, reviews or {}) + [""]
    parts += _rules_section(results) + [""]
    parts += _metrics_section(metrics, d.years) + [""]
    parts += _input_section(d) + [""]
    parts += ["## 5. Data room (full text)", source_text or "Not provided.", "",
              "Write the three deliverables (two-page memo, information request list and notes to improve the "
              "template) in Markdown, in British English. Review them against the checklist before answering and "
              "reply with the deliverables only."]
    return "\n".join(parts)


# ---------------------------------------------------------------- Claude API call
def write_memo(material: str, client: anthropic.Anthropic | None = None,
               on_text: Callable[[str], None] | None = None) -> Memo:
    """Send the material to the Claude API and return the memo. on_text receives the text as it arrives."""
    client = client or anthropic.Anthropic()
    try:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",     # if the model declines, the API retries on the recommended fallback model
            system=system_prompt(),
            messages=[{"role": "user", "content": material}],
        ) as stream:
            for text in stream.text_stream:
                if on_text:
                    on_text(text)
            msg = stream.get_final_message()
    except TypeError as e:
        if "authentication method" in str(e):   # the SDK found no key at all
            raise MemoError("No Claude API key found. Copy .env.example to .env and paste your key "
                            "(ANTHROPIC_API_KEY=...).") from e
        raise

    if msg.stop_reason == "refusal":
        raise MemoError("The model declined the request (and so did the fallback model). Review the material sent.")
    text = "".join(b.text for b in msg.content if b.type == "text")
    return Memo(text, msg.model, msg.usage.input_tokens, msg.usage.output_tokens,
                truncated=msg.stop_reason == "max_tokens")
