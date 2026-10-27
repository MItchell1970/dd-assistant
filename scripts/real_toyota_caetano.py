"""Toyota Caetano Portugal, S.A. — consolidated statements FY2024/FY2023, copied as printed in the
2024 annual report (pages 85–90). Written the way an analyst would paste them into Excel."""
import sys
from pathlib import Path
from openpyxl import Workbook

UNIT = "(Montantes expressos em Euros)"
DRE = [
    ["Rendimentos operacionais:"],
    ["Vendas", 30, 605002182, 464900086],
    ["Prestações de serviços", 30, 53168125, 46670546],
    ["Outros rendimentos operacionais", 33, 34746983, 27739438],
    ["Variação da produção", 12, 2108825, -2205290],
    ["Total de rendimentos operacionais", None, 695026115, 537104780],
    ["Gastos operacionais:"],
    ["Custo das vendas", 12, -494547643, -379198024],
    ["Fornecimentos e serviços externos", 31, -66038907, -49997937],
    ["Gastos com o pessoal", 32, -53728968, -48798349],
    ["Amortizações e depreciações", "5, 6 e 7", -28125353, -16992177],
    ["Imparidade de inventários", 26, -1957603, -779622],
    ["Imparidade de dívidas a receber", 26, -1166, 427844],
    ["Provisões e perdas por imparidade", 26, -442937, -1648880],
    ["Outros gastos operacionais", 33, -3674399, -3257713],
    ["Total de gastos operacionais", None, -648516976, -500244858],
    ["Resultados operacionais", None, 46509139, 36859922],
    ["Resultados relativos a empresas associadas e empreendimentos conjuntos", 10, -1620256, -4855313],
    ["Gastos e perdas financeiros", 34, -8871934, -6554306],
    ["Rendimentos e ganhos financeiros", 34, 452843, 740929],
    ["Resultados antes de impostos", None, 36469792, 26191232],
    ["Impostos sobre o rendimento", 27, -8316756, -8723608],
    ["Resultado líquido consolidado do exercício", None, 28153036, 17467624],
    ["Resultado líquido consolidado atribuível:"],
    ["ao Grupo", None, 27790475, 17119170],
    ["a interesses que não controlam", 19, 362561, 348454],
]
BALANCO = [
    ["ATIVO"],
    ["ATIVOS NÃO CORRENTES:"],
    ["Goodwill", 9, 611997, 875997],
    ["Ativos intangíveis", 5, 1249137, 4502520],
    ["Ativos fixos tangíveis", 6, 125775711, 114839875],
    ["Propriedades de investimento", 7, 10237380, 9238419],
    ["Investimentos financeiros em associadas e empreendimentos conjuntos", 10, 42952038, 45928451],
    ["Outros investimentos", 11, 5677728, 5394224],
    ["Ativos por impostos diferidos", 16, 4068370, 3158216],
    ["Clientes", 13, 13190, 52314],
    ["Total de ativos não correntes", None, 190585551, 183990016],
    ["ATIVOS CORRENTES:"],
    ["Inventários", 12, 131803688, 147053173],
    ["Clientes", 13, 81055758, 86171610],
    ["Outras dívidas de terceiros", 14, 1618004, 3877802],
    ["Outros ativos correntes", 15, 4767458, 7103855],
    ["Caixa e equivalentes a caixa", 17, 24799624, 24827114],
    ["Total de ativos correntes excluindo ativos não correntes detidos para venda", None, 244044532, 269033554],
    ["Ativos não correntes detidos para venda", 8, 1724506, 2474403],
    ["Total de ativos correntes", None, 245769038, 271507957],
    ["Total do ativo", None, 436354589, 455497973],
    ["CAPITAL PRÓPRIO E PASSIVO"],
    ["CAPITAL PRÓPRIO:"],
    ["Capital social", None, 35000000, 35000000],
    ["Reserva legal", None, 7498903, 7498903],
    ["Reservas de justo valor", None, 2284304, 2042622],
    ["Outras reservas e resultados transitados", None, 113605310, 106559886],
    ["Resultado consolidado líquido do exercício", None, 27790475, 17119170],
    [None, 18, 186178992, 168220581],
    ["Interesses que não controlam", 19, 2178229, 1807434],
    ["Total do capital próprio", None, 188357221, 170028015],
    ["PASSIVO:"],
    ["PASSIVO NÃO CORRENTE:"],
    ["Financiamentos obtidos", 20, 47544798, 32431252],
    ["Responsabilidades por planos de benefícios definidos", 25, 215736, 1211669],
    ["Provisões", 26, 3466893, 3337677],
    ["Outras dívidas a terceiros", 22, 794232, 2417931],
    ["Passivos por impostos diferidos", 16, 2135011, 3392365],
    ["Total de passivos não correntes", None, 54156670, 42790894],
    ["PASSIVO CORRENTE:"],
    ["Financiamentos obtidos", 20, 28332494, 80796382],
    ["Fornecedores", 21, 19935577, 27892084],
    ["Outras dívidas a terceiros", 22, 81078149, 71247771],
    ["Imposto sobre o rendimento a pagar", 23, 6248948, 3333158],
    ["Outros passivos correntes", 24, 58245530, 59409669],
    ["Total de passivos correntes", None, 193840698, 242679064],
    ["Total do passivo", None, 247997368, 285469958],
    ["Total do passivo e capital próprio", None, 436354589, 455497973],
]
DFC = [
    ["ATIVIDADES OPERACIONAIS:"],
    ["Recebimentos de clientes", None, 928797933, 775586738],
    ["Pagamentos a fornecedores", None, -632280274, -635954524],
    ["Pagamentos ao pessoal", None, -46432449, -43123360],
    ["Fluxo gerado pelas operações", None, 250085210, 96508854],
    ["Pagamento do imposto sobre o rendimento", None, -7998400, -6822815],
    ["Outros recebimentos/pagamentos relativos à atividade operacional", None, -179230134, -102544615],
    ["Fluxo das atividades operacionais", None, 62856676, -12858576],
    ["ATIVIDADES DE INVESTIMENTO:"],
    ["Recebimentos provenientes de:"],
    ["Propriedade de investimento", 7, 145170, 100000],
    ["Ativos não correntes detidos para venda", 8, 755000, 410000],
    ["Ativos fixos tangíveis", None, 166205, 1184],
    ["Subsídios ao investimento", None, 1459939, 923781],
    ["Juros e proveitos similares", None, 15435, 13557],
    ["Dividendos", 10, 1276544, 1579562],
    [None, None, 3818293, 3028084],
    ["Pagamentos respeitantes a:"],
    ["Investimentos financeiros", 10, 0, -12388000],
    ["Ativos fixos tangíveis", None, -9653503, -8100045],
    ["Ativos intangíveis", None, -2237901, -2420827],
    [None, None, -11891404, -22908872],
    ["Fluxo das atividades de investimento", None, -8073111, -19880788],
    ["ATIVIDADES DE FINANCIAMENTO:"],
    ["Recebimentos provenientes de:"],
    ["Financiamentos obtidos", 20, 356000000, 390500083],
    ["Passivos de locação", 20, 10130121, 9062112],
    ["Juros e rendimentos similares", None, 77600, 30477],
    ["Subsídios e doações", 20, 328886, 0],
    [None, None, 366536607, 399592672],
    ["Pagamentos respeitantes a:"],
    ["Financiamentos obtidos", 20, -398250000, -335136286],
    ["Rendas de passivos de locação", 20, -6683211, -6034944],
    ["Juros e custos similares", None, -5639842, -3178431],
    ["Outros credores", None, -291642, -236590],
    ["Dividendos", 18, -10482967, -8739690],
    [None, None, -421347662, -353325941],
    ["Fluxo das atividades de financiamento", None, -54811055, 46266731],
    ["CAIXA E EQUIVALENTES"],
    ["Caixa e seus equivalentes no início do período", 17, 24827114, 11299747],
    ["Caixa e seus equivalentes no fim do período", 17, 24799624, 24827114],
    ["Variação de caixa e seus equivalentes", None, -27490, 13527367],
]

wb = Workbook()
src = wb.active
src.title = "Source"
src.append(['Toyota Caetano Portugal, S.A. — published consolidated accounts FY2024'])
src.append(['Copied as printed from the 2024 annual report, consolidated statements, pages 85–90. Figures in euros.'])
src.append(["Source: " + 'https://toyotacaetano.pt/wp-content/uploads/sites/24/2025/04/RC-2024_04_30-FINAL-CLC-e-Parecer-CF.pdf'])
src.append(["Real, published figures. Used to test the agent on real accounts."])
src.column_dimensions["A"].width = 110
for title, heading, rows in [("DRE", "Demonstração consolidada dos resultados por naturezas", DRE),
                             ("Balanço", "Demonstração da posição financeira consolidada", BALANCO),
                             ("DFC", "Demonstração consolidada dos fluxos de caixa", DFC)]:
    ws = wb.create_sheet(title)
    ws.append([heading])
    ws.append([UNIT])
    ws.append([])
    ws.append([None, "Notas", 2024, 2023])
    for r in rows:
        ws.append(r)
    ws.column_dimensions["A"].width = 70
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'data/Toyota_Caetano_2024_published.xlsx')
wb.save(out)
print("saved", out)
