"""Corticeira Amorim, S.G.P.S., S.A. — consolidated statements FY2025/FY2024 copied as printed in the official 2025
annual report (Portuguese, ESEF XHTML on filings.xbrl.org): quarterly columns before the label in the income and cash
flow statements, as printed. An XHTML has no pages: each statement is located by its printed title. Note 19 (cash and
cash equivalents) is copied too: it reconciles the cash of the balance sheet to the cash flow statement."""
import sys
from pathlib import Path

from openpyxl import Workbook

URL = "https://filings.xbrl.org/213800J5M11TDEP3LQ76/2025-12-31/ESEF/PT/0/000544-2025-12-31.zip"
UNIT = "milhares de euros"
BS = [  # label, note, 31 Dec 2025, 31 Dec 2024
    ["Ativo"],
    ["Ativos fixos tangíveis", 8, 418745, 435511], ["Ativos intangíveis", 9, 11403, 15073], ["Direito de uso", 11, 5141, 5242],
    ["Goodwill", 9, 29095, 29165], ["Ativos biológicos", 10, 4245, 4324], ["Propriedades de investimento", 12, 2061, 2204],
    ["Investimentos em associadas e emp. conjuntos", 13, 35073, 35322], ["Outros ativos financeiros", 14, 2205, 1640],
    ["Impostos diferidos", 15, 15191, 20379], ["Outros ativos", 18, 1356, 1518],
    ["Ativos não correntes", None, 524515, 550376],
    ["Inventários", 16, 388297, 466545], ["Ativos biológicos", 10, 973, 711], ["Clientes", 17, 175804, 194403],
    ["Imposto sobre o rendimento", 15, 7856, 19630], ["Outros ativos financeiros", 14, 37057, 40558],
    ["Outros ativos", 18, 11405, 13335], ["Caixa e equivalentes", 19, 64997, 76636],
    ["Ativos correntes", None, 686388, 811818],
    ["Total do Ativo", None, 1210903, 1362194],
    ["Capital Próprio"],
    ["Capital social", 20, 133000, 133000], ["Reservas e outras componentes do capital próprio", 20, 562546, 541588],
    ["Resultado líquido do exercício", None, 55567, 69699], ["Interesses que não controlam", 21, 89200, 90770],
    ["Total do Capital Próprio", None, 840312, 835057],
    ["Passivo"],
    ["Dívida remunerada", 22, 100365, 119053], ["Outros passivos financeiros", 24, 5633, 6651],
    ["Outros passivos", 24, 2366, 2400], ["Provisões", 25, 3539, 5691], ["Benefícios pós-emprego", 26, 3798, 3210],
    ["Impostos diferidos", 15, 32597, 40586],
    ["Passivos não correntes", None, 148299, 177592],
    ["Dívida remunerada", 22, 40491, 153270], ["Fornecedores", 23, 107945, 112159],
    ["Outros passivos financeiros", 24, 43264, 51070], ["Outros passivos", 24, 26612, 28033],
    ["Imposto sobre o rendimento", 15, 3981, 5012],
    ["Passivos correntes", None, 222293, 349545],
    ["Total do Passivo e Capital Próprio", None, 1210903, 1362194],
]
IS = [  # 4T25, 4T24 (not audited), label, note, 2025, 2024
    [184453, 212813, "Vendas", 7, 860967, 939061],
    [-77841, -103784, "Custo das mercadorias vendidas e das matérias consumidas", None, -374484, -443873],
    [-2797, 4043, "Variação de produção", None, -16112, 1074],
    [-36273, -39702, "Fornecimento e serviços externos", 27, -140517, -151501],
    [-44326, -44432, "Gastos com pessoal", 28, -190711, -193191],
    [-40, -1046, "Ajustamentos de imparidade de ativos", 29, -2516, -789],
    [5207, 6220, "Outros rendimentos e ganhos", 30, 17421, 17849],
    [-4974, -4195, "Outros gastos e perdas", 30, -13065, -11064],
    [23410, 29917, "Resultado operacional antes de depreciações/amortizações e não recorrentes", None, 140985, 157566],
    [-13601, -15204, "Depreciações/Amortizações", "8, 9, 10, 11,12", -58895, -57636],
    [9809, 14713, "Resultado operacional", None, 82090, 99930],
    [34, 6730, "Resultados não recorrentes", 31, -413, 1434],
    [-809, -3057, "Gastos financeiros", 32, -5872, -12865],
    [329, 236, "Rendimentos financeiros", 32, 1093, 973],
    [-966, 1164, "Ganhos (perdas) em associadas e emp. conjuntos", 13, 1888, 4305],
    [8397, 19785, "Resultados antes de impostos", None, 78785, 93776],
    [2489, 2170, "Imposto sobre os resultados", 15, -16227, -16630],
    [10887, 21955, "Resultado líquido", None, 62558, 77146],
    [999, 90, "Interesses que não controlam", 21, 6991, 7447],
    [9887, 21865, "Resultado líquido atribuível aos acionistas da Corticeira Amorim", None, 55567, 69699],
]
CF = [  # 4T25, 4T24 (not audited), label, note, 2025, 2024
    [None, None, "ATIVIDADES OPERACIONAIS"],
    [213027, 237377, "Recebimentos de clientes", None, 930244, 1004992],
    [-144913, -160512, "Pagamentos a fornecedores", None, -601966, -725733],
    [-46036, -51942, "Pagamentos ao pessoal", None, -184707, -189968],
    [22079, 24923, "Fluxo gerado pelas operações", None, 143571, 89291],
    [-6843, -16093, "Pagamento/recebimento do imposto sobre o rendimento", None, -8321, -30115],
    [29216, 17622, "Outros recebimentos/pagamentos relativos à atividade operacional", None, 83765, 61737],
    [44451, 26452, "FLUXOS DAS ATIVIDADES OPERACIONAIS", None, 219015, 120913],
    [None, None, "ATIVIDADES DE INVESTIMENTO"],
    [None, None, "Recebimentos provenientes de:"],
    [650, 641, "Ativos fixos tangíveis", None, 1392, 1179],
    [-18, 41, "Ativos intangíveis", None, 35, 87],
    ["-", 18897, "Alienação de subsidiárias (líquido de caixa e equivalentes de caixa)", 6, "-", 18915],
    [6, "-", "Outros ativos", None, 23, "-"],
    [754, 433, "Juros e proveitos relacionados", None, 1499, 1310],
    [500, 350, "Dividendos", None, 3249, 1499],
    [None, None, "Pagamentos respeitantes a:"],
    [-16844, -10224, "Ativos fixos tangíveis", None, -39888, -40397],
    [2461, -4380, "Investimentos Financeiros", 6, -379, -4380],
    [-3119, "-", "Outros Ativos Financeiros", None, -3119, "-"],
    [-921, 228, "Ativos intangíveis", None, -1896, -1325],
    [-16531, 5985, "FLUXOS DAS ATIVIDADES DE INVESTIMENTOS", None, -39083, -23113],
    [None, None, "ATIVIDADES DE FINANCIAMENTO"],
    [None, None, "Recebimentos provenientes de:"],
    [-49569, 57200, "Empréstimos obtidos", None, 2731, 109650],
    [1268, 2100, "Subsídios de investimento", None, 1972, 7006],
    [419, 531, "Outros", None, 1578, 1501],
    [None, None, "Pagamentos respeitantes a:"],
    [11958, -95631, "Empréstimos obtidos", None, -114745, -114309],
    [-1644, -2617, "Juros e gastos similares", None, -7003, -12411],
    [552, -549, "Locações", None, -1316, -978],
    ["-", -11970, "Dividendos pagos aos acionistas da Corticeira Amorim", 20, -42560, -38570],
    [-956, -1138, "Dividendos pagos aos Interesses que não controlam", 21, -6675, -5723],
    [-2800, "-", "Aquisição de Interesses que não controlam", 21, -2800, "-"],
    [-770, 149, "Subsídios de investimento", None, -2149, -2480],
    [-154, -190, "Outros", None, -1025, -722],
    [-41695, -52116, "FLUXOS DAS ATIVIDADES DE FINANCIAMENTO", None, -171992, -57037],
    [-13776, -19679, "Variações de caixa e seus equivalentes", None, 7940, 40763],
    [199, 192, "Efeito das diferenças de câmbio", None, -358, 70],
    [49122, 47451, "Caixa e seus equivalentes no início do período", 19, 27964, -12869],
    [35546, 27964, "Caixa e seus equivalentes no fim do período", 19, 35546, 27964],
]
NOTE19 = [  # label, 2025, 2024
    ["Caixa", 222, 275], ["Depósitos à ordem", 43770, 72632], ["Depósitos a prazo", 20966, 3689], ["Outros", 39, 41],
    ["Caixa e equivalentes conforme D.F. Posição Financeira", 64997, 76636],
    ["Descobertos bancários", -29451, -48672],
    ["Caixa e equivalentes conforme D. F. Caixa", 35546, 27964],
]

wb = Workbook()
src = wb.active
src.title = "Source"
src.append(["Corticeira Amorim, S.G.P.S., S.A. — published consolidated accounts FY2025"])
src.append(["Copied as printed from the official 2025 annual report (Portuguese): 'Demonstração Consolidada da Posição "
            "Financeira', 'Demonstração Consolidada de Resultados por Naturezas', 'Demonstração Consolidada dos Fluxos de "
            "Caixa' and note 19 (Caixa e equivalentes). Figures in thousand euros."])
src.append(["Source: official ESEF report (XHTML) " + URL])
src.append(["Obtained on 4 November 2026 from filings.xbrl.org; read from the printed text. Real, published figures, used to "
            "test the agent on real accounts."])
src.column_dimensions["A"].width = 120
ws = wb.create_sheet("Posição financeira")
ws.append(["Demonstração Consolidada da Posição Financeira"])
ws.append([])
ws.append([None, "Notas", "31 dezembro 2025", "31 dezembro 2024"])
for r in BS:
    ws.append(r)
ws.append([])
ws.append([UNIT])
for title, heading, rows in [("Resultados", "Demonstração Consolidada de Resultados por Naturezas", IS),
                             ("Fluxos de caixa", "Demonstração Consolidada dos Fluxos de Caixa", CF)]:
    ws = wb.create_sheet(title)
    ws.append([heading])
    ws.append([])
    ws.append(["4T25", "4T24", None, "Notas", 2025, 2024])
    ws.append(["(não auditado)", "(não auditado)"])
    for r in rows:
        ws.append(r)
    ws.append([])
    ws.append([UNIT])
ws = wb.create_sheet("Nota 19 Caixa")
ws.append(["19. Caixa e equivalentes"])
ws.append([UNIT, 2025, 2024])
for r in NOTE19:
    ws.append(r)
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] /
           "data/Corticeira_Amorim_2025_published.xlsx")
wb.save(out)
print("saved", out)
