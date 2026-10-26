"""Camada 3 — catálogo de regras e geração de alertas.

Cada regra compara uma métrica com um limite, em cada ano. Se disparar em pelo
menos um ano, gera um alerta com evidência (números + fonte), pergunta-modelo e
documento a pedir. A IA nunca cria alertas: só explica os que saem daqui.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable

from .input_loader import CompanyData
from .metrics import Metrics


# ---------------------------------------------------------------- formatação
def xround(x, nd: int) -> str:
    """Igual a ROUND(x; nd)&"" no Excel: arredonda meio para cima e tira zeros à direita."""
    if not isinstance(x, (int, float)):
        raise TypeError("valor não numérico")
    q = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    s = format(q.normalize(), "f")
    return "0" if s in ("-0", "") else s


def pct(x) -> str:  # 0.238 -> "23.8%"
    return xround(x * 100, 1) + "%"


def n0(x) -> str:   # 1415.2 -> "1415"
    return xround(x, 0)


def d1(x) -> str:   # 72.01 -> "72"
    return xround(x, 1)


# ---------------------------------------------------------------- regras
@dataclass
class Rule:
    id: str
    area: str
    name: str
    calc: str
    op: str            # ">", "<" ou "abs>"
    limit: float
    limit_fmt: str     # pct, pp, days, eur, count
    metric: str
    relevance: str
    ponto: str
    pergunta: str
    documento: str
    porque: str
    evidence: Callable[["Ctx"], str]

    def fires(self, value) -> str:
        """'Sim', 'Não' ou 'n.d.' (sem valor)."""
        if not isinstance(value, (int, float)):
            return "n.d."
        if self.op == ">":
            hit = value > self.limit
        elif self.op == "<":
            hit = value < self.limit
        else:
            hit = abs(value) > self.limit
        return "Sim" if hit else "Não"

    def limit_text(self) -> str:
        f = self.limit_fmt
        if f == "pct":
            return xround(self.limit * 100, 0) + "%"
        if f == "pp":
            return xround(self.limit, 10) + " p.p."
        if f == "days":
            return xround(self.limit, 10) + " dias"
        if f == "eur":
            return xround(self.limit, 10) + " mil €"
        return "mais de " + xround(self.limit, 10)

    def rule_text(self) -> str:
        return f"{self.id} · {self.name} (limite: {self.limit_text()})"


class Ctx:
    """Atalhos para escrever a evidência: métricas, dados e anos."""

    def __init__(self, d: CompanyData, m: Metrics):
        self.d, self.m = d, m
        self.Y = d.pl_years[-3:]          # os três anos analisados
        self.L = d.pl_years[-1]           # último ano
        self.P = d.pl_years[-2]           # penúltimo ano

    def g(self, key, year):
        return self.m[key].get(year)

    def yrs(self, key, f) -> str:
        return "; ".join(f"{y}: {f(self.g(key, y))}" for y in self.Y)

    def src(self, key) -> str:
        return self.d.sources.get(key, "")


def _r(*a, ev):
    return Rule(*a, evidence=ev)


RULES: list[Rule] = [
    _r("R01", "Receitas", "Maior cliente acima do limite", "Vendas do maior cliente / vendas", ">", 0.20, "pct", "top_share", "Alta",
       "Dependência de um cliente: risco de perda e de pressão sobre preços.",
       "Há contrato de longo prazo com este cliente? Com que prazo, preços e cláusula de mudança de controlo (change of control)?",
       "Contrato com o cliente; vendas e margem mensais por cliente",
       "Perder um cliente grande muda o valor da empresa; uma cláusula de change of control pode deixá-lo sair após a compra.",
       ev=lambda c: f"Maior cliente em % das vendas — {c.yrs('top_share', pct)} ({c.g('top_name', c.L)} em {c.L}). "
                    f"Fonte: {c.src('vendas')}; {c.d.clients_source} e seguintes"),
    _r("R02", "Receitas", "Cliente novo com peso relevante nas vendas", "Vendas a clientes sem vendas no ano anterior / vendas", ">", 0.05, "pct", "new_share", "Alta",
       "Crescimento que pode vir de uma venda pontual e não da carteira recorrente.",
       "As vendas a este cliente repetem-se? Qual a natureza do contrato, o prazo e o que está previsto para o próximo ano?",
       "Contrato e faturas do cliente; carteira de encomendas",
       "O comprador paga por receita que se repete; uma venda pontual infla o crescimento e o EBITDA.",
       ev=lambda c: f"Clientes novos em {c.L}: {pct(c.g('new_share', c.L))} das vendas ({c.g('new_name', c.L)}, {n0(c.g('new_sales', c.L))}). "
                    f"Vendas: +{pct(c.g('g_vendas', c.L))}; sem clientes novos: {pct(c.g('g_ex_new', c.L))}. "
                    f"Fonte: {c.d.clients_source} e seguintes"),
    _r("R03", "Margens", "Variação forte da margem bruta", "Margem bruta do ano − ano anterior (p.p.)", "abs>", 3, "pp", "gm_pp", "Alta",
       "O que mudou nos preços, no mix de produtos ou nos custos de compra.",
       "O que explica a variação da margem bruta: preços de venda, mix de produtos, custos de compra ou descontos a clientes específicos?",
       "Margem por cliente e por linha de produto; tabelas de preços",
       "Cada ponto de margem bruta muda diretamente o EBITDA; se a variação for estrutural, o EBITDA futuro muda.",
       ev=lambda c: f"Margem bruta — {c.yrs('gm', pct)} (variação em {c.L}: {d1(c.g('gm_pp', c.L))} p.p.). "
                    f"Fonte: {c.src('vendas')}; {c.src('cmv')}"),
    _r("R04", "Qualidade do EBITDA", "Outros rendimentos relevantes dentro do EBITDA", "Outros rendimentos / vendas", ">", 0.01, "pct", "or_share", "Alta",
       "Ganhos pontuais (venda de ativos, subsídios, indemnizações) dentro do EBITDA.",
       "Qual o detalhe de outros rendimentos? Inclui ganhos com venda de ativos, subsídios ou outros itens que não se repetem?",
       "Razão (extrato) de outros rendimentos; documentos dos itens relevantes",
       "Um ganho que não se repete, dentro do EBITDA, aumenta o preço pago por algo que não volta a acontecer.",
       ev=lambda c: "Outros rendimentos — " + "; ".join(f"{y}: {n0(c.d.v('orend', y))}" for y in c.Y)
                    + f" ({pct(c.g('or_share', c.L))} das vendas; variação de {pct(c.g('or_var', c.L))}). Fonte: {c.src('orend')}"),
    _r("R05", "Qualidade do EBITDA", "Ajustes da gestão elevados", "Ajustes / EBITDA reportado", ">", 0.10, "pct", "adj_pct", "Alta",
       "Se os ajustes são de facto não recorrentes e têm prova.",
       "Que documentos sustentam cada ajuste? Por que cada custo é considerado não recorrente?",
       "Faturas e contratos de cada ajuste",
       "O EBITDA ajustado é a base do preço; cada ajuste sem prova passa valor do comprador para o vendedor.",
       ev=lambda c: f"Ajustes em % do EBITDA reportado — {c.yrs('adj_pct', pct)}. EBITDA {c.L}: reportado {n0(c.g('ebitda', c.L))}, "
                    f"ajustado pela gestão {n0(c.g('ebitda_adj', c.L))}. Fonte: {c.d.adjustments_source} e seguintes; {c.src('vendas')}"),
    _r("R06", "Qualidade do EBITDA", "Ajuste 'não recorrente' que se repete todos os anos", "Nº de ajustes com valor nos 3 anos", ">", 0, "count", "adj_rec", "Média",
       "Custos classificados como não recorrentes que, na prática, são recorrentes.",
       "Por que este custo aparece todos os anos? O que garante que não se repetirá?",
       "Detalhe do ajuste por ano; plano e custos do programa associado",
       "Um custo que se repete é recorrente: não deve ser somado ao EBITDA.",
       ev=lambda c: f"{n0(c.g('adj_rec', c.L))} ajuste(s) aparece(m) em {c.Y[0]}, {c.Y[1]} e {c.Y[2]} (ex.: {c.g('adj_rec_name', c.L)}). "
                    f"Fonte: {c.d.adjustments_source} e seguintes"),
    _r("R07", "Capital de giro", "Contas a receber crescem acima das vendas", "Crescimento de clientes − crescimento das vendas (p.p.)", ">", 10, "pp", "cli_gap", "Alta",
       "Possível deterioração dos recebimentos ou alargamento de prazos.",
       "Como evoluíram os prazos de pagamento e os saldos vencidos? Que clientes explicam o aumento? Houve alargamento de prazos?",
       "Aging de clientes nos dois últimos fechos; recebimentos após o fecho",
       "Vendas que não se recebem não geram caixa e podem esconder perdas futuras.",
       ev=lambda c: f"Clientes +{pct(c.g('g_cli', c.L))} vs. vendas +{pct(c.g('g_vendas', c.L))} em {c.L} "
                    f"(diferença de {d1(c.g('cli_gap', c.L))} p.p.; {c.P}: {d1(c.g('cli_gap', c.P))} p.p.). "
                    f"DSO: {d1(c.g('dso', c.P))} → {d1(c.g('dso', c.L))} dias. Fonte: {c.src('cli')}; {c.src('vendas')}"),
    _r("R08", "Capital de giro", "Aumento forte do prazo de recebimento", "DSO do ano − DSO do ano anterior (dias)", ">", 15, "days", "dso_var", "Média",
       "Clientes a pagar mais tarde.",
       "Por que os clientes estão a pagar mais tarde? Houve mudança de condições de crédito?",
       "Aging de clientes; condições de crédito por cliente",
       "Prazos maiores prendem caixa e aumentam o risco de incobráveis.",
       ev=lambda c: f"DSO — {c.yrs('dso', d1)} dias. Fonte: {c.src('cli')}; {c.src('vendas')}"),
    _r("R09", "Capital de giro", "Inventários crescem acima do CMV", "Crescimento dos inventários − crescimento do CMV (p.p.)", ">", 10, "pp", "inv_gap", "Média",
       "Stock parado ou obsoleto; compras acima das necessidades.",
       "Qual a composição e a antiguidade dos stocks? Que encomendas justificam o nível atual? Qual a política de imparidades?",
       "Aging de inventários; artigos sem movimento; carteira de encomendas",
       "Stock parado prende caixa e pode valer menos do que o registado.",
       ev=lambda c: f"Inventários +{pct(c.g('g_inv', c.L))} vs. CMV +{pct(c.g('g_cmv', c.L))} em {c.L} "
                    f"(diferença de {d1(c.g('inv_gap', c.L))} p.p.). DIO: {d1(c.g('dio', c.P))} → {d1(c.g('dio', c.L))} dias. "
                    f"Fonte: {c.src('inv')}; {c.src('cmv')}"),
    _r("R10", "Geração de caixa", "Fraca conversão do EBITDA em caixa", "Caixa gerada pelas operações / EBITDA", "<", 0.70, "pct", "conv", "Alta",
       "EBITDA que não se transforma em caixa.",
       "Por que o EBITDA não se converteu em caixa? Que rubricas de capital de giro explicam a diferença?",
       "Reconciliação entre EBITDA e caixa; mapa mensal de capital de giro",
       "O comprador avalia a empresa pelo caixa que ela gera.",
       ev=lambda c: f"Conversão de caixa — {c.yrs('conv', pct)}. FCO {c.L}: {n0(c.g('fco', c.L))}. Fonte: {c.src('cgo')}; {c.src('vendas')}"),
    _r("R11", "Dívida", "Dívida concentrada nos próximos 12 meses", "Financiamentos correntes / dívida financeira", ">", 0.40, "pct", "st_share", "Alta",
       "Necessidade de refinanciamento.",
       "Existem linhas contratadas ou negociações de refinanciamento em curso? Em que condições?",
       "Contratos de financiamento; propostas dos bancos; certificados de covenants",
       "Sem refinanciamento, a empresa pode não conseguir pagar a dívida que vence.",
       ev=lambda c: f"Dívida a vencer em 12 meses — {c.yrs('st_share', pct)} ({n0(c.d.v('fin_cp', c.L))} de {n0(c.g('debt', c.L))} em {c.L}). "
                    f"Fonte: {c.src('fin_cp')}; {c.src('fin_lp')}"),
    _r("R12", "Consistência", "Balanço não fecha", "Ativo − (capital próprio + passivo)", "abs>", 1, "eur", "bs_diff", "Alta",
       "Erro nas demonstrações financeiras.", "Qual a versão correta do balanço?", "Balancete e balanço finais",
       "Um balanço que não fecha invalida as análises que dependem dele.",
       ev=lambda c: f"Diferença no balanço — {c.yrs('bs_diff', n0)}. Fonte: Input, secção Balanço"),
    _r("R13", "Consistência", "Caixa da DFC não bate com o balanço", "Caixa final da DFC − caixa do balanço", "abs>", 1, "eur", "cash_diff", "Média",
       "Erro na DFC ou no balanço.", "Qual é o valor correto? A DFC é a versão auditada? Há outros erros na informação?",
       "DFC corrigida; relatório de auditoria",
       "Um erro simples põe em dúvida a qualidade de toda a informação financeira.",
       ev=lambda c: f"Caixa final da DFC − caixa do balanço — {c.yrs('cash_diff', n0)}. Fonte: {c.src('cx_fim')}; {c.src('caixa')}"),
    _r("R14", "Consistência", "Variações de capital de giro da DFC não batem com o balanço", "Soma das diferenças nas 5 linhas de capital de giro", "abs>", 1, "eur", "wc_diff", "Média",
       "Linha da DFC preenchida com o valor errado.", "Qual a variação correta de cada rubrica de capital de giro?",
       "DFC corrigida; balancetes de abertura e fecho",
       "Se a DFC estiver errada, a conversão de caixa também está.",
       ev=lambda c: f"Diferença entre DFC e balanço nas variações de capital de giro — {c.yrs('wc_diff', n0)}. "
                    f"Fonte: {c.src('d_cli')} a {c.src('d_opc')}"),
    _r("R15", "Consistência", "Resultado líquido diferente entre demonstrações", "Maior diferença entre DRE, balanço e DFC", "abs>", 1, "eur", "ni_diff", "Alta",
       "Demonstrações de versões diferentes.", "Qual é o resultado líquido correto de cada ano?", "Contas finais aprovadas",
       "Demonstrações que não batem podem vir de versões diferentes das contas.",
       ev=lambda c: f"Diferença no resultado líquido — {c.yrs('ni_diff', n0)}. Fonte: {c.src('rl_dre')}; {c.src('rl_bs')}; {c.src('rl_dfc')}"),
    _r("R16", "Consistência", "Vendas por cliente não somam as vendas da DRE", "Soma das vendas por cliente − vendas da DRE", "abs>", 1, "eur", "cl_diff", "Média",
       "Listagem de clientes incompleta ou de outra base.", "Por que a listagem de vendas por cliente não bate com a DRE?",
       "Extração de vendas por cliente reconciliada com a contabilidade",
       "As análises de concentração só valem se a base bater com as contas.",
       ev=lambda c: f"Vendas por cliente − vendas da DRE — {c.yrs('cl_diff', n0)}. Fonte: Input, secção Vendas por cliente"),
    _r("R17", "Consistência", "Mapa da dívida não bate com o balanço", "Diferença no total e na parcela corrente", "abs>", 1, "eur", "map_diff", "Média",
       "Dívida em falta no mapa ou no balanço.", "Que financiamentos explicam a diferença entre o mapa e o balanço?",
       "Mapa da dívida reconciliado; extratos bancários",
       "Dívida não identificada reduz diretamente o valor para o acionista.",
       ev=lambda c: f"Mapa da dívida − balanço em {c.L}: {n0(c.g('map_diff', c.L))}. Fonte: {c.src('map_tot')}; {c.src('fin_cp')}"),
    _r("R18", "Informação", "Documentos obrigatórios em falta", "Nº de documentos marcados com 'Não'", ">", 0, "count", "docs_miss", "Média",
       "Sem estes documentos, alguns alertas não podem ser confirmados nem afastados.",
       "Podem enviar os documentos em falta?", "Os documentos listados na evidência",
       "O que falta também é um ponto de atenção: limita o que o comprador pode verificar.",
       ev=lambda c: f"{n0(c.g('docs_miss', c.L))} documento(s) em falta: {c.g('docs_list', c.L)}. Fonte: Input, Documentos recebidos"),
    _r("R19", "Qualidade do EBITDA", "Ganho na venda de ativos dentro do EBITDA", "Ganhos na alienação de ativos / EBITDA reportado", ">", 0.05, "pct", "gain_pct", "Alta",
       "Ganho que não se repete a aumentar o EBITDA.",
       "Que ativos foram vendidos? Em que rubrica foi registado o ganho e está incluído no EBITDA apresentado?",
       "Contrato ou escritura de venda; registo contabilístico do ganho",
       "Um ganho de venda de ativos não se repete; dentro do EBITDA, o comprador pagaria por ele no múltiplo.",
       ev=lambda c: f"Ganhos na alienação de ativos — {c.yrs('gain', n0)} ({pct(c.g('gain_pct', c.L))} do EBITDA). "
                    f"EBITDA de {c.L} sem esses ganhos: {n0(c.g('ebitda_ex_gain', c.L))}. Fonte: {c.src('ganho_alien')}; {c.src('orend')}"),
    _r("R20", "Dívida", "Folga do covenant reduzida", "1 − (dívida líquida / EBITDA) / limite do covenant", "<", 0.15, "pct", "cov_head", "Alta",
       "Risco de quebra do covenant se o EBITDA comparável for menor do que o reportado.",
       "Como o contrato define o EBITDA do covenant? Qual foi a folga nos últimos testes? Já houve pedidos de dispensa (waiver)?",
       "Contrato do empréstimo; certificados de cumprimento de covenants",
       "A quebra de um covenant pode tornar a dívida exigível de imediato e dá poder negocial aos bancos.",
       ev=lambda c: f"Dívida líquida / EBITDA em {c.L}: {xround(c.g('nd_ebitda', c.L), 2)}x (limite {xround(c.g('cov_lim', c.L), 1)}x); "
                    f"folga de {pct(c.g('cov_head', c.L))}. EBITDA mínimo para cumprir: {n0(c.g('ebitda_min', c.L))}. "
                    f"Sem ganhos na alienação, o rácio é {xround(c.g('nd_ebitda_ex', c.L), 2)}x. Fonte: {c.src('cov_lim')}; {c.src('fin_cp')}"),
]


@dataclass
class RuleResult:
    rule: Rule
    values: dict[int, object]
    fires: dict[int, str]
    evidence: str

    @property
    def alert(self) -> bool:
        return "Sim" in self.fires.values()

    @property
    def years_text(self) -> str:
        return ", ".join(str(y) for y, f in self.fires.items() if f == "Sim")


def evaluate(d: CompanyData, m: Metrics, rules: list[Rule] = RULES) -> list[RuleResult]:
    """Aplica todas as regras aos três últimos anos e devolve o resultado de cada uma."""
    ctx = Ctx(d, m)
    out = []
    for r in rules:
        values = {y: m[r.metric].get(y) for y in ctx.Y}
        fires = {y: r.fires(v) for y, v in values.items()}
        try:
            ev = r.evidence(ctx)
        except (TypeError, ValueError, ZeroDivisionError):
            ev = "Ver folha Métricas"   # como o IFERROR da planilha
        out.append(RuleResult(r, values, fires, ev))
    return out


def alerts(results: list[RuleResult]) -> list[RuleResult]:
    """Só as regras que dispararam, pela ordem do catálogo."""
    return [r for r in results if r.alert]
