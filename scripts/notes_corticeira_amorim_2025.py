"""Corticeira Amorim, S.G.P.S., S.A. — notes to the CONSOLIDATED accounts FY2025, copied as printed in the official
2025 annual report (Portuguese, ESEF XHTML). An XHTML has no pages: each note is located by its printed number and
title. Amounts in thousand euros ("milhares de euros"). Copy, never compute: every number below was read in the
printed text; '-' is a dash as printed, None is a cell printed empty. The checks at the end only verify the copying
(lines against the printed total, the printed total against the consolidated statements); the report rounds each line
to the thousand, so a difference of 1 or 2 is the report's own rounding.

    python scripts/notes_corticeira_amorim_2025.py            # writes data/notes/Corticeira_Amorim_2025_notes.xlsx
"""
import sys
from pathlib import Path

from openpyxl import Workbook

UNIT = "milhares de euros"
SOURCE = "Source: Relatório e Contas 2025 (ESEF), nota {}"
D = "-"  # a dash, as printed

SEG_HEADER = ["Amorim Florestal", "Amorim Cork", "Amorim Cork Solutions", "Corticeira Amorim e Outras", "Ajustamentos",
              "Consolidado"]
PROV_HEADER = ["Detalhe", "Contingências Fiscais - IS", "Contingências Fiscais - Outros", "Garantias Clientes", "Outros",
               "Total"]

# sheet, topic, note, title as printed, header (after 'Item'), rows
NOTES = [
    ("N30a Outros rendimentos", "other_income", 30, "30. OUTROS RENDIMENTOS E GANHOS / OUTROS GASTOS E PERDAS",
     ["2025", "2024"], [
        ["Cobertura risco cambial: dif. câmbio (nota 3a))", D, D],
        ["Cobertura risco cambial: var. JV instrum. finan. (nota 3a))", 1646, D],
        ["Ganhos em ativos fixos tangíveis / Propriedades de Investimento", 1452, 568],
        ["Reversões de provisões", 681, 310],
        ["Subsídios à exploração", 381, 827],
        ["Subsídios ao investimento", 2130, 4612],
        ["Rendimentos suplementares", 2178, 3131],
        ["Rendimentos de imóveis", 524, 574],
        ["Trabalhos para a própria entidade", 1380, 2198],
        ["Outros", 7051, 5628],
        ["Outros rendimentos e ganhos", 17421, 17849],
     ]),
    ("N30b Outros gastos", "other_expenses", 30, "30. OUTROS RENDIMENTOS E GANHOS / OUTROS GASTOS E PERDAS",
     ["2025", "2024"], [
        ["Cobertura risco cambial: dif. câmbio (nota 3a))", 322, 611],
        ["Cobertura risco cambial: var. JV instrum. finan. (nota 3a))", D, 1716],
        ["Impostos", 2620, 2536],
        ["Provisões do período", 67, 365],
        ["Perdas em ativos fixos tangíveis / Propriedades de Investimento", 973, 99],
        ["Servíços bancários", 1010, 705],
        ["Dívidas incobráveis", 186, 248],
        ["Perdas em inventários", 56, 34],
        ["Donativos e quotizações", 1409, 1411],
        ["Outros", 6422, 3339],
        ["Outros gastos e perdas", 13065, 11064],
     ]),
    ("N31 Result. não recorrentes", "other_expenses", 31, "31. RESULTADOS NÃO RECORRENTES", ["2025", "2024"], [
        ["Os resultados não recorrentes dizem respeito à transferência da unidade industrial de Silves, principalmente "
         "indemnizações por rescisão e desmontagem de equipamentos, e recebimento de PERES no valor de 500 K€."],
        ["Encerramento de site industrial", -913, D],
        ["Gastos de reestruturação", D, -5366],
        ["Descontinuação de linha de produto", D, -9086],
        ["Reversão parcial de gastos de reestruturação", D, 2085],
        ["Mais-valia da alienação de subsidiárias", D, 13801],
        ["Outros resultados não recorrentes - imposto de selo", 500, D],
        ["Resultados não recorrentes", -413, 1434],
     ]),
    ("N22a Dívida corrente", "borrowings", 22, "22. DÍVIDA REMUNERADA", ["2025", "2024"], [
        ["No final do período, a dívida remunerada corrente tinha a seguinte composição:"],
        ["Descobertos e empréstimos bancários", 38156, 64807],
        ["Empréstimos por obrigacões", D, 30000],
        ["Locações", 2335, 2406],
        ["Factoring", D, 907],
        ["Papel comercial", D, 55150],
        ["Dívida remunerada corrente", 40491, 153270],
        ["Deste total cerca de 4,1% é denominada em divisa não euro (Dez. 2024: 4%)."],
     ]),
    ("N22b Dívida não corrente", "borrowings", 22, "22. DÍVIDA REMUNERADA", ["2025", "2024"], [
        ["A dívida remunerada não corrente tinha a seguinte composição:"],
        ["Empréstimos bancários", 3579, 4807],
        ["Locações", 2635, 2797],
        ["Papel comercial", 94150, 111450],
        ["Dívida remunerada não corrente", 100365, 119053],
        ["No final do período, 1,7% desta dívida era denominada em divisa não euro, sendo o remanescente em euro "
         "(Dez 2024: 100%)."],
        ["Da dívida remunerada, corrente e não corrente, 110,6 M€ vencem juros a taxa variável. Os 30,3 M€ de dívida "
         "remanescente vencem juros a taxa fixa. O custo médio registado no período para o conjunto das linhas de "
         "crédito utilizadas situou-se nos 2,58% (2024: 3,71%)."],
     ]),
    ("N22c Maturidade dívida", "borrowings_maturity", 22, "22. DÍVIDA REMUNERADA", ["2025"], [
        ["A 31 de dezembro de 2025, a maturidade da dívida remunerada não corrente era a seguinte:"],
        ["Vencimento entre 01/01/2027 e 31/12/2027", 37293],
        ["Vencimento entre 01/01/2028 e 31/12/2028", 663],
        ["Vencimento entre 01/01/2029 e 31/12/2029", 62352],
        ["Vencimento após 01/01/2030", 56],
        ["Total", 100365],
        ["À data de fecho de contas de 2025, a Corticeira Amorim tinha linhas de financiamento cuja documentação "
         "contratual de suporte incluía covenants genericamente usados neste tipo de contratos, nomeadamente: "
         "cross-default, pari passu e, em alguns casos, negative pledge. Não é esperado que a Corticeira Amorim tenha "
         "dificuldades em cumprir os covenants contratualizados."],
        ["Duas participadas da Corticeira Amorim no estrangeiro utilizam financiamentos em 31 de dezembro de 2025 (num "
         "total de cerca de 1,7 M€) aos quais estão associados covenants financeiros. Estes consubstanciavam-se, "
         "essencialmente, no cumprimento de rácios que permitem acompanhar a situação financeira das empresas, "
         "nomeadamente:"],
        ["- Asset coverage ratio – observação trimestral;"],
        ["- Fixed charge coverage ratio – observação anual;"],
        ["- Net income – observação anual;"],
        ["Os rácios acima mencionados não são limitativos e foram cumpridas integralmente as exigências constantes dos "
         "contratos que formalizavam os referidos financiamentos. Na eventualidade do seu não cumprimento, haveria a "
         "possibilidade de tal circunstância conduzir ao reembolso antecipado dos montantes tomados."],
        ["Para além do referido cumprimento, informa-se que a capacidade de assegurar o serviço de dívida estava ainda "
         "reforçada pela existência, à data de 31 de dezembro de 2025, de 326,1 M€ de linhas de crédito contratadas, "
         "mas não utilizadas."],
     ]),
    ("N3 Risco de liquidez", "borrowings_maturity", 3, "3. GESTÃO DE RISCO FINANCEIRO",
     ["Até 1 ano", "De 1 a 2 anos", "De 2 a 4 anos", "Mais de 4 anos", "Total"], [
        ["Os cash flows não descontados estimados por maturidade contratual para os passivos financeiros são como "
         "seguem:"],
        ["Dívida remunerada (nota 22)", 153270, 9271, 48416, 61366, 272323],
        ["Outros passivos financeiros (nota 24)", 51070, 2170, 3776, 706, 57722],
        ["Fornecedores (nota 23)", 112159, None, None, None, 112159],
        ["Total a 31 de dezembro de 2024", 316499, 11440, 52192, 62072, 442204],
        ["Dívida remunerada (nota 22)", 40491, 37293, 63016, 56, 140856],
        ["Outros passivos financeiros (nota 24)", 43264, 2103, 3457, 74, 48898],
        ["Fornecedores (nota 23)", 107945, None, None, None, 107945],
        ["Total a 31 de dezembro de 2025", 191701, 39396, 66472, 130, 297699],
        ["A Corticeira Amorim terminou o ano com linhas de crédito e programas de emissão de papel comercial não "
         "utilizados num total de 326,1 M€ (em 31 de dezembro de 2024 o valor comparável era de 302,9 M€). Se "
         "adicionarmos o caixa e equivalentes, a reserva de liquidez, no final de 2025, era de, 391,1 M€ (379,5 M€ em "
         "31 de dezembro de 2024)."],
     ]),
    ("N11 Direito de uso", "leases", 11, "11. DIREITO DE USO", ["Direito de uso"], [
        ["Valores brutos", 13584],
        ["Depreciações e ajustamentos", -8538],
        ["Abertura (1 de janeiro 2024)", 5046],
        ["Aumento", 1318],
        ["Depreciações / Imparidades", -1399],
        ["Diminuições-Alienações-Abates", -52],
        ["Reclass. / Out. Movim. / Ajust.", 324],
        ["Diferenças de conversão", 5],
        ["Valores brutos", 15179],
        ["Depreciações e ajustamentos", -9937],
        ["Fecho (31 de dezembro 2024)", 5242],
        ["Valores brutos", 15179],
        ["Depreciações e ajustamentos", -9937],
        ["Abertura (1 de janeiro 2025)", 5242],
        ["Aumento", 1084],
        ["Depreciações / Imparidades", -1610],
        ["Diminuições-Alienações-Abates", -353],
        ["Reclass. / Out. Movim. / Ajust.", 780],
        ["Diferenças de conversão", -2],
        ["Valores brutos", 16688],
        ["Depreciações e ajustamentos", -11547],
        ["Fecho (31 de dezembro 2025)", 5141],
     ]),
    ("N22d Locações", "leases", 22, "22. DÍVIDA REMUNERADA", ["2025", "2024"], [
        ["Os passivos de locação da Corticeira Amorim estão incluídos na dívida remunerada."],
        ["No final do período, a dívida remunerada corrente tinha a seguinte composição:"],
        ["Locações", 2335, 2406],
        ["A dívida remunerada não corrente tinha a seguinte composição:"],
        ["Locações", 2635, 2797],
     ]),
    ("N24a Out. passivos financ.", "other_financial", 24, "24. OUTROS PASSIVOS FINANCEIROS E OUTROS PASSIVOS",
     ["2025", "2024"], [
        ["Outros passivos financeiros"],
        ["Subsídios reembolsáveis", 5557, 6615],
        ["Outros credores diversos", 77, 37],
        ["Outros passivos financeiros não correntes", 5633, 6651],
        ["Subsídios reembolsáveis", 2624, 3503],
        ["Credores por acréscimo gastos - fornecimentos e serviços", 4686, 4441],
        ["Credores por acréscimo gastos - outros", 5282, 10439],
        ["IVA a pagar", 6907, 7426],
        ["Estado e S. Social - retenções e outros", 9291, 9066],
        ["Outros credores diversos", 14476, 16194],
        ["Outros passivos financeiros correntes", 43264, 51070],
        ["Em outros passivos financeiros está incluído o montante de 21 K€ (2024: 1 868 K€), o qual se refere ao valor "
         "dos derivados de cobertura de risco cambial."],
        ["O valor da rubrica de outros credores diversos – corrente – diz respeito essencialmente a remunerações a "
         "pagar no valor de 3 895 K€, adiantamento a clientes no valor de 1 968 K€ e credores por recuperação de "
         "gastos no valor de 2 836 K€."],
        ["O valor de 5 633 K€ de Outros passivos financeiros – Não correntes tinha o seu vencimento de 1 a 2 anos "
         "(2 103 K€), de 2 a 4 anos (3 457K€) e a mais de 4 anos (74 K€)."],
     ]),
    ("N24b Outros passivos", "other_financial", 24, "24. OUTROS PASSIVOS FINANCEIROS E OUTROS PASSIVOS",
     ["2025", "2024"], [
        ["Outros passivos"],
        ["Subsídios não reembolsáveis", 7475, 7831],
        ["Rendimentos a reconhecer", 2019, 810],
        ["Credores por acréscimo gastos - remunerações a liquidar", 17117, 19392],
        ["Outros passivos correntes", 26612, 28033],
        ["Em outros passivos não correntes, está reconhecida a componente não corrente de remunerações a líquidar "
         "relativa à política de remunerações da Corticeira Amorim aprovada em 2024."],
     ]),
    ("N24c Subsídios não reemb.", "other_financial", 24, "24. OUTROS PASSIVOS FINANCEIROS E OUTROS PASSIVOS",
     ["2025", "2024"], [
        ["Os saldos relativos a subsídios evoluíram do seguinte modo:"],
        ["Subsídios não reembolsáveis"],
        ["Saldo inicial", 7831, 5873],
        ["Reconhecimento de rendimentos no exercício", -2113, -4612],
        ["Recebimentos", 1757, 2952],
        ["Reclassificações / Transferências / Entradas", D, 3619],
        ["Saldo final", 7475, 7831],
     ]),
    ("N24d Subsídios reembolsáveis", "other_financial", 24, "24. OUTROS PASSIVOS FINANCEIROS E OUTROS PASSIVOS",
     ["2025", "2024"], [
        ["Subsídios reembolsáveis"],
        ["Saldo inicial", 10118, 12177],
        ["Pagamentos do exercício", -2149, -2480],
        ["Recebimentos do exercício", 216, 4054],
        ["Reclassificações / Transferências", -4, -3634],
        ["Saldo final", 8181, 10118],
        ["O valor de transferências é essencialmente relativo a montantes de benefícios reembolsáveis entretanto "
         "convertidos para não reembolsáveis em algumas subsidiárias e ao reconhecimento do juro pela mensuração a "
         "custo amortizado."],
     ]),
    ("N14 Outros ativos financ.", "other_financial", 14, "14. OUTROS ATIVOS FINANCEIROS", ["2025", "2024"], [
        ["Instrumentos financeiros derivados", 93, 111],
        ["IVA a receber", 17600, 21740],
        ["IS/IVA - Pagamento PERES", 294, 1436],
        ["IS/IVA - Pagamento PERES imparidade", -294, -1436],
        ["Investimentos em fundos, seguros de capitalização e similares", 9948, 6192],
        ["Outros", 9416, 12515],
        ["Outros ativos financeiros correntes", 37057, 40558],
        ["Os Investimentos em fundos, seguros de capitalização e similares referem-se essencialmente a seguros de "
         "capitalização do Grupo SACI, Industria Corchera e Corpack Bourrasse. Estes seguros (apólices de seguro "
         "associadas a fundos de investimento) são investimentos de curto prazo, podendo ser alienados quando "
         "necessário sem algum constrangimento em particular."],
        ["Os ativos incluídos na rubrica de outros ativos financeiros não corrente (31 dezembro 2025: 2 205 K€, "
         "31 dezembro 2024: 1 640 K€) referem-se a ativos financeiros ao justo valor através de resultados, incluindo "
         "essencialmente instrumentos de capital próprio."],
        ["A rubrica outros tem diz respeito essencialmente a devedores por recuperação de gastos (2,5 M) e outros "
         "devedores diversos (6,8 M€)."],
     ]),
    ("N25a Provisões", "provisions", 25, "25. PROVISÕES", ["2025", "2024"], [
        ["Contingências fiscais", 101, 127],
        ["Garantias a clientes", 631, 1300],
        ["Outros", 2806, 4263],
        ["Provisões", 3539, 5691],
        ["As Outras contingências incluem essencialmente provisões para cessação de emprego (1,4 M€), processos em "
         "curso (0,5 M€) e outras provisões (0,9 M€)."],
     ]),
    ("N25b Provisões mov. 2025", "provisions", 25, "25. PROVISÕES", PROV_HEADER, [
        ["Saldo inicial 2025", None, 62, 66, 1300, 4263, 5691],
        ["Constituição", "Outros gastos - Nota 30", D, D, D, 67, 67],
        ["Constituição", "Reestruturação", D, D, D, D, D],
        ["Constituição", "Outros", D, D, D, 159, 159],
        ["Reversão", "Outros rendimentos - Nota 30", D, D, D, -599, -599],
        ["Reversão", "Reestruturação", D, D, D, -443, -443],
        ["Reversão", "Outros", D, -26, -668, -749, -1444],
        ["Diferença conversão cambial", None, D, D, D, 108, 108],
        ["Utilização", None, D, D, D, D, D],
        ["Saldo final 2025", None, 62, 39, 631, 2806, 3539],
        ["No exercício findo em 31 de dezembro de 2025, a rubrica de garantias a clientes (que são essencialmente da "
         "Amorim Cork Solutions) diminuiu em 668 K€, sendo contabilizadas de acordo com a IAS 37 Provisões, Passivos "
         "Contingentes e Ativos Contingentes."],
     ]),
    ("N25c Provisões mov. 2024", "provisions", 25, "25. PROVISÕES", PROV_HEADER, [
        ["Saldo inicial 2024", None, 62, 2, 477, 7402, 7942],
        ["Constituição", "Outros gastos - Nota 30", D, D, D, 365, 365],
        ["Constituição", "Imposto sobre o rendimento", D, 93, D, None, 93],
        ["Constituição", "Reestruturação", D, D, D, 443, 443],
        ["Constituição", "Outros", D, D, 823, 1061, 1884],
        ["Reversão", "Outros rendimentos - Nota 30", D, D, D, -310, -310],
        ["Reversão", "Reestruturação", D, D, D, 2085, 2085],
        ["Reversão", "Outros", D, -29, D, -751, -779],
        ["Diferença conversão cambial", None, D, D, D, 32, 32],
        ["Utilização", None, D, D, D, -6063, -6063],
        ["Saldo final 2024", None, 62, 66, 1300, 4263, 5691],
     ]),
    ("N35 Garantias", "contingencies", 35, "35. OUTRAS INFORMAÇÕES - e. Garantias", ["Montante", "Motivo"], [
        ["No decurso da sua atividade operacional, a Corticeira Amorim prestou garantias a terceiros que ascendiam em "
         "31/12/2025 a 272 K€ (Dez. 2024: 262 K€)."],
        ["Agências Governamentais", 77, "Apoios a investimentos"],
        ["Diversos", 195, "Diversos"],
        ["TOTAL", 272, None],
        ["Os compromissos relativos à compra de cortiça atingem os 15 716€ (2026: 11 633 K€; 2027: 1 602 K€, 2028: "
         "1 172 K€ e 2029 e seguintes 1 308 K€)."],
        ["Adicionalmente foram prestadas garantias pelas subsidiárias, não relacionadas com financiamentos, e que "
         "ascendiam à data de 31.12.2025 ao valor de 734 K€."],
     ]),
    ("N15 Contingências fiscais", "contingencies", 15,
     "15. IMPOSTOS DIFERIDOS / IMPOSTO SOBRE O RENDIMENTO / IMPOSTO SOBRE OS RESULTADOS - Provisões para contingências "
     "fiscais", [], [
        ["As provisões para contingências fiscais em sede de imposto sobre o rendimento finalizaram com um valor de "
         "26,7 M€ (31.12.2024: 33,1 M€). Durante o exercício as contingências para impostos a pagar na demonstração da "
         "posição financeira diminuíram em 6,4 M€."],
        ["Os processos que continuam em aberto, tanto em fase judicial, como em fase graciosa, e que podem afetar "
         "desfavoravelmente a Corticeira Amorim estão cobertos por provisões. As autoridades fiscais portuguesas têm "
         "em curso a inspeção tributária ao exercício de 2023 para algumas das subsidiárias portuguesas pertencentes "
         "ao RETGS."],
        ["O principal aumento da rubrica de provisões para contingências fiscais relaciona-se com a provisão para "
         "fazer face aos benefícios fiscais de 2025 tendo tido um aumento de 3,1 M€. A redução do ano da provisão para "
         "benefícios fiscais foi de 9,4 M€. A provisão para benefícios fiscais no final de 2025 apresenta o valor de "
         "26,7 M€."],
        ["Não existem processos fiscais não provisionados, pelo que, desta forma, os passivos contingentes são nulos."],
     ]),
    ("N33 Entidades relacionadas", "related_parties", 33, "33. SALDOS E TRANSAÇÕES COM ENTIDADES RELACIONADAS", [], [
        ["A Corticeira Amorim consolida diretamente na Amorim – Investimentos e Participações, S.G.P.S., S.A. com sede "
         "em Mozelos (Santa Maria da Feira), holding do Grupo Amorim."],
        ["A 31 de dezembro de 2025 a participação do Amorim – Investimentos e Participações, S.G.P.S., S.A. na "
         "Corticeira Amorim era de 51%, correspondente a 51% dos direitos de voto."],
        ["As transações da Corticeira Amorim com empresas relacionadas resumem-se, no essencial, à prestação de "
         "serviços por parte de subsidiárias da Amorim – Investimentos e Participações, S.G.P.S., S.A. O total das "
         "prestações de serviços destas empresas ao conjunto das empresas da Corticeira Amorim foi de 650 K€ "
         "(Dez. 2024: 605 K€)."],
        ["As compras de amadia efetuadas no exercício a empresas detidas pelos principais acionistas indiretos da "
         "Corticeira Amorim atingiram o valor de 1 296 K€ (Dez. 2024: 2 286 K€), correspondendo a menos de 2% das "
         "compras totais da matéria-prima cortiça."],
        ["Os saldos a 31 de dezembro de 2025 e de 2024 são os decorrentes do período normal de pagamento (entre 30 e "
         "60 dias) e por isso considerados imateriais."],
        ["Os serviços são normalmente negociados com as entidades relacionadas numa base de cost plus num intervalo "
         "entre 2% e 5%."],
        ["O total de remunerações de curto prazo do pessoal-chave (inclui comissão executiva da SGPS e diretores "
         "gerais das Unidades de Negócios) da Corticeira Amorim atingiu no exercício o valor de 4 700 K€ (2024: "
         "8 090 K€). O valor de benefícios pós-emprego, outros benefícios de longo prazo, benefícios de cessação de "
         "emprego e de pagamentos com base em ações, excluindo a parte referida na nota 28, é nulo."],
     ]),
    ("N7a Segmentos 2025", "segments", 7, "7. RELATO POR SEGMENTOS", SEG_HEADER, [
        ["2025"],
        ["Vendas clientes exterior", 7038, 691560, 161031, 1339, D, 860967],
        ["Vendas outros segmentos", 215230, 15431, 974, 16375, -248011, D],
        ["Vendas totais", 222269, 706991, 162005, 17714, -248011, 860967],
        ["Custo das vendas", -173747, -359317, -71429, -223, 230233, -374484],
        ["Fornecimento e serviços externos", -16797, -100716, -29485, -13074, 19554, -140517],
        ["Custos com pessoal", -19936, -122323, -37718, -10794, 60, -190711],
        ["EBITDA (*)", 13979, 113008, 13772, -4786, 5012, 140985],
        ["Ativo não corrente", 97645, 303173, 89780, 7746, 26170, 524515],
        ["Ativo corrente", 196094, 426857, 90092, 5441, -32095, 686388],
        ["Passivo", 51133, 161748, 60099, 100455, -2841, 370592],
        ["Investimento tangível e intangível", 5406, 29169, 7488, 769, D, 42832],
        ["Depreciações", -6582, -37625, -14039, -649, D, -58895],
        ["Ganhos (perdas) em associadas", 0, 2147, -257, -1, D, 1888],
        ["Ajustamentos = desempolamentos inter-segmentos e valores não alocados a segmentos."],
        ["(*)EBITDA = Resultado operacional antes de depreciações/amortizações e resultados não recorrentes"],
     ]),
    ("N7b Segmentos 2024", "segments", 7, "7. RELATO POR SEGMENTOS", SEG_HEADER, [
        ["2024"],
        ["Vendas clientes exterior", 8339, 717449, 212159, 1115, D, 939061],
        ["Vendas outros segmentos", 223287, 14848, 912, 17697, -256744, D],
        ["Vendas totais", 231626, 732296, 213071, 18812, -256744, 939061],
        ["Custo das vendas", -185456, -382372, -114969, -147, 239072, -443873],
        ["Fornecimento e serviços externos", -17844, -100264, -39800, -14511, 20918, -151501],
        ["Custos com pessoal", -19077, -117351, -43129, -13731, 97, -193191],
        ["EBITDA (*)", 11470, 142334, 14161, -9971, -428, 157566],
        ["Ativo não corrente", 101360, 316595, 89710, 11643, 31068, 550376],
        ["Ativo corrente", 254558, 479762, 75700, 17155, -15357, 811818],
        ["Passivo", 61986, 192443, 72549, 206671, -6512, 527137],
        ["Investimento tangível e intangível", 8374, 27454, 6503, 709, D, 43040],
        ["Depreciações", -6488, -36574, -13927, -648, D, -57636],
        ["Ganhos (perdas) em associadas", D, 4389, -81, -3, D, 4305],
        ["Ajustamentos = desempolamentos inter-segmentos e valores não alocados a segmentos."],
        ["(*)EBITDA = Resultado operacional antes de depreciações/amortizações e resultados não recorrentes"],
     ]),
    ("N7c Vendas por mercado", "segments", 7, "7. RELATO POR SEGMENTOS - Distribuição das vendas por mercado",
     ["2025", "2025 (%)", "2024", "2024 (%)"], [
        ["Mercados"],
        ["União Europeia", 578984, 67.2, 637356, 67.9],
        ["dos quais: Portugal", 59865, 7.0, 58790, 6.3],
        ["Resto da Europa", 24290, 2.8, 29133, 3.1],
        ["EUA", 136677, 15.9, 151893, 16.2],
        ["Resto da América", 59402, 6.9, 59394, 6.3],
        ["Austrália/ Ásia", 47255, 5.5, 46999, 5.0],
        ["África", 14360, 1.7, 14287, 1.5],
        ["Total", 860967, 100, 939061, 100],
     ]),
    ("N28 Gastos com pessoal", "staff", 28, "28. GASTOS COM PESSOAL", ["2025", "2024"], [
        ["Remunerações dos Órgãos Sociais", 2521, 5260],
        ["Remunerações do pessoal", 144557, 146224],
        ["Encargos sobre remunerações", 30592, 29792],
        ["Indemnizações", 2013, 1077],
        ["Benefícios pós-emprego", 1216, 1212],
        ["Outros custos com o pessoal", 9863, 9657],
        ["Gastos capitalizados", -51, -31],
        ["Gastos com pessoal", 190711, 193191],
        ["Número médio de trabalhadores", 4699, 4866],
        ["Número de trabalhadores no final do período", 4637, 4849],
     ]),
]

# The consolidated statements, as printed (to check the totals of the notes): sheet, label, values after the label
STATEMENTS = [
    ("N30a Outros rendimentos", "Outros rendimentos e ganhos", [17421, 17849]),
    ("N31 Result. não recorrentes", "Resultados não recorrentes", [-413, 1434]),
    ("N22a Dívida corrente", "Dívida remunerada corrente", [40491, 153270]),
    ("N22b Dívida não corrente", "Dívida remunerada não corrente", [100365, 119053]),
    ("N22c Maturidade dívida", "Total", [100365]),
    ("N24a Out. passivos financ.", "Outros passivos financeiros não correntes", [5633, 6651]),
    ("N24a Out. passivos financ.", "Outros passivos financeiros correntes", [43264, 51070]),
    ("N24b Outros passivos", "Outros passivos correntes", [26612, 28033]),
    ("N14 Outros ativos financ.", "Outros ativos financeiros correntes", [37057, 40558]),
    ("N25a Provisões", "Provisões", [3539, 5691]),
    ("N11 Direito de uso", "Fecho (31 de dezembro 2025)", [5141]),
    ("N28 Gastos com pessoal", "Gastos com pessoal", [190711, 193191]),
    ("N7a Segmentos 2025", "Vendas totais", [222269, 706991, 162005, 17714, -248011, 860967]),
    ("N7b Segmentos 2024", "Vendas totais", [231626, 732296, 213071, 18812, -256744, 939061]),
]
# Lines that must add up to the printed total (a check on the copying): sheet, first line, last line before the total
SUMS = [
    ("N30a Outros rendimentos", 0, 10), ("N30b Outros gastos", 0, 10), ("N31 Result. não recorrentes", 1, 7),
    ("N22a Dívida corrente", 1, 6), ("N22b Dívida não corrente", 1, 4), ("N22c Maturidade dívida", 1, 5),
    ("N24a Out. passivos financ.", 1, 3), ("N24a Out. passivos financ.", 4, 10), ("N24b Outros passivos", 1, 4),
    ("N14 Outros ativos financ.", 0, 6), ("N25a Provisões", 0, 3), ("N28 Gastos com pessoal", 0, 7),
    ("N7c Vendas por mercado", None, None),
]
TOLERANCE = 2  # thousand euros: the report rounds each line


def _num(value):
    return value if isinstance(value, (int, float)) else 0


def check():
    """The copied lines add up to the printed totals and the totals are the ones in the consolidated statements."""
    by_sheet = {note[0]: note[5] for note in NOTES}
    problems = []
    for sheet, label, expected in STATEMENTS:
        if not any(row[0] == label and row[1:] == expected for row in by_sheet[sheet]):
            problems.append(f"{sheet}: '{label}' is not {expected}")
    for sheet, first, last in SUMS:
        rows = by_sheet[sheet]
        if first is None:  # sales by market: 'dos quais' is a part of the line above
            lines, total = [row for row in rows[1:-1] if not row[0].startswith("dos quais")], rows[-1]
            columns = (1, 3)
        else:
            lines, total = rows[first:last], rows[last]
            columns = range(1, len(total))
        for column in columns:
            difference = sum(_num(row[column]) for row in lines) - _num(total[column])
            if abs(difference) > TOLERANCE:
                problems.append(f"{sheet}: column {column} of '{total[0]}' differs by {difference}")
    for sheet in ("N25b Provisões mov. 2025", "N25c Provisões mov. 2024"):  # opening + movements = closing
        rows = [row for row in by_sheet[sheet] if len(row) > 1]
        for column in range(2, 7):
            difference = sum(_num(row[column]) for row in rows[:-1]) - _num(rows[-1][column])
            if abs(difference) > TOLERANCE:
                problems.append(f"{sheet}: column {column} does not close, differs by {difference}")
    return problems


def write(path):
    workbook = Workbook()
    index = workbook.active
    index.title = "Index"
    index.append(["Sheet", "Topic", "Note", "Title as printed", "Page", "Unit", "Status"])
    for sheet, topic, note, title, header, rows in NOTES:
        if len(sheet) > 31:
            raise ValueError(f"sheet name too long: {sheet}")
        index.append([sheet, topic, note, title, f"note {note} (ESEF report, no page)", UNIT, "read"])
        page = workbook.create_sheet(sheet)
        page["A1"] = title
        page["A2"] = SOURCE.format(note)
        page["A3"] = UNIT
        for column, value in enumerate(["Item"] + header, start=1):
            page.cell(row=5, column=column, value=value)
        for number, row in enumerate(rows, start=6):
            for column, value in enumerate(row, start=1):
                if value is not None:
                    page.cell(row=number, column=column, value=value)
        page.column_dimensions["A"].width = 60
    index.column_dimensions["A"].width = 32
    index.column_dimensions["D"].width = 60
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def main():
    problems = check()
    for problem in problems:
        print("CHECK FAILED:", problem)
    if problems:
        return 1
    path = Path(__file__).resolve().parent.parent / "data" / "notes" / "Corticeira_Amorim_2025_notes.xlsx"
    write(path)
    print(f"{path}: {len(NOTES)} note sheets, checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
