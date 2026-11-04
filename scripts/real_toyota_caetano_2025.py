"""Toyota Caetano Portugal, S.A. — consolidated statements FY2025/FY2024, copied as printed in the 2025 annual report
(Relatório Anual 2025), from the visible text of the official ESEF report (the XHTML on filings.xbrl.org). The
report's own XBRL tags are not used: several are wrong (held-for-sale assets tagged as inventories). An XHTML has no
pages, so each statement is located by its printed title."""
import sys
from pathlib import Path

from openpyxl import Workbook

URL = "https://filings.xbrl.org/213800NI6JNPX5F44U15/2025-12-31/ESEF/PT/0/213800NI6JNPX5F44U15-2025-12-31.zip"
UNIT = "(Montantes expressos em euros)"
DRE = [
    ["Rendimentos operacionais:"],
    ["Vendas", 30, 607298406, 605002182],
    ["Prestações de serviços", 30, 59695444, 53168125],
    ["Outros rendimentos operacionais", 33, 40035831, 34746983],
    ["Variação da produção", 12, 1059380, 2108825],
    ["Total de rendimentos operacionais", None, 708089061, 695026115],
    ["Gastos operacionais:"],
    ["Custo das vendas", 12, -515450876, -494547643],
    ["Fornecimentos e serviços externos", 31, -65202159, -66038907],
    ["Gastos com o pessoal", 32, -58229812, -53728968],
    ["Amortizações e depreciações", "5, 6 e 7", -18616527, -28125353],
    ["Imparidade de inventários", 26, 2277607, -1957603],
    ["Imparidade de dívidas a receber", 26, 32701, -1166],
    ["Provisões e perdas por imparidade", 26, -357232, -442937],
    ["Outros gastos operacionais", 33, -4972271, -3674399],
    ["Total de gastos operacionais", None, -660518569, -648516976],
    ["Resultados operacionais", None, 47570492, 46509139],
    ["Resultados relativos a empresas associadas e empreendimentos conjuntos", 10, -5513831, -1620256],
    ["Gastos e perdas financeiros", 34, -8070339, -8871934],
    ["Rendimentos e ganhos financeiros", 34, 439774, 452843],
    ["Resultados antes de impostos", None, 34426096, 36469792],
    ["Impostos sobre o rendimento", 27, -8765487, -8316756],
    ["Resultado líquido consolidado do exercício", None, 25660609, 28153036],
    ["Resultado líquido consolidado atribuível:"],
    ["ao Grupo", None, 25082171, 27790475],
    ["a interesses que não controlam", 19, 578438, 362561],
]
BALANCO = [
    ["ATIVO"],
    ["ATIVOS NÃO CORRENTES:"],
    ["Goodwill", 9, 611997, 611997],
    ["Ativos intangíveis", 5, 1202450, 1249137],
    ["Ativos fixos tangíveis", 6, 134968956, 125775711],
    ["Propriedades de investimento", 7, 6711339, 10237380],
    ["Investimentos financeiros em associadas e empreendimentos conjuntos", 10, 35861822, 42952038],
    ["Outros investimentos", 11, 5938493, 5677728],
    ["Ativos por impostos diferidos", 16, 4049209, 4068370],
    ["Clientes", 13, 176106, 13190],
    ["Total de ativos não correntes", None, 189520372, 190585551],
    ["ATIVOS CORRENTES:"],
    ["Inventários", 12, 165828156, 131803688],
    ["Clientes", 13, 87048191, 81055758],
    ["Outras dívidas de terceiros", 14, 1053396, 1618004],
    ["Outros ativos correntes", 15, 6573955, 4767458],
    ["Caixa e equivalentes a caixa", 17, 16570589, 24799624],
    ["Total de ativos correntes excluindo ativos não correntes detidos para venda", None, 277074287, 244044532],
    ["Ativos não correntes detidos para venda", 8, 4146101, 1724506],
    ["Total de ativos correntes", None, 281220388, 245769038],
    ["Total do ativo", None, 470740760, 436354589],
    ["CAPITAL PRÓPRIO E PASSIVO"],
    ["CAPITAL PRÓPRIO:"],
    ["Capital social", None, 35000000, 35000000],
    ["Reserva legal", None, 7498903, 7498903],
    ["Reservas de justo valor", None, 2629378, 2284304],
    ["Outras reservas e resultados transitados", None, 129820618, 113605310],
    ["Resultado consolidado líquido do exercício", None, 25082171, 27790475],
    [None, 18, 200031070, 186178992],
    ["Interesses que não controlam", 19, 2764842, 2178229],
    ["Total do capital próprio", None, 202795912, 188357221],
    ["PASSIVO:"],
    ["PASSIVO NÃO CORRENTE:"],
    ["Financiamentos obtidos", 20, 49877079, 47544798],
    ["Responsabilidades por planos de benefícios definidos", 25, 131047, 215736],
    ["Provisões", 26, 3615941, 3466893],
    ["Outras dívidas a terceiros", 22, 4114465, 794232],
    ["Passivos por impostos diferidos", 16, 2155969, 2135011],
    ["Total de passivos não correntes", None, 59894501, 54156670],
    ["PASSIVO CORRENTE:"],
    ["Financiamentos obtidos", 20, 43225036, 28332494],
    ["Fornecedores", 21, 20318005, 19935577],
    ["Outras dívidas a terceiros", 22, 72707400, 81078149],
    ["Imposto sobre o rendimento a pagar", 23, 1376521, 6248948],
    ["Outros passivos correntes", 24, 70423385, 58245530],
    ["Total de passivos correntes", None, 208050347, 193840698],
    ["Total do passivo", None, 267944848, 247997368],
    ["Total do passivo e capital próprio", None, 470740760, 436354589],
]
DFC = [
    ["ATIVIDADES OPERACIONAIS:"],
    ["Recebimentos de Clientes", None, 1014637317, 928797933],
    ["Pagamentos a Fornecedores", None, -821437440, -632280274],
    ["Pagamentos ao Pessoal", None, -51043983, -46432449],
    ["Fluxo gerado pelas Operações", None, 142155894, 250085210],
    ["Pagamento do Imposto sobre o Rendimento", None, -12650137, -7998400],
    ["Outros Recebimentos/Pagamentos relativos à Atividade Operacional", None, -133493254, -179230134],
    ["Fluxo das Atividades Operacionais", None, -3987497, 62856676],
    ["ATIVIDADES DE INVESTIMENTO:"],
    ["Recebimentos provenientes de:"],
    ["Propriedade de Investimento (Nota 7)", None, 205792, 145170],
    ["Ativos não correntes detidas para venda (Nota 8)", None, 5292500, 755000],
    ["Ativos Fixos Tangíveis", None, 3831, 166205],
    ["Subsídios ao Investimento", None, 1142054, 1459939],
    ["Juros e Proveitos Similares", None, 2712, 15435],
    ["Dividendos", None, 1470000, 1276544],
    [None, None, 8116889, 3818293],
    ["Pagamentos respeitantes a:"],
    ["Ativos Fixos Tangíveis", None, -5741359, -9653503],
    ["Ativos Intangíveis", None, -236721, -2237901],
    [None, None, -5978080, -11891404],
    ["Fluxo das Atividades de Investimento", None, 2138809, -8073111],
    ["ATIVIDADES DE FINANCIAMENTO:"],
    ["Recebimentos provenientes de:"],
    ["Financiamentos Obtidos (Nota 20)", None, 420150000, 356000000],
    ["Passivos de Locação (Nota 20)", None, 8536515, 10130121],
    ["Juros e rendimentos similares", None, 132740, 77600],
    ["Subsídios ao investimento", None, "-", 328886],
    [None, None, 428819255, 366536607],
    ["Pagamentos respeitantes a:"],
    ["Financiamentos Obtidos (Nota 20)", None, -410650000, -398250000],
    ["Rendas de Passivos de Locação (Nota 20)", None, -7321969, -6683211],
    ["Juros e Custos Similares", None, -4682298, -5639842],
    ["Outros Credores", None, -310144, -291642],
    ["Dividendos (Nota 18)", None, -12234538, -10482967],
    [None, None, -435198949, -421347662],
    ["Fluxo das Atividades de Financiamento", None, -6379694, -54811055],
    ["CAIXA E EQUIVALENTES"],
    ["Caixa e Seus Equivalentes no Início do Exercício (Nota 17)", None, 24799624, 24827114],
    ["Variação do Perímetro (Nota 4)", None, -653, "-"],
    ["Caixa e Seus Equivalentes no Fim do Exercício (Nota 17)", None, 16570589, 24799624],
    ["Variação de Caixa e Seus Equivalentes", None, -8228382, -27490],
]

wb = Workbook()
src = wb.active
src.title = "Source"
src.append(["Toyota Caetano Portugal, S.A. — published consolidated accounts FY2025"])
src.append(["Copied as printed from the 2025 annual report (Relatório Anual 2025), consolidated statements: 'Demonstrações "
            "da posição financeira consolidada em 31 de dezembro de 2025 e 2024', 'Demonstrações consolidadas dos "
            "resultados por naturezas…', 'Demonstrações consolidadas dos fluxos de caixa…'. Figures in euros."])
src.append(["Source: official ESEF report (XHTML) " + URL])
src.append(["Obtained on 4 November 2026 from filings.xbrl.org; read from the printed text, not from the XBRL tags. Real, "
            "published figures, used to test the agent on real accounts."])
src.column_dimensions["A"].width = 120
for title, heading, rows in [("DRE", "Demonstração consolidada dos resultados por naturezas", DRE),
                             ("Balanço", "Demonstração da posição financeira consolidada", BALANCO),
                             ("DFC", "Demonstração consolidada dos fluxos de caixa", DFC)]:
    ws = wb.create_sheet(title)
    ws.append([heading])
    ws.append([UNIT])
    ws.append([])
    ws.append([None, "Notas", 2025, 2024])
    for r in rows:
        ws.append(r)
    ws.column_dimensions["A"].width = 70
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data/Toyota_Caetano_2025_published.xlsx")
wb.save(out)
print("saved", out)
