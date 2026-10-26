"""Camada 1 — ler os dados da folha Input do template.

As linhas são encontradas pelo texto da coluna A (não pelo número da linha),
por isso o template pode ganhar linhas novas sem partir o código.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

# Texto da coluna A da folha Input -> chave usada no código.
LINE_LABELS = {
    "Vendas e serviços prestados": "vendas",
    "Custo das mercadorias vendidas (CMV)": "cmv",
    "Fornecimentos e serviços externos": "fse",
    "Gastos com o pessoal": "pess",
    "Imparidade de dívidas a receber": "imp",
    "Outros rendimentos": "orend",
    "Outros gastos": "ogast",
    "Depreciações e amortizações": "da",
    "Juros e gastos similares": "juros",
    "Imposto sobre o rendimento": "irc",
    "Resultado líquido (DRE)": "rl_dre",
    "Ativos fixos tangíveis": "aft",
    "Outros ativos não correntes": "oanc",
    "Inventários": "inv",
    "Clientes": "cli",
    "Outros ativos correntes": "oac",
    "Caixa e depósitos bancários": "caixa",
    "Total do capital próprio": "cp",
    "Resultado líquido (balanço)": "rl_bs",
    "Financiamentos obtidos (não corrente)": "fin_lp",
    "Outros passivos não correntes": "opnc",
    "Fornecedores": "forn",
    "Financiamentos obtidos (corrente)": "fin_cp",
    "Outros passivos correntes": "opc",
    "Resultado líquido (DFC)": "rl_dfc",
    "Variação de clientes": "d_cli",
    "Variação de inventários": "d_inv",
    "Variação de fornecedores": "d_forn",
    "Variação de outros ativos correntes": "d_oac",
    "Variação de outros passivos correntes": "d_opc",
    "Caixa gerada pelas operações (antes de juros e impostos)": "cgo",
    "Fluxo de caixa das atividades operacionais (FCO)": "fco",
    "Pagamentos de ativos fixos (capex)": "capex",
    "Recebimentos da alienação de ativos fixos": "alien",
    "(Ganhos)/perdas na alienação de ativos fixos": "ganho_alien",
    "Caixa no início do período": "cx_ini",
    "Caixa no fim do período": "cx_fim",
    "Total em dívida segundo o mapa": "map_tot",
    "Parcela corrente segundo o mapa": "map_cur",
    "Covenant: dívida líquida / EBITDA máximo": "cov_lim",
}

# Início do texto dos cabeçalhos de secção (o "(" evita confundir com linhas
# da lista de documentos, como "Vendas por cliente").
SECTION_CLIENTS = "Vendas por cliente ("
SECTION_ADJ = "Ajustes ao EBITDA apresentados"
SECTION_DOCS = "Documentos recebidos ("
OTHER_CLIENTS = "Outros clientes"

YEAR_COLS = ["B", "C", "D", "E"]  # colunas de anos na folha Input
HEADER_ROW = 4
SOURCE_COL = "F"


@dataclass
class Named:
    """Uma linha com nome (cliente ou ajuste) e um valor por ano."""
    name: str
    values: dict[int, float | None]


@dataclass
class CompanyData:
    years: list[int]
    lines: dict[str, dict[int, float | None]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    clients: list[Named] = field(default_factory=list)
    other_clients: dict[int, float | None] = field(default_factory=dict)
    clients_source: str = ""
    adjustments: list[Named] = field(default_factory=list)
    adjustments_source: str = ""
    documents: list[tuple[str, bool]] = field(default_factory=list)

    def v(self, key: str, year: int) -> float | None:
        """Valor de uma linha num ano (None se não existir)."""
        return self.lines.get(key, {}).get(year)

    @property
    def pl_years(self) -> list[int]:
        """Anos com demonstração de resultados (têm vendas)."""
        return [y for y in self.years if self.v("vendas", y) is not None]

    @property
    def bs_years(self) -> list[int]:
        """Anos com balanço (têm clientes)."""
        return [y for y in self.years if self.v("cli", y) is not None]


def _num(x):
    return float(x) if isinstance(x, (int, float)) else None


def load_input(path: str | Path) -> CompanyData:
    """Lê a folha Input do template e devolve os dados da empresa."""
    wb = load_workbook(path, data_only=True)
    ws = wb["Input"]
    years = [int(ws[f"{c}{HEADER_ROW}"].value) for c in YEAR_COLS]
    year_of = dict(zip(YEAR_COLS, years))
    data = CompanyData(years=years)

    section = None
    for row in range(HEADER_ROW + 1, ws.max_row + 1):
        label = ws[f"A{row}"].value
        label = label.strip() if isinstance(label, str) else label
        values = {year_of[c]: _num(ws[f"{c}{row}"].value) for c in YEAR_COLS}
        source = ws[f"{SOURCE_COL}{row}"].value or ""

        # cabeçalhos de secção mudam o modo de leitura
        if isinstance(label, str) and label.startswith(SECTION_CLIENTS):
            section = "clients"; continue
        if isinstance(label, str) and label.startswith(SECTION_ADJ):
            section = "adj"; continue
        if isinstance(label, str) and label.startswith(SECTION_DOCS):
            section = "docs"; continue

        if section == "clients":
            if label == OTHER_CLIENTS:
                data.other_clients = values
                section = None
                continue
            if not data.clients_source:
                data.clients_source = source
            if label:  # linhas vazias do template são ignoradas
                data.clients.append(Named(str(label), values))
            continue
        if section == "adj":
            if not data.adjustments_source and source:
                data.adjustments_source = source
            if label:
                data.adjustments.append(Named(str(label), values))
            elif source == "" and all(v is None for v in values.values()):
                section = None  # linha totalmente vazia fecha a secção
            continue
        if section == "docs":
            if label:
                data.documents.append((str(label), str(ws[f"B{row}"].value).strip() == "Sim"))
            continue

        if label in LINE_LABELS:
            key = LINE_LABELS[label]
            data.lines[key] = values
            data.sources[key] = source
    return data
