# Fase 6 — desenho final (para o Opus implementar)

Especificação, não código. Substitui a secção 3 da `docs/FASE5_DESIGN.md` (cor e símbolos) e acrescenta o resto. Textos do produto em inglês. Todos os números continuam a vir do motor e a passar pelo memo-checker. Sem Go/No-Go.

## 1. Diagnóstico (capturas de 16 de novembro de 2026: app a 1440 e 375 px, site a 1440 px)

1. **Topo cortado.** O seletor começa aos 38 px e a barra do Streamlit ocupa os primeiros 60 px; na cloud, os botões dela ficam por cima do seletor. A 375 px o topo gasta 250 px antes do score.
2. **Sem cor.** Em todo o Summary só há três triângulos vermelhos de 10 px. Medium (●) e o texto têm a mesma cor; os KPIs são todos brancos, incluindo −€272m.
3. **Top 5 da TAP com 3 itens que não são achados:** leasings (standard), receita diferida (NWC) e R11.
4. **R11 é um facto antigo.** "€450m, High" refere-se a FY23 (69,3%); em FY25 são 2,8% (€20m). O montante usa o último ano em que a regra disparou (`issues.py:167`), não o último ano.
5. **Score repetido** (faixa e 4.º KPI) e sem explicação visível: a fórmula está num popover de um parágrafo.
6. **Símbolos sem legenda, e ○ com dois sentidos** (Low nos achados, "blocked" na cobertura). "–" não diz nada.
7. **"When" repete "Protection"** (Completion accounts / Completion accounts).
8. **Gráficos estreitos:** 502, 318 e 688 px num contentor de 1120 px; o de valuation tem 3 barras num cartão alto.
9. **Evidence é texto:** 14 linhas "request more information" e 7 perguntas longas abertas por defeito.
10. **Site:** verificação com 4 números de 28 px no fim da página; os cartões de empresa não distinguem 54 de 32.

## 2. Severidade, materialidade e score

**O que a pesquisa diz.** Não existe um limiar público de FDD: o âmbito e o formato do relatório são acordados com o cliente (ICAEW, Guideline 71, escrita pela PwC) [1]. Os números do mercado são percentagens do preço: mais de metade dos *baskets* fica em 0,5% do valor do negócio ou menos (SRS Acquiom, via Fasken) [2]; uma grelha de fornecedor usa <2% / 2–10% / >10% do EV [3]. Sem preço (modo outside-in), a âncora defensável é a dos auditores: 5% do resultado antes de impostos como exemplo da ISA 320 e 0,5–1% das vendas na prática [4]. **Decisão: manter 5% do EBITDA reportado (itens de resultados) e 1% das vendas (itens de balanço); quando o utilizador der um EV, usar 1% do EV para os dois.** TAP: €36m e €43m.

| Marca | Nome | Critério (camada `issues`, não `rules.evaluate`) | Frase visível |
|---|---|---|---|
| ▲ vermelho | High | Regra High do livro de regras, disparada no **último ano**, montante ≥ materialidade ou não quantificável | Could change the price or the terms |
| ● âmbar | Medium | Regra Medium, disparada no último ano, ≥ materialidade | Needs an answer before signing |
| ○ cinzento | Low | Regra Low; ou qualquer achado abaixo da materialidade; ou **histórico** (só disparou em anos anteriores) | Note it; no action yet |
| etiqueta | Debt-like · To assess · Standard | Item de balanço; nenhuma regra disparou. Não tem severidade | — |

**Porque os leasings não são High:** a severidade mede uma anomalia (uma regra disparou); os leasings não são anomalia, são um item que qualquer comprador deduz e que a nota 19 explica. Tamanho vai na coluna do montante; severidade é outra pergunta. O EBITDA é pós-IFRS 16, por isso o múltiplo já pressupõe a dedução [5].

**Score: validado com duas correções.** A estrutura severidade × materialidade × evidência fica: é determinística e publicada (o dd-agents mostra "62/100 — High" e "Conditional Go" sem fórmula [6]). Limite conhecido: multiplicar escalas ordinais não dá uma medida de risco (Cox 2008; Krisper 2021) [7]. Por isso o score é um índice de triagem, mostra-se sempre decomposto e nunca ordena empresas nem achados (a ordem é pelo montante).
- **Correção 1, só o último ano:** um achado que só disparou em anos anteriores é *historical*: fica em Findings com o chip "Historical · FY23" e severidade Low, mas sai do score e do top. É o caso da R11 da TAP (69,3% em FY23, 2,8% em FY25).
- **Correção 2, faixas com palavra:** 0–24 *Few open points* (verde) · 25–59 *Several open points* (âmbar) · 60–100 *Many open points* (vermelho).

`points = severity (3·2·1) × materiality (1 · 0.75 · 0.5) × evidence (1 · 0.75 · 0.5)`, só para issues do último ano; `score = min(100, points ÷ 30 × 100)`.

**Exemplo da TAP (antes, 54):** R07 3 + R11 2,25 + R28 2 + R24 2 + R30 2 + R22 1 + Provisions 1 + R25 1 + Assets held for sale 1 + Other financial assets 1 = 16,25 pontos; 16,25 ÷ 30 = 54. Sem a R11 (histórica): 14 pontos, score 47. Por área: Net debt 13,3 · Working capital 16,7 · Quality of earnings 6,7 · Cash flow 6,7 · Tax 3,3.

**Texto para um não especialista (na app):** *"Each open question in the latest year gets points: how serious, how big, how unexplained. 30 points = 100. It is a to-do meter for the diligence, not a grade for the company."*
**Para um entrevistador:** "É um índice de triagem, determinístico e decomposto ao ponto. Sei que multiplicar escalas ordinais é criticado, por isso não o uso como probabilidade nem para ordenar: a ordem dos issues é pelo montante em causa, e 100 corresponde a dez achados High, materiais, abertos e atuais."

## 3. Sistema visual

| Token | Hex | Uso |
|---|---|---|
| bg · card · line | `#0d1117` · `#161b22` · `#30363d` | fundo, cartões, linhas |
| text · muted | `#e6edf3` · `#8b949e` | texto, rótulos e fontes |
| red | `#f85149` | pior para o comprador: High, aumenta net debt, reduz valor, número negativo de caixa, falha |
| green | `#3fb950` | melhor / bate certo: check passado, reduz net debt, caixa positiva, "explained" |
| amber | `#d29922` | só Medium, faixa média do score e "partly explained" |
| accent | `#58a6ff` | só interação: separador ativo, links, slider. Nunca num número |
| tints | cor a 12% no fundo, a 40% no contorno | cartões e chips tingidos |

Vermelho e verde seguem o significado e não o sinal, e a cor fica reservada ao que importa (IBCS) [8].

| Componente | Cor |
|---|---|
| Cartão de achado, linha do Top 5 | barra esquerda de 3 px e fundo tingido pela severidade |
| Chip de severidade / evidência | tingido: High vermelho, Medium âmbar, Low cinzento; open vermelho, partly âmbar, explained verde |
| KPI | número vermelho se a regra ligada disparou (Leverage ↔ R21, cover ↔ R22) ou se a caixa é negativa; verde se positivo/passou; net debt sempre neutro |
| Score | número e marcador na cor da faixa |
| Pontes | como hoje; item standard a cinzento |
| Grelha de cobertura | ✓ verde · □ cinzento · – cinzento-escuro |

**Tipografia:** Inter; Source Serif 4 só nos action titles. 56 (score) · 32 (KPI) · 22 (action title) · 15 (corpo) · 13 (rótulos). `tabular-nums`.
**Legenda (uma linha fixa, por baixo do herói no Summary e dos filtros em Findings):** `▲ High · could change price or terms   ● Medium · answer before signing   ○ Low · note it   [Debt-like] [To assess] [Standard] balance sheet items, no rule fired`. Em Evidence: `✓ run   □ blocked: a document is missing   – not applicable`. O "blocked" passa de ○ para □ em todo o lado (app, site, databook, `deal_layer.md`).

## 4. App

**Topo (prioridade 1), por ordem:**
1. Esconder a barra do Streamlit (`[data-testid="stHeader"]{display:none}`), `padding-top:16px`.
2. **Barra da app** (56 px, fixa): à esquerda "DD Assistant" e três pills de empresa (TAP · Toyota · Amorim; substituem o selectbox); à direita `FY25 · €m · Published accounts` em 13 e o botão **Download databook**. A 375 px: pills numa linha com scroll, botão só com ícone.
3. **Separadores** Summary · Findings · Impact · Evidence, numa só linha também a 375 px, ativo em accent.
4. **Herói** (cartão a toda a largura, tingido pela faixa do score), três colunas:
   - *Esquerda:* score a 56 na cor da faixa, `/ 100`, a palavra da faixa e "Finding intensity, not a recommendation".
   - *Centro:* barra empilhada 0–100 com os cinco segmentos de área (somam o score), rótulo e pontos por segmento; por baixo, a frase para não especialista e o link **How the score is built** (abre a tabela: issue · severity × materiality × evidence · points · total ÷ 30).
   - *Direita:* três contadores tingidos, `2 ▲ High` · `6 ● Medium` · `1 ○ Low`, e `22 / 30 rules run`.

| Vista | Secções, por ordem | 5 s | 30 s | 2 min |
|---|---|---|---|---|
| **Summary** | Herói · 4 KPIs (Adjusted net debt · Leverage · Free cash flow after leases · **Reading checks 10 of 10** a verde; sai o KPI "Risk score") · legenda · **Top deal issues** (4 colunas: marca · issue · amount · protection or next step; sai "When") · faixa **Already in the price** (leasings €2,158m · receita diferida €711m · NWC contra o peg, cada um com 1 linha de razão, a cinzento) | score, cor, onde pesa | os cinco issues e o que já está no preço | abrir um issue |
| **Findings** | Filtros · legenda · cartões tingidos; fechado: marca · ID · título · montante · chip de evidência; aberto: como hoje, com a regra num `expander` e o chip **Historical FY23** quando aplicável | quantos vermelhos | evidência citada de um achado | decisão do revisor |
| **Impact** | Ponte de net debt (largura total) · duas colunas: impacto de diligence em barras horizontais com slider \| tabela "Already in the price" · ponte de caixa (largura total) | action title | o que conta e o que não conta | mover o slider |
| **Evidence** | Grelha de cobertura com legenda · 3 contadores de open items (fechados) · ações em 4 colunas, **agrupadas por ação** ("Request more information · 6" com os nomes em chips) · encaminhamentos como chips por workstream, pergunta ao clicar · downloads | 22 de 30 | o que falta pedir | descarregar |

**Top deal issues, regra nova:** só achados e itens "To assess"/"Debt-like" de diligence, do último ano. Entram primeiro todos os High abertos (máx. 5), depois completa-se pelo montante; mostra-se por montante. TAP esperada: R28 €631m · Provisions €415m · R22 €196m · Pensions €173m · R07 €63m (▲).
**Gráficos:** SVG a 100% do contentor (altura máx. 360 px); action title ≤ 70 caracteres, por exemplo "Leases are €2,158m of TAP's €2,293m net debt; diligence adds €177m".

## 5. Site

**Página inicial:** 1. Hero (como hoje, com uma captura do topo novo da app à direita) · 2. Três cartões: score na cor da faixa, barra empilhada por área, adjusted net debt, action title · 3. **How it is verified** logo a seguir, grelha 4×2, número a 48 px (verde quando é 100%), uma linha de rótulo e, em 13, o comando ou ficheiro que o prova · 4. "How the score works" em 3 passos com o exemplo da TAP · 5. Limites · rodapé.

| Número (calculado no build por `demo.verification()`, nunca escrito à mão) | Prova |
|---|---|
| **304** automated tests, all passing | `python -m unittest` |
| **30** rules, each with threshold, source and plain-language reason | `python -m dd_assistant --rules` |
| **100%** of figures traced to a cell, page or tag (novo: linhas lidas com fonte ÷ linhas lidas) | `CompanyData.sources` |
| **415** memo figures checked, **0** without a source | `--check-memo` · `docs/examples/*/memo_check.md` |
| **10 of 10** published subtotals rebuilt to the euro | reading checks · `tests/test_real_companies.py` |
| **48 of 49** planted distortions detected (o "1 missed: TAP, M18" a vermelho, com link) | `docs/DETECTION.md` |
| **0** false alarms on the clean company | `tests/test_clean_company.py` |
| **18 of 18** databook totals: Excel = Python | folha Checks · `tests/test_databook.py` |

**Página de empresa:** herói igual ao da app · Top 3 (a mesma regra nova) · faixa "Already in the price" · ponte de net debt a toda a largura · grelha de cobertura com legenda · botão para a app.

## 6. Alterações ao motor (métricas e regras não mudam; paridade e Velmora não mudam)

1. **Erro encontrado (R11 da TAP):** o 4.º top issue (€450m, High) vem de FY23; em FY25 a dívida a menos de um ano é 2,8% (€20m). `issues.amount_at_stake` usa o último ano em que a regra disparou. Correção: `RuleResult.historical` e `KeyIssue.historical` = a regra não disparou no último ano com valor; histórico → Low, nota "historical: fired in FY23, not in FY25", montante rotulado com o ano. Fora do score e do top. **Teste novo** (`tests/test_deal_layer.py`): nenhum issue do top 5 nem nenhuma linha do score tem `historical`, e o ano de cada achado do top é o último ano; na TAP a R11 está em Findings como histórica.
2. `deal_layer.risk_score`: só issues do último ano; `band` (palavra e cor); contagem por severidade; `lines` com título e os três fatores; `SCORE_FORMULA` atualizada.
3. `deal_layer.top_issues`: regra da secção 4. Novo `in_price(a)`: itens standard, itens de working capital e o NWC contra o peg, com a razão (`NOT_COUNTED_WHY`).
4. `Coverage.status`: "blocked □". `charts.py`: `AMBER`, `ACCENT`, tints; SVG a 100%; títulos ≤ 70 caracteres.
5. `demo.verification()`: os oito números da secção 5; `tests/test_site.py` compara cada um com uma contagem feita no teste.
6. Regenerar databooks, `deal_layer.md`, slides, site e imagens; correr o memo-checker nos três memos (o score e o top mudam na secção 1c do material) e corrigir o memo se citar o valor antigo.

## 7. Critérios de aceitação (capturas por `scripts/demo_review.py`, 1440×900 e 375×812, três empresas)

1. Nenhum elemento da app fica por baixo de outro no topo: o primeiro elemento começa a ≤ 24 px e a barra do Streamlit não existe no DOM visível (local e cloud).
2. Summary a 1440×900 sem scroll: barra, separadores, herói, 4 KPIs, legenda e Top issues. A 375 px o score aparece nos primeiros 320 px.
3. Na TAP, o Top não contém "Lease liabilities", "Deferred revenue" nem R11; os três estão em "Already in the price" ou marcados Historical.
4. O score aparece uma vez por ecrã; a soma dos segmentos da barra é igual ao score; a tabela de linhas soma os pontos mostrados.
5. Cada ecrã com marcas tem a legenda visível; ○ nunca significa "blocked"; "–" não aparece sozinho.
6. Cor: só os tokens da secção 3 (teste no CSS e nos SVG); cada vermelho, verde ou âmbar corresponde à tabela de uso (teste: KPI vermelho ⇔ regra ligada disparou ou valor negativo).
7. A coluna "When" não existe; nenhuma ação repetida mais de uma vez em Evidence.
8. Cada SVG de ponte ocupa ≥ 95% da largura do contentor a 1440 px; títulos ≤ 70 caracteres.
9. Site: 8 números de verificação, cada um com a prova ao lado e igual à contagem do teste.
10. Suite completa OK; paridade e Velmora (0 alertas, score 0) sem mudança; "Go", "No-Go", "recommend" e "should buy" continuam ausentes.

## Fontes

[1] ICAEW, *Financial due diligence* (Best-Practice Guideline 71, 2024): https://www.icaew.com/technical/corporate-finance/guidelines/financial-due-diligence-guideline-71 (li o resumo; o PDF não abriu em texto)
[2] Fasken, *Key takeaways: SRS Acquiom M&A Deal Terms Study*: https://fasken.com/en/knowledge/2020/05/20-key-takeaways-srs-acquioms-2020-ma-deal-terms-study · CMS European M&A Study 2026: https://cms.law/en/int/publication/cms-european-m-a-study-2026
[3] Peony, *Due diligence red flags* (convenção de um fornecedor): https://www.peony.ink/blog/due-diligence-red-flags
[4] ISA 320, material de aplicação: https://www.charteredaccountants.ie/chariotindex/text/apb_isa_320_2010/12.html · CPA Ireland, *Materiality and its practicalities*: https://www.cpaireland.ie/CPAIreland/media/Education-Training/Study%20Support%20Resources/P1%20Auditing/Relevant%20Articles/materiality-and-its-practicalities.pdf
[5] FTI Consulting, *Valuation implications of IFRS 16*: https://www.fticonsulting.com/insights/articles/valuation-implications-ifrs-16 · Baker Tilly, *Lease accounting in M&A*: https://bakertillysr.nz/news/lease-accounting/
[6] dd-agents, sample report: https://zoharbabin.com/due-diligence-agents/sample-report/
[7] Cox (2008), "What's wrong with risk matrices?", *Risk Analysis* 28(2); Krisper (2021): https://arxiv.org/pdf/2103.05440
[8] IBCS, notação semântica (via SAP): https://www.sap.com/design-system/sac-dashboard-design-best-practices/resources/ibcs
