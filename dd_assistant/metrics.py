"""Camada 2 — calcular as métricas (determinístico, sem IA).

Cada métrica é um dicionário {ano: valor}. None significa "n.d." (não disponível):
falta o ano anterior ou o dado. As fórmulas espelham a folha Métricas do template;
o teste de paridade (tests/test_parity.py) confirma que os resultados são iguais.
"""
from __future__ import annotations

from .input_loader import CompanyData

# Chave -> texto da coluna A da folha Métricas (usado no relatório e no teste de paridade).
LABELS = {
    "vendas": "Vendas",
    "g_vendas": "Crescimento das vendas",
    "new_sales": "Vendas a clientes novos",
    "new_share": "Clientes novos (% das vendas)",
    "new_name": "Maior cliente novo",
    "g_ex_new": "Crescimento das vendas sem clientes novos",
    "top_share": "Maior cliente (% das vendas)",
    "top_name": "Maior cliente",
    "ex_top_new": "Vendas sem o maior cliente e sem clientes novos",
    "g_ex_top_new": "Crescimento das vendas sem o maior cliente e sem novos",
    "gm": "Margem bruta",
    "gm_pp": "Variação da margem bruta",
    "ebitda": "EBITDA reportado",
    "ebitda_m": "Margem EBITDA",
    "or_share": "Outros rendimentos (% das vendas)",
    "or_var": "Variação dos outros rendimentos",
    "gain": "Ganhos na alienação de ativos (dentro do EBITDA)",
    "gain_pct": "Ganhos na alienação (% do EBITDA)",
    "ebitda_ex_gain": "EBITDA sem ganhos na alienação",
    "adj": "Ajustes da gestão ao EBITDA",
    "ebitda_adj": "EBITDA ajustado (gestão)",
    "adj_pct": "Ajustes (% do EBITDA reportado)",
    "adj_rec": "Ajustes 'não recorrentes' presentes nos 3 anos",
    "adj_rec_name": "Exemplo de ajuste repetido",
    "g_cli": "Crescimento de clientes (contas a receber)",
    "cli_gap": "Clientes vs. vendas (diferença de crescimento)",
    "dso": "DSO (prazo médio de recebimento)",
    "dso_var": "Variação do DSO",
    "g_inv": "Crescimento dos inventários",
    "g_cmv": "Crescimento do CMV",
    "inv_gap": "Inventários vs. CMV (diferença de crescimento)",
    "dio": "DIO (dias de stock)",
    "dpo": "DPO (prazo médio de pagamento)",
    "dpo_var": "Variação do DPO",
    "cgo": "Caixa gerada pelas operações",
    "conv": "Conversão de caixa",
    "fco": "Fluxo de caixa operacional (FCO)",
    "fcf": "Free cash flow",
    "capex_pct": "Capex (% das vendas)",
    "debt": "Dívida financeira",
    "st_share": "Dívida a vencer em 12 meses (% do total)",
    "net_debt": "Dívida líquida",
    "nd_ebitda": "Dívida líquida / EBITDA",
    "nd_ebitda_ex": "Dívida líquida / EBITDA sem ganhos na alienação",
    "cov_lim": "Limite do covenant (dívida líquida / EBITDA)",
    "cov_head": "Folga do covenant",
    "ebitda_min": "EBITDA mínimo para cumprir o covenant",
    "bs_diff": "Ativo − (capital próprio + passivo)",
    "cash_diff": "Caixa final da DFC − caixa do balanço",
    "wc_diff": "Variações de capital de giro: DFC vs. balanço",
    "ni_diff": "Resultado líquido: maior diferença DRE / balanço / DFC",
    "cl_diff": "Vendas por cliente − vendas da DRE",
    "map_diff": "Mapa da dívida − balanço",
    "docs_miss": "Documentos obrigatórios em falta",
    "docs_list": "Lista de documentos em falta",
}

Metrics = dict[str, dict[int, object]]


def N(x) -> float:
    """Como a função N() do Excel: vazio conta como 0."""
    return x if isinstance(x, (int, float)) else 0.0


def div(a, b):
    """Divisão que devolve None em vez de dar erro."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def growth(cur, prev):
    r = div(cur, prev)
    return None if r is None else r - 1


def compute_metrics(d: CompanyData) -> Metrics:
    P = d.pl_years                      # anos com DRE (2023–2025)
    B = d.bs_years                      # anos com balanço (2022–2025)
    L = P[-1]                           # último ano
    prev = {y: (P[i - 1] if i > 0 else None) for i, y in enumerate(P)}
    prev_bs = {y: (B[B.index(y) - 1] if y in B and B.index(y) > 0 else None) for y in B}
    m: Metrics = {k: {} for k in LABELS}
    v = d.v

    def put(key, years, fn):
        for y in years:
            m[key][y] = fn(y)

    Pp = [y for y in P if prev[y] is not None]   # anos com ano anterior na DRE

    # ---------------- Receitas
    put("vendas", P, lambda y: v("vendas", y))
    put("g_vendas", Pp, lambda y: growth(v("vendas", y), v("vendas", prev[y])))

    def new_by_client(y):
        p = prev[y]
        return [(c.name, N(c.values.get(y)))
                for c in d.clients if N(c.values.get(p)) == 0 and N(c.values.get(y)) > 0]

    put("new_sales", Pp, lambda y: sum(x for _, x in new_by_client(y)))
    put("new_share", Pp, lambda y: div(m["new_sales"][y], v("vendas", y)))

    def new_name(y):
        lst = new_by_client(y)
        if not lst:
            return "—"
        best = max(x for _, x in lst)
        return next(n for n, x in lst if x == best)

    put("new_name", Pp, new_name)
    put("g_ex_new", Pp, lambda y: growth(v("vendas", y) - m["new_sales"][y], v("vendas", prev[y])))

    def top(y):
        vals = [(c.name, N(c.values.get(y))) for c in d.clients]
        best = max(x for _, x in vals)
        return next(n for n, x in vals if x == best), best

    put("top_share", P, lambda y: div(top(y)[1], v("vendas", y)))
    put("top_name", P, lambda y: top(y)[0])
    put("ex_top_new", P, lambda y: v("vendas", y) - top(y)[1] - (m["new_sales"][y] if y in Pp else 0))
    put("g_ex_top_new", Pp, lambda y: growth(m["ex_top_new"][y], m["ex_top_new"][prev[y]]))

    # ---------------- Margens e qualidade do EBITDA
    put("gm", P, lambda y: div(v("vendas", y) + v("cmv", y), v("vendas", y)))
    put("gm_pp", Pp, lambda y: (m["gm"][y] - m["gm"][prev[y]]) * 100)
    ebitda_lines = ["vendas", "cmv", "fse", "pess", "imp", "orend", "ogast"]
    put("ebitda", P, lambda y: sum(N(v(k, y)) for k in ebitda_lines))
    put("ebitda_m", P, lambda y: div(m["ebitda"][y], v("vendas", y)))
    put("or_share", P, lambda y: div(v("orend", y), v("vendas", y)))
    put("or_var", Pp, lambda y: None if N(v("orend", prev[y])) == 0 else growth(v("orend", y), v("orend", prev[y])))
    put("gain", P, lambda y: -N(v("ganho_alien", y)))
    put("gain_pct", P, lambda y: None if m["ebitda"][y] <= 0 else m["gain"][y] / m["ebitda"][y])
    put("ebitda_ex_gain", P, lambda y: m["ebitda"][y] - m["gain"][y])
    put("adj", P, lambda y: sum(N(a.values.get(y)) for a in d.adjustments))
    put("ebitda_adj", P, lambda y: m["ebitda"][y] + m["adj"][y])
    put("adj_pct", P, lambda y: None if m["ebitda"][y] <= 0 else m["adj"][y] / m["ebitda"][y])
    last3 = P[-3:]
    repeated = [a.name for a in d.adjustments if all(N(a.values.get(y)) != 0 for y in last3)]
    if len(P) >= 3:
        m["adj_rec"][L] = len(repeated)
        m["adj_rec_name"][L] = repeated[0] if repeated else "—"

    # ---------------- Capital de giro
    Pb = [y for y in P if prev_bs.get(y) is not None]   # anos com balanço do ano anterior
    put("g_cli", Pb, lambda y: growth(v("cli", y), v("cli", prev_bs[y])))
    put("cli_gap", Pp, lambda y: None if m["g_cli"].get(y) is None or m["g_vendas"].get(y) is None
        else (m["g_cli"][y] - m["g_vendas"][y]) * 100)
    put("dso", P, lambda y: div(v("cli", y), v("vendas", y)) * 365)
    put("dso_var", Pp, lambda y: m["dso"][y] - m["dso"][prev[y]])
    put("g_inv", Pb, lambda y: growth(v("inv", y), v("inv", prev_bs[y])))
    put("g_cmv", Pp, lambda y: growth(v("cmv", y), v("cmv", prev[y])))
    put("inv_gap", Pp, lambda y: None if m["g_inv"].get(y) is None or m["g_cmv"].get(y) is None
        else (m["g_inv"][y] - m["g_cmv"][y]) * 100)
    put("dio", P, lambda y: v("inv", y) / -v("cmv", y) * 365)
    put("dpo", P, lambda y: v("forn", y) / -v("cmv", y) * 365)
    put("dpo_var", Pp, lambda y: m["dpo"][y] - m["dpo"][prev[y]])

    # ---------------- Geração de caixa
    put("cgo", P, lambda y: v("cgo", y))
    put("conv", P, lambda y: None if m["ebitda"][y] <= 0 else m["cgo"][y] / m["ebitda"][y])
    put("fco", P, lambda y: v("fco", y))
    put("fcf", P, lambda y: N(v("fco", y)) + N(v("capex", y)) + N(v("alien", y)))
    put("capex_pct", P, lambda y: div(-N(v("capex", y)), v("vendas", y)))

    # ---------------- Dívida
    put("debt", B, lambda y: N(v("fin_lp", y)) + N(v("fin_cp", y)))
    put("st_share", B, lambda y: div(N(v("fin_cp", y)), m["debt"][y]))
    put("net_debt", B, lambda y: m["debt"][y] - N(v("caixa", y)))
    put("nd_ebitda", P, lambda y: None if m["ebitda"][y] <= 0 else m["net_debt"][y] / m["ebitda"][y])
    put("nd_ebitda_ex", P, lambda y: None if m["ebitda_ex_gain"][y] <= 0 else m["net_debt"][y] / m["ebitda_ex_gain"][y])
    lim = v("cov_lim", L)
    if lim:
        m["cov_lim"][L] = lim
        nd = m["nd_ebitda"].get(L)
        m["cov_head"][L] = None if nd is None else 1 - nd / lim
        m["ebitda_min"][L] = m["net_debt"][L] / lim

    # ---------------- Consistência (0 = tudo bate)
    assets = ["aft", "oanc", "inv", "cli", "oac", "caixa"]
    liabs = ["cp", "fin_lp", "opnc", "forn", "fin_cp", "opc"]
    put("bs_diff", B, lambda y: sum(N(v(k, y)) for k in assets) - sum(N(v(k, y)) for k in liabs))
    put("cash_diff", P, lambda y: N(v("cx_fim", y)) - N(v("caixa", y)))

    def wc(y):
        p = prev_bs[y]
        delta = lambda k: N(v(k, y)) - N(v(k, p))
        # ativos: a variação na DFC tem sinal contrário ao aumento no balanço
        return (abs(N(v("d_cli", y)) + delta("cli")) + abs(N(v("d_inv", y)) + delta("inv"))
                + abs(N(v("d_forn", y)) - delta("forn")) + abs(N(v("d_oac", y)) + delta("oac"))
                + abs(N(v("d_opc", y)) - delta("opc")))

    put("wc_diff", Pb, wc)
    put("ni_diff", P, lambda y: max(abs(N(v("rl_dre", y)) - N(v("rl_bs", y))), abs(N(v("rl_dre", y)) - N(v("rl_dfc", y)))))
    put("cl_diff", P, lambda y: sum(N(c.values.get(y)) for c in d.clients) + N(d.other_clients.get(y)) - v("vendas", y))
    if v("map_tot", L) is not None:
        m["map_diff"][L] = abs(N(v("map_tot", L)) - m["debt"][L]) + abs(N(v("map_cur", L)) - N(v("fin_cp", L)))

    # ---------------- Informação
    missing = [name for name, ok in d.documents if not ok]
    m["docs_miss"][L] = len(missing)
    m["docs_list"][L] = "; ".join(missing) if missing else "—"
    return m
