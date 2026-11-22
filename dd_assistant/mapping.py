"""Layer 1f — mapping a company's own chart of accounts to the standard model, with a confidence per account.

Each account of the ledger (ledger.py) is linked to a line of the model by up to four clues:
  1. the description, against the dictionary of the statements (extract.py), after expanding abbreviations
     ('Forn. c/c' -> 'fornecedores conta corrente');
  2. the description, against account-level words (a trial balance is more detailed than a statement: 'remunerações',
     'encargos sobre remunerações' are staff costs);
  3. the code, when it looks like the Portuguese national chart (SNC: six digits, 21 customers, 22 suppliers, 62
     external services…);
  4. the behaviour of the balance: profit and loss (it starts again each January) or balance sheet, debit or credit.
Confidence: High = one line found by a rule (1-3), no other line, and the behaviour agrees; Medium = rules point to
different lines or the behaviour disagrees (the first rule's line is used, and the reason shown); Low = no rule, only
the behaviour: never mapped by the agent. A Low account waits for the reviewer's decision (a line, or 'exclude'),
and every decision is recorded with its reason. Until then it is left out and the tie to the annual accounts shows
the gap: nothing enters in silence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .extract import FIELDS
from .ledger import Ledger, Series, norm

PL_KEYS = ("vendas", "cmv", "fse", "pess", "orend", "own", "imp", "ogast", "da", "juros", "irc")
CREDIT_PL = ("vendas", "orend", "own")
ASSETS = ("aft", "oanc", "inv", "cli", "oac", "caixa")
LIABILITIES = ("cp", "fin_lp", "opnc", "fin_cp", "forn", "opc")
LABEL = {f.key: f.label for f in FIELDS}
EXCLUDE = "exclude"
ABBREV = {"merc": "mercadorias", "nac": "nacional", "export": "exportacao", "remuner": "remuneracoes",
          "s": "sobre", "c c": "conta corrente", "forn": "fornecedores", "emprest": "emprestimos",
          "banc": "bancarios", "mlp": "medio e longo prazo", "cp": "curto prazo", "out": "outros",
          "rendim": "rendimentos", "operac": "operacionais", "imparid": "imparidades", "amortiz": "amortizacoes",
          "amort": "amortizacoes", "exerc": "do exercicio", "supor": "suportados", "financ": "financiamentos",
          "acum": "acumuladas", "equip": "equipamento", "transp": "transporte", "dev": "devedores",
          "diferim": "diferimentos", "acresc": "acrescimos", "result": "resultados", "transit": "transitorios",
          "do": "depositos a ordem", "cmvmc": "custo das mercadorias vendidas e das materias consumidas",
          "fse": "fornecimentos e servicos externos", "trab": "trabalhos", "especializ": "especializados",
          "alien": "alienacao", "aft": "ativos fixos tangiveis", "val": "valias", "irc": "imposto sobre o rendimento",
          "basico": "basico", "ativ": "ativos", "seg": "seguranca", "soc": "social", "prov": "provisoes"}
# account-level words (a trial balance is more detailed than a statement), most specific first
ACCOUNT_RULES = [
    (r"^vendas\b", "vendas"), (r"prestacoes de servicos", "vendas"),
    (r"custo das mercadorias vendidas", "cmv"),
    (r"fornecimentos e servicos externos|trabalhos especializados|rendas e alugueres", "fse"),
    (r"remuneracoes|encargos sobre remuneracoes|gastos com o pessoal", "pess"),
    (r"mais valias", "orend"), (r"outros rendimentos|subsidios a exploracao", "orend"),
    (r"imparidades\b.*\bclientes|imparidades de dividas", "imp"),
    (r"outros gastos", "ogast"),
    (r"amortizacoes do exercicio|depreciacoes do exercicio", "da"),
    (r"amortizacoes acumuladas|ativos fixos tangiveis|equipamento", "aft"),
    (r"juros suportados|gastos de financiamento", "juros"),
    (r"imposto sobre o rendimento", "irc"),
    (r"^mercadorias$|^inventarios|materias primas", "inv"),
    (r"^clientes", "cli"),
    (r"outros devedores|diferimentos ativos", "oac"),
    (r"depositos a ordem|^caixa$", "caixa"),
    (r"^capital|^reservas|resultados transitados", "cp"),
    (r"emprestimos bancarios medio e longo prazo", "fin_lp"),
    (r"emprestimos bancarios curto prazo|conta caucionada|descobertos", "fin_cp"),
    (r"^fornecedores", "forn"),
    (r"^estado|outros credores|acrescimos (de )?gastos", "opc"),
]
SNC = [("71", "vendas"), ("72", "vendas"), ("61", "cmv"), ("62", "fse"), ("63", "pess"), ("64", "da"), ("69", "juros"),
       ("81", "irc"), ("78", "orend"), ("68", "ogast"), ("11", "caixa"), ("12", "caixa"), ("21", "cli"),
       ("22", "forn"), ("24", "opc"), ("32", "inv"), ("33", "inv"), ("43", "aft"), ("51", "cp"), ("56", "cp")]


def expand(text: str) -> str:
    """'Forn. c/c' -> 'fornecedores conta corrente'; 'Mais-val. alien. AFT' -> 'mais valias alienacao ativos fixos …'."""
    t = norm(text)
    t = re.sub(r"\bc c\b", "conta corrente", t)
    words = [ABBREV.get(w, w) for w in t.split()]
    return " ".join(words)


@dataclass
class AccountMap:
    series: Series
    key: str | None                 # the model line used (None: pending the reviewer)
    confidence: str                 # High, Medium, Low
    method: str                     # what found it
    reason: str
    suggestion: str | None = None   # Low: what the behaviour suggests (never applied by the agent)
    decision: dict = field(default_factory=dict)   # reviewer: key, reason, who, when

    @property
    def status(self) -> str:
        if self.decision:
            return "Decided by the reviewer" + (" (excluded)" if self.key is None else "")
        return "Pending the reviewer" if self.key is None else "Mapped by the agent"


def behaviour(s: Series) -> tuple[str, str]:
    """('pl' or 'bs', 'debit', 'credit' or 'nil') from the balances: a profit and loss account starts again each
    January (its January closing is the January movement)."""
    janu = [p for (y, m), p in s.points.items() if m == 1 and p.movement is not None]
    is_pl = bool(janu) and all(abs(p.closing - p.movement) < 0.01 for p in janu) and \
        any(abs(p.closing) > 0.01 for p in s.points.values())
    decembers = [p.closing for (y, m), p in s.points.items() if m == 12]
    total = sum(decembers) if decembers else 0.0
    side = "nil" if all(abs(p.closing) < 0.01 for p in s.points.values()) else "debit" if total > 0 else "credit"
    return ("pl" if is_pl else "bs"), side


def _expected(key: str) -> tuple[str, str]:
    if key in PL_KEYS:
        return "pl", "credit" if key in CREDIT_PL else "debit"
    return "bs", "debit" if key in ASSETS else "credit"


def _dictionary(text: str) -> str | None:
    """The statement line whose words the account starts with; None when several lines share them (the statements
    tell current from non-current borrowings by the section, which a trial balance account does not have)."""
    keys = {f.key for f in FIELDS if f.statement in ("pl", "bs") and not f.optional and any(
        text == syn or text.startswith(syn + " ") for syn in f.synonyms)}
    return keys.pop() if len(keys) == 1 else None


def map_account(s: Series) -> AccountMap:
    text = expand(s.name)
    found: list[tuple[str, str]] = []           # most specific first: account words, the code, the statements
    for pattern, key in ACCOUNT_RULES:
        if re.search(pattern, text):
            found.append(("account words", key))
    code = s.codes[-1]
    if re.fullmatch(r"\d{6}", code):
        if key := next((k for prefix, k in SNC if code.startswith(prefix)), None):
            found.append((f"SNC code {code[:2]}", key))
    if key := _dictionary(text):
        found.append(("statement dictionary", key))
    kind, side = behaviour(s)
    keys = list(dict.fromkeys(k for _, k in found))
    seen = f"behaviour: {'profit and loss' if kind == 'pl' else 'balance sheet'}, {side}"
    if not keys:
        guess = {("pl", "debit"): "ogast", ("pl", "credit"): "orend", ("bs", "debit"): "oac",
                 ("bs", "credit"): "opc"}.get((kind, side))
        return AccountMap(s, None, "Low", "behaviour only", f"No rule recognises '{s.name}' ({text}); {seen}. "
                          "Waiting for the reviewer.", guess)
    key = keys[0]
    exp_kind, exp_side = _expected(key)
    contra = key == "aft" and "acumuladas" in text        # accumulated depreciation: a credit inside fixed assets
    agrees = kind == exp_kind and (side in (exp_side, "nil") or contra)
    methods = ", ".join(sorted({m for m, k in found if k == key}))
    if len(keys) == 1 and agrees:
        return AccountMap(s, key, "High", methods, f"'{text}' → {LABEL.get(key, key)} ({methods}); {seen}.")
    why = []
    if len(keys) > 1:
        why.append("the words point to " + " and ".join(LABEL.get(k, k) for k in keys))
    if not agrees:
        why.append(f"{seen}, expected {exp_kind}, {exp_side}")
    # the behaviour decides between the lines the rules found, when it can
    fitting = [k for k in keys if _expected(k)[0] == kind and _expected(k)[1] in (side, "nil")]
    key = fitting[0] if fitting else key
    return AccountMap(s, key, "Medium", methods, f"'{text}' → {LABEL.get(key, key)}: " + "; ".join(why)
                      + ". Check before relying on it.")


def map_accounts(ledger: Ledger, decisions: dict | None = None) -> list[AccountMap]:
    """Every account mapped; the reviewer's decisions (code -> {'key': line or 'exclude', 'reason', 'who', 'when'})
    applied on top and recorded."""
    out = []
    for s in ledger.series:
        m = map_account(s)
        d = next((decisions[c] for c in s.codes if decisions and c in decisions), None)
        if d:
            m.decision = dict(d)
            m.key = None if d.get("key") == EXCLUDE else d.get("key")
        out.append(m)
    return out


def _value(key: str, closing: float) -> float:
    """Ledger balance (debit positive, euros) -> model value (EUR thousands, as in the statements)."""
    return (closing if key in ASSETS else -closing) / 1000


def mapped_lines(ledger: Ledger, maps: list[AccountMap], years: list[int]) -> tuple[dict, dict]:
    """Model lines from the mapped accounts at each December: {key: {year: EUR k}} and their sources. Equity includes
    the year's result (the profit and loss accounts before closing), as the balance sheet does."""
    lines: dict[str, dict[int, float]] = {}
    sources: dict[str, list[str]] = {}
    first = min(ledger.months)[0] if ledger.months else None
    for m in maps:
        if not m.key:
            continue
        for y in years:
            p = m.series.points.get((y, 12))
            if p is not None:
                closing = p.closing
            elif y == (first or 0) - 1 and first in ledger.tb:   # the year before the first export: the trial
                opening = [ledger.tb[first][c][0] for c in m.series.codes if c in ledger.tb[first]]   # balance's opening
                if not opening:
                    continue
                closing = opening[0]
            else:
                continue
            lines.setdefault(m.key, {}).setdefault(y, 0.0)
            lines[m.key][y] += _value(m.key, closing)
            if y == years[-1]:
                sources.setdefault(m.key, []).append(f"{m.series.code} ({p.source})")
    for y in years:     # the year's result sits in the profit and loss accounts until the accounts are closed
        if y < (first or 0):
            continue        # the opening balances are after closing: the result is already in equity
        result = sum(lines.get(k, {}).get(y, 0.0) for k in PL_KEYS)
        if "cp" in lines and y in lines["cp"]:
            lines["cp"][y] += result
    lines = {k: {y: round(v, 2) for y, v in vals.items()} for k, vals in lines.items()}
    return lines, {k: "; ".join(v) for k, v in sources.items()}


def tie_to_accounts(lines: dict, data, years: list[int]) -> list[dict]:
    """The new reading check: each line from the ledger against the annual accounts (to the euro)."""
    out = []
    for key in PL_KEYS + ASSETS + LIABILITIES:
        for y in (y for y in years if y in (data.pl_years if key in PL_KEYS else data.bs_years)):
            published = data.v(key, y)
            mapped = lines.get(key, {}).get(y)
            if published is None and mapped is None:
                continue
            if mapped is None and published == 0:       # no account for a line that is nil in the accounts
                mapped = 0.0
            diff = None if published is None or mapped is None else round(mapped - published, 3)
            out.append({"Line": LABEL.get(key, key), "key": key, "Year": y, "From the ledger": mapped,
                        "Annual accounts": published, "Difference": diff,
                        "OK": diff is not None and abs(diff) <= 0.001})
    return out


def high_share(maps: list[AccountMap]) -> float:
    return sum(m.confidence == "High" for m in maps) / len(maps) if maps else 0.0
