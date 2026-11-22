# Fase 2 — progresso

Ficheiro de retoma. Especificação: `docs/archive/FASE2_SPEC.md`. Atualizado no fim de cada incremento.

**Estados:** construído · testado automaticamente · conferido contra a fonte · revisto pelo Bernardo. Um estado só aparece quando aconteceu.

## Agora

- **Módulo:** M2, databook.
- **M0 concluído:** M0.1 (o verificador do memo liga cada número ao ano citado), M0.2 (ausência ≠ zero), M0.3 (R13 com descobertos; a Amorim ficou fechada com a nota 19 do relatório publicado, conferida no PDF descarregado com autorização do Bernardo), M0.4 (alertas das empresas reais classificados; contagem em `docs/examples/validation/VALIDATION.md`).
- **M2 feito até agora:** databook com as 12 folhas (`dd_assistant/databook.py`), fórmulas nos totais e pontes, recálculo pelo Excel e comparação com o Python; na app (botão "Download databook") e na linha de comandos (`--databook`).
- **M2e feito:** R27 (D&A muito acima do imobilizado), R28 (rubrica "outra" acima de 10% da receita, listada "a avaliar" no net debt), R29 (crescimento com aquisições), EBITDA antes da IFRS 16 (QoE) e nota IFRS 16 (Net Debt). Dividendos como possível leakage ficam para o M3.
- **M3 feito:** `dd_assistant/price.py` (completion accounts, locked box, leakage, sensibilidade), candidatos a leakage lidos da DFC (dividendos pagos), folhas EV to Equity e Leakage no databook, secção "Price" na app (mecanismo obrigatório, sem escolha por defeito).
- **Parado aqui, como pede a especificação:** fim do M3, à espera do resumo revisto pelo Bernardo. Depois, com aprovação: versão simples do M6.
- **Comando para retomar:** `python -m unittest -v` (268 testes) e `python scripts\build_site.py` (site estático). Último bloco: "Fecho da Fase 3", no fim deste ficheiro.

## Diagnóstico (4 de novembro de 2026)

Estado confirmado no repositório: 21 commits no ramo `main`, igual ao GitHub; 124 testes a passar; só `docs/archive/FASE2_SPEC.md` e `docs/archive/FASE2_INICIO.md` por registar. A app foi verificada em sessões anteriores em modo headless (Streamlit AppTest) e no browser; nesta fase ainda não foi aberta.

Percurso de um número: ficheiro → `dataroom.py` / `esef.py` / `extract.py` (linha identificada, fonte `Folha!Célula` ou etiqueta XBRL) → `CompanyData.lines` → `metrics.py` → `rules.py` (alerta com evidência) e `deal.py` (pontes) → `report.py` (Excel/CSV) e `ai_memo.py` (material) → `memo_check.py`.

| Requisito | Estado comprovado | Evidência | Lacuna | Impacto | Correção | Critério de aceitação |
|---|---|---|---|---|---|---|
| Memo: número ligado ao período | Era falso: um valor de FY23 citado como FY24 passava | Corrigido no M0.1; `tests/test_memo_check.py` `PeriodTest` | O rótulo só gera aviso (a prosa varia) | Um memo podia trocar anos sem ninguém notar | M0.1 feito | Toyota `€27,739k in FY24` falha; o memo da Amorim (74 números) passa |
| Ausência ≠ zero | Falso: `metrics.N()` trata vazio como zero (27 usos em `metrics.py`, 10 em `deal.py`) | `metrics.py:100` | Caixa ou dívida em falta dão pontes com zero | Net debt e NWC podem parecer completos sem o serem | M0.2 | Caixa em falta → ponte "incompleta" e diz o que falta |
| R13 (caixa DFC vs. balanço) | Dispara na Amorim por definição de caixa (descobertos) | `tests/test_real_companies.py` Amorim | Não distingue reconciliação explicada de erro | Alarme falso numa empresa real | M0.3 | Amorim sem R13; diferença mostrada como reconciliação |
| Classificação dos alertas reais | Os testes só listam IDs | `tests/test_real_companies.py` | Sem "verdadeiro positivo / alarme falso / por rever" | Não se mede a precisão das regras | M0.4 | Cada alerta esperado classificado; contagem no relatório |
| Leitura Excel, 6 formatos | Construído, testado, conferido na Toyota e na Amorim (contas publicadas) | `test_europe.py`, `test_extract.py`, `test_real_companies.py` | Formatos espanhol, francês, alemão e italiano só com dados sintéticos | Generalização por provar | Fora desta fase (M5) | — |
| ESEF | Construído; testado com pacote sintético; conferido à mão na EDP (resultado operacional ao milhar) | `test_esef.py` | 1 filing real; sem factos nil nem duplicados conflitantes; ZIP lido em memória sem limite de expansão | Ficheiro malicioso ou grande pode esgotar memória | Limite de tamanho no M0/M2; resto no M5 | ZIP acima do limite recusado com mensagem |
| Proveniência | Construído em parte: fonte `Folha!Célula` ou etiqueta | `CompanyData.sources` | Sem hash do ficheiro, natureza (reportado/calculado/…) nem valor original nas correções | Rastreabilidade incompleta no databook | M2 (Source Register) | Cada ficheiro com hash; cada linha com natureza |
| Revisão humana | Construído na app (Accepted / Dismissed / Pending, comentário) | `app.py:278` | Sem autor, data nem persistência; exportação sem versão | Decisões perdem-se ao fechar a app | M2 (registos no databook) | Exportação com versão, data e revisor declarado |
| Deal view | QoE, net debt, NWC, peg indicativo | `deal.py`, `test_deal.py` | EV → equity, completion accounts, locked box, leakage | Não liga a DD ao preço | M3 | Casos da secção 6 da especificação |
| Databook | Excel com red flags, deal view, setor, checks, métricas | `report.py` | Folhas da secção 5, fórmulas auditáveis, recálculo | Não é o entregável de uma equipa de transação | M2 | Folhas da secção 5; recálculo pelo Excel igual ao Python |
| Itens vistos na Toyota | Nenhum apanhado por regra | Especificação, secção 2 | D&A vs. imobilizado; "outras" no NWC; IFRS 16; aquisições; dividendos | Pontos que um revisor encontrou e as regras não | M2 (regras novas) | Testados na Toyota; Velmora com zero alertas analíticos |
| Dados mensais | Inexistente | — | Tudo | Peg só indicativo | M4 (opcional) | — |

## Decisões

- **M0.1, rótulo como aviso e não como erro.** Um número só passa se existir no material para o ano citado na mesma oração; um ano trocado é erro. Se o número existe para esse ano mas noutra linha, é aviso, porque a prosa do memo não usa os rótulos do material ("operating cash" por "cash generated from operations"); um erro aqui daria alarmes falsos. Sem ano na oração, vale a regra antiga (o número existe no material).
- **M0.1, ano citado:** o ano logo a seguir ao número sem outro número pelo meio ("67.6% in FY23"), senão o mais próximo antes ("FY23: €27,739k"), senão o mais próximo depois. No material, as células do data room recebem o ano do cabeçalho da folha.

- **M0.2, o que conta como "não apresentado".** Um resultado fica desconhecido (não zero) quando falta um dado de que depende: net debt sem caixa ou sem nenhuma linha de financiamentos; NWC sem clientes, fornecedores ou as outras linhas correntes; FCF sem fluxo operacional ou capex; R12 sem caixa ou capital próprio. Continuam a contar como nulas as linhas que uma demonstração pode simplesmente não ter: imparidades, trabalhos para a própria entidade, inventários (serviços), a segunda linha de financiamentos quando a primeira existe. A R14 compara só os movimentos que a DFC apresenta. A paridade não muda: a Duriva e a Velmora têm todos os dados, e a planilha dá os mesmos resultados.
- **M0.2, o que ainda usa N():** o EBITDA (soma das linhas operacionais apresentadas), as listas de clientes e os ajustes da gestão (um ano vazio de um ajuste é zero). Um EBITDA sem uma linha de custo principal é apanhado pelas reading checks, não por N().

- **M0.3, "explicada" quer dizer igual, ao milhar.** A diferença de caixa só passa a reconciliação quando uma linha identificada a explica dentro da tolerância da R13 (€1k): descobertos bancários (IAS 7.8, caixa da DFC líquida de descobertos) ou caixa restrita (US GAAP, incluída na DFC). Uma explicação parcial continua a disparar. Os descobertos são lidos da DFC ou de uma folha de nota (por exemplo, a nota de caixa).
- **M0.3, Amorim:** a diferença (FY24 −€48,672k; FY23 −€86,263k) é a dos descobertos da nota 19 do relatório anual de 2024 (página 426: "Overdrafts −48,672 / −86,263"; política na página 399: a caixa da DFC inclui os descobertos que estão em "Bank loans"). PDF: `Amorim_RC24_EN_low.pdf`, amorim.com, obtido a 4 de novembro de 2026, SHA-256 `e743e35dae3f3e431b53f8fa7cd6770c9bf0b9db1346cb196b8cfb1fbcb06ff3`, 12,6 MB (fica fora do projeto). A nota foi copiada tal como impressa para a folha "Note 19 Cash" por `scripts/real_corticeira_amorim.py`. Os descobertos já estão dentro da dívida (em "Bank loans"), por isso não entram outra vez na net debt. O memo de exemplo em `docs/examples/` ainda fala da R13 da Amorim: é um registo histórico da corrida de outubro e fica como estava.

- **M2, ajuste por regra (R19) entra no EBITDA ajustado.** O ganho de alienação que a DFC identifica fica com o estado "Applied by rule" e conta no cenário base, como na app, para os números baterem entre app, databook e relatório. O analista pode pô-lo em "Rejected" no databook. Os ajustes da gestão começam como "Proposed" e só entram quando o analista os aprova. **Decisão a confirmar pelo Bernardo.**
- **M2, ligações que ficam vazias.** No Excel, uma ligação a uma célula vazia dá 0. Cada ligação do databook usa `IF(ISBLANK(...),"",...)`: um dado em falta continua em falta e o total diz "incomplete", como no Python (M0.2).
- **M2, recálculo.** O openpyxl escreve fórmulas sem as calcular. `databook.recalculate()` pede ao Excel deste PC (via COM) que calcule e grave; a folha Checks compara cada total com o valor do Python. Sem Excel, a folha diz PENDING e o Excel calcula ao abrir (`fullCalcOnLoad`). Não há LibreOffice neste PC.
- **M3, o que entra no preço.** Completion accounts: Equity = EV + caixa − dívida financeira − itens debt-like incluídos (+ cash-like incluídos) + (NWC ao closing − peg) + ajustes contratuais com sinal. Os itens são os que o analista incluiu no Net Debt, contados uma vez; o peg por defeito é a média indicativa dos fechos, sempre rotulada como "não é um peg". Locked box: preço acordado + accrual fixo ou ticking fee (ACT/365) − leakage confirmado, deduzido no closing ou como reclamação separada, nunca os dois. Sem true-up de NWC.
- **M3, leakage.** Os dividendos pagos da DFC entram como "Candidate", nunca como leakage: as contas anuais não dizem a data do pagamento nem o que o SPA permite. Sem nenhum item revisto, a conclusão é "evidência insuficiente".
- **M3, verificação independente.** A especificação pede um subagente sem acesso à implementação para os casos difíceis. Para o preço usei os esperados escritos na própria especificação (secção 6) e uma conta à mão da Duriva; não usei um subagente. Fica como pendente se quiseres essa revisão.
- **M3, falha apanhada tarde.** As regras R27–R29 do M2e não estavam na lista de ordenação da app e a Toyota rebentava no Overview; só a vi no M3, ao abrir a app. Corrigido e com um teste que obriga todas as regras a estar na lista.
- **M2, inspeção visual: pendente.** Não consigo ver imagens do Excel neste PC. Exportei o PDF pelo Excel e conferi o texto (28 páginas, sem `####` nem erros de fórmula). Falta abrires o ficheiro.

## Incrementos

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| M6 simples | README atualizado (29 regras, databook, preço, limites); roteiro de demo em `docs/archive/DEMO.md`; fluxo da app visto no browser (Overview → Deal view → Price: CA €7,099k na Duriva, sem erros na consola) | Sim | 165 testes OK | Números do roteiro conferidos na app | Databook revisto pelo Bernardo no Excel (exercício Net Debt → NWC, Toyota); README e roteiro pendentes |
| M3 | EV → equity (completion accounts, locked box), registo de leakage, sensibilidade só com EV derivado; folhas no databook; secção na app | Sim | 165 testes OK (14 em `tests/test_price.py` com os casos da secção 6; 1 no databook recalculado); app headless: sem mecanismo não calcula, CA €7,099k e LB €9,050k na Duriva | Casos da especificação (esperados escritos na especificação); Duriva conferida à mão (EV 10,000 + 603 − 4,350 + 846) | Pendente |
| M2e | Regras R27–R29, item "a avaliar" para rubricas "outras" materiais, EBITDA antes da IFRS 16 | Sim | 149 testes OK; Velmora continua com zero alertas analíticos | Toyota: esperados calculados à mão a partir da DRE, Balanço e DFC publicados (`test_what_a_reviewer_found`) | Pendente |
| M2a–d | Databook: Read Me, Executive Summary, Source Register (com SHA-256), Financials, QoE (registo de ajustes com estado), NWC (política de inclusão), Net Debt (classificação e inclusão), Issues & Requests (pedidos fundidos), Checks; EV to Equity, Leakage e Monthly & LTM dizem que ainda não existem | Sim | 148 testes OK (10 novos em `tests/test_databook.py`, 2 recalculam no Excel); app headless com o botão nas 4 amostras | Totais do Excel = Python na Duriva e na Toyota (11 e 6 controlos) | Pendente (inspeção visual tua) |
| M0.1 | `memo_check` liga cada número ao ano citado | Sim | 127 testes OK (3 novos em `PeriodTest`) | Valores da Toyota conferidos na DRE publicada (outros rendimentos FY23 27.739.438 €, FY24 34.746.983 €) | Pendente |
| M0.4 | Alertas das empresas reais classificados (5 verdadeiros positivos, 4 por rever; o alarme falso da Amorim foi resolvido no M0.3); `scripts/validation_report.py` escreve `docs/examples/validation/VALIDATION.md` | Sim | 138 testes OK | Classificação feita a partir dos números publicados (Toyota DRE/DFC, Amorim DR/DFC) | Pendente: a classificação é uma proposta |
| M0.3 | R13: diferença explicada por descobertos ou caixa restrita passa a reconciliação (memo no net debt) | Sim | 138 testes OK (4 novos em `tests/test_cash_reconciliation.py`); paridade igual | Sim: Amorim, nota 19 (p. 426), igual ao milhar nos dois anos | Pendente |
| M0.2 | Ausência ≠ zero: net debt, NWC, FCF, R12, R14, mapa da dívida; avisos "incompleto" na app, no Excel, no memo e no JSON | Sim | 133 testes OK (6 novos em `tests/test_absence.py`); app headless sem erros nas 4 amostras | Não aplicável (casos construídos a partir da Velmora) | Pendente |

## Demo online (docs/archive/DEMO_ONLINE_SPEC.md)

- **Feito:** TAP FY2025 transcrita do 2025 Integrated Report (site da TAP, obtido a 4 de novembro de 2026; o PDF enviado pelo Bernardo, `ANN153482.pdf`, tem o mesmo texto nas páginas das demonstrações e das notas). Resultado operacional reconstruído ao euro nos dois anos; balanço fechado; teste em `tests/test_real_companies.py` (`TapTest`). O dicionário aprendeu um P&L de companhia aérea; a R12 usa os totais publicados quando existem; as rubricas "outras" medem-se sem os itens já classificados.
- **Não há ESEF da TAP** (não está no filings.xbrl.org). O relatório consolidado de 2025 só existe dentro do Integrated Report.
- **Toyota e Amorim FY2025:** os pacotes ESEF existem (filings.xbrl.org, 3,7 MB e 13,5 MB, obtidos a 4 de novembro de 2026, fora do projeto), mas a leitura falha as reading checks: no da Toyota há etiquetas trocadas pela própria empresa (ativos detidos para venda etiquetados como "Inventories", um subtotal corrente etiquetado como ativos detidos para venda) e a receita de serviços fica de fora; no da Amorim a diferença em FY25 é de €34,738k, por investigar.
- **Toyota e Amorim FY2025 transcritas** (decisão do Bernardo: transcrever). Os sites bloqueiam o download automático dos PDF (301/403), por isso a fonte é o texto impresso do relatório anual oficial em ESEF (XHTML, filings.xbrl.org; as etiquetas XBRL não são usadas). Toyota: resultado operacional ao euro. Amorim: EBITDA publicado 140,985 contra 140,983 das dez linhas impressas, arredondamento do relatório; a tolerância das reading checks passou a ser meia unidade por linha somada quando as contas vêm em milhares (visível em cada check). O dicionário aprendeu os subtotais e rótulos portugueses de um grupo IFRS cotado ("Ativos correntes", "Dívida remunerada", "Imposto sobre os resultados"…); sem os subtotais, o ativo não corrente ia parar às "outras" correntes e dava uma R28 falsa.
- **Modo demo feito** (`DD_DEMO=1`, `dd_assistant/demo.py`): página inicial com o aviso e três cartões; país, setor e finalidade fixos (os que o motor sugere e com que o memo foi verificado); sem upload, sem botões da API, sem campo de chave; o separador Memo mostra o memo guardado e corre o verificador outra vez; downloads no topo (databook, red flags em Excel e CSV, request list); rodapé com autor, GitHub, LinkedIn e limites. No Streamlit Community Cloud o modo demo é o padrão (pasta `/mount/src`). O motor só importa a biblioteca `anthropic` quando lê um PDF ou escreve o memo pela API.
- **Memos da demo feitos** pelo agente (skill, sem API) e verificados: TAP 89 números, Toyota 78, Amorim 85, nenhum sem fonte, zero avisos. Guardados em `docs/examples/<empresa>/` com o resultado do verificador e o databook recalculado pelo Excel (6 de 6 totais iguais ao Python em cada um). `scripts/demo_examples.py` volta a gerar databooks e verificações.
- **Case notes feitas** (uma página por empresa). O contexto da privatização da TAP (JN, 6 de setembro de 2026) aparece só na página da TAP na demo e na case note; um teste garante que não chega ao memo nem ao material.
- **README refeito** (Live demo como marcador, imagens da app pelo Playwright com o Edge e do databook pelo Excel, "What it found", How it works com diagrama, How it is verified, Limits, Built by); detalhes técnicos passaram para baixo. `docs/DEPLOY.md` com os passos no share.streamlit.io; `requirements.txt` com versões fixas.
- **Testes:** 192 OK. `tests/test_demo.py`: interruptor, página inicial, as três empresas sem upload nem API, a app sem a biblioteca `anthropic`, memo guardado a passar agora, verificação guardada atual, números dos cartões e das case notes no material, databook guardado igual ao motor (sem erros de fórmula, painéis fixos, unidades visíveis), app e memo com o mesmo EBITDA e net debt ajustada.
- **Percurso visual feito** no browser: as três empresas, o preço (completion accounts com EV) e o memo, sem erros na consola. Não carreguei nos downloads no browser (o conteúdo de cada um é testado).
- **Decisão:** na Toyota e na Amorim, a DFC pelo método direto tem o subtotal "Fluxo gerado pelas operações", que o dicionário não lê; a R10 usa o fluxo operacional final. Na Toyota isso é o prudente (os "outros pagamentos" de -€133,493k ficariam de fora e a conversão passaria a 215%). Ficou anotado nos memos, em "Notes to improve the template"; mudar o motor muda os alertas e fica para decidires.
- **Publicado** pelo Bernardo a 4 de novembro de 2026 em https://dd-assistant-tickmark.streamlit.app; conferido no browser: as três empresas abrem, sem upload, e o memo passa no verificador também na cloud (89, 78 e 85 números). O `server.address = "localhost"` não impediu a cloud de abrir a app.
- **Pendente:** rever o texto "Built by" do README e as case notes.

## Demo UX (docs/archive/DEMO_UX_SPEC.md, 9 de novembro de 2026)

A secção 6b referida na mensagem do Bernardo não estava no ficheiro; as 10 lições da mensagem foram aplicadas.

- **Credibilidade (secção 2):** contas consolidadas passam a IFRS por defeito (o SNC fica para contas individuais); cartão do working capital com a nota do setor ("normal for airlines"), a cor continua a vir dos achados de NWC (R07 High, limites sem mudança); cabeçalho com nome curto, nome legal, relatório e páginas e uma só unidade; o método de leitura passou para o separador Data room.
- **Key insights e cascatas:** os três pontos da case note no topo; cascatas de net debt (por categoria: leasings €2,158m na TAP), EBITDA e EBITDA antes da IFRS 16, e NWC com a média. Passos calculados em `deal.py`; o gráfico só desenha.
- **Página inicial:** frase de valor, autor, para quem, limites, três botões (TAP, Excel, código), nota dos dados, 5 passos, cartões com um número grande, o databook, "How it is verified" calculado na página, Measured / Not measured, How you check it, glossário.
- **Barra lateral recolhida** com "About this demo"; glossário ao passar o rato; fonte em cada cartão (p.152, p.153, p.156 na TAP); barra do Streamlit em modo minimal.
- **Visita de 60 segundos** (`st.dialog`, 5 passos, com a página do relatório no red flag).
- **Imagens:** GIF de 23 s, página inicial, cascata da net debt, Excel e social preview 1280×640, por `scripts/demo_screenshots.py`; verificação a 1440 e 375 px por `scripts/demo_review.py`.
- **Testes:** 203 OK.
- **Pendente:** confirmar a linha "Built by … ex-EY Transaction Services intern" (o README diz "International Tax and Transaction Services"); push com aprovação; carregar a social preview no GitHub.

## Fase 3 (docs/archive/FASE3_SPEC.md, 10 de novembro de 2026)

**Decisões do Bernardo:** materialidade "o normal do mercado" (ficou 5% do EBITDA reportado para itens de resultados e 1% das vendas para itens de balanço, editável); linha de autor "former intern in International Tax and Transaction Services at EY"; nome público por decidir (no GitHub e na app continua "DD Assistant").

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| A1 + A2 | Materialidade, montante em causa por achado, lista única de key issues (achados e itens de net debt) por montante, implicação para o deal por regra e editável; folha Key Issues no databook, separador na app, secção 1b no material do memo, JSON | Sim | 219 testes OK (16 novos em `tests/test_issues.py`); memos reverificados: 96, 85 e 93 números, nenhum sem fonte | TAP: leasings (4 linhas do balanço, p.152), excesso de clientes da R07 e juros da R22 calculados à mão a partir das células publicadas | Pendente |

- **Decisão de desenho, diferente da especificação:** a materialidade é uma camada acima das regras (`dd_assistant/issues.py`). `rules.evaluate` continua a dar a severidade da planilha, por isso a paridade não mudou e o teste não foi ajustado. A severidade final (com "below materiality") é a de `pipeline.analyse`.
- **Montante por regra:** tabela `issues.AMOUNTS` (por exemplo R07 = clientes acima do nível que o crescimento das vendas daria; R10 = caixa operacional em falta face ao limite; R24 = D&A menos capex). A R18 fica "not quantifiable from the accounts". Um achado não quantificável mantém a severidade da regra.
- **O que mudou de severidade:** na Duriva, a R13 e a R14 (€85k) passam de Medium a Low (abaixo de 1% das vendas, €214k). Nas três empresas da demo nenhuma severidade mudou: na TAP a R07 fica High porque o excesso de clientes (€63m) passa o limiar de €43m; desce para o 7.º lugar da lista.
- **Itens "to assess" que a R28 já cobre** não aparecem duas vezes na lista.
- **Memos:** cada um ganhou a tabela "Key issues by amount at stake" (5 primeiros, com a implicação). Os temas não foram reordenados: fica para quando as notas (A4) mudarem o conteúdo.
- **Pendente:** o Excel "Red flags" e o CSV ainda não têm a coluna do montante (o databook tem); nome público; push.

### A3 + A4 (11 de novembro de 2026): três anos, reexpressões e notas

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| A3 | Três anos a partir de dois relatórios (`dd_assistant/history.py`, `--prior`); regra R30 (comparativos reexpressos); CAGR só com os três anos; as três empresas da demo com FY23–FY25 | Sim | 12 testes em `tests/test_history.py` | TAP 2024: transcrição por subagente a partir do relatório consolidado de 2024 (pp. 54, 55, 58, 123, 145); resultado operacional reconstruído ao euro em FY24 e FY23 | Pendente |
| A4 | Notas-chave transcritas para as três empresas (`data/notes/`, `scripts/notes_*.py`); leitor `dd_assistant/notes.py`; estado de evidência de cada achado e item (open · partly explained · explained by note N); pedido de nível seguinte; notas no material do memo, na app, no databook e no JSON (`--notes`) | Sim | 13 testes em `tests/test_notes.py` | 30 valores das notas lidos por um subagente independente, sem acesso às transcrições: 30 em 30 iguais | Pendente |

- **Total de testes:** 244 OK. Memos reescritos com os três anos e as notas: TAP 142 números, Toyota 134, Amorim 139, nenhum sem fonte, zero avisos.
- **Política dos comparativos:** para o ano que os dois relatórios dão usa-se o comparativo do relatório mais recente; cada linha diferente (acima de €1k) fica listada com as duas fontes. Linhas derivadas ("total menos as linhas identificadas") não contam, porque dependem do detalhe de cada ficheiro.
- **Reexpressões encontradas:** Toyota e Amorim, nenhuma. TAP: seis linhas de totais do balanço de 2024 (ativo total €5,739m publicado, €5,797m como comparativo); a R30 dispara (Medium, €58m).
- **O que as notas resolveram:** Toyota: outros rendimentos explicados pela nota 33 (recuperações de encargos €13,977k, subsídios €5,142k, mais-valias €4,862k) e outras dívidas a terceiros pela nota 22, que revela €48,078k devidos à Toyota Kreditbank para compra de viaturas, fora dos financiamentos. TAP: leasings (nota 19) e provisões (nota 18: €291m de redelivery). Amorim: dívida de curto prazo de 2024 (nota 22), outros passivos e ativos financeiros (notas 24 e 14: sobretudo saldos operacionais e fiscais); outros rendimentos só em parte (nota 30 deixa €7,051k em "Outros").
- **Como se decide o estado:** "explained" exige que um valor da nota seja igual (±€1k) à linha das demonstrações por trás do achado; se a maior linha da nota for um "Outros" residual, fica "partly explained". Nada é inferido.
- **Correções feitas pelo caminho:** o imposto a pagar do balanço de 2025 da Amorim ("Imposto sobre o rendimento", passivo corrente) passou a ser reconhecido como debt-like, como já era no de 2024; a net debt ajustada de FY25 passa de €79,657k para €83,638k. O verificador do memo passou a aceitar euros citados em milhões e a não tratar o dia de uma data ("31 de dezembro de 2024") como número.
- **Teste da empresa limpa ajustado:** a R30 fica "n/a" com um só relatório, por desenho; o teste que exige todas as regras testadas na Velmora exclui-a com essa razão. Nenhum alarme novo na Velmora.
- **Não feito (fica em GAPS):** regras novas baseadas em notas (partes relacionadas, contingências sem provisão, concentração por segmento); itens das notas a entrar sozinhos na ponte de net debt (o financiamento de stock da Toyota e as provisões de redelivery da TAP estão no memo, não na ponte); a app normal (sem demo) ainda não tem campo para o relatório anterior nem para as notas, só a linha de comandos.
- **Commit único para A3 + A4:** os dois blocos mexem nos mesmos ficheiros e os memos só voltaram a passar com ambos.

### B1 + B3 (11 de novembro de 2026): benchmark de deteção e folha de revisão

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| B1 | `scripts/detection_benchmark.py`: 19 distorções e 2 controlos, uma de cada vez, nas três empresas da demo; resultado em `docs/DETECTION.md` e resumo em `docs/examples/validation/VALIDATION.md`, README e página inicial | Sim | 8 testes em `tests/test_detection.py` (252 no total) | Não aplicável: mede o motor contra distorções plantadas | Pendente |
| B3 | `docs/examples/validation/REVIEW_SHEET.xlsx` (`scripts/review_sheet.py`): 23 achados e 16 itens de net debt, com evidência, estado das notas e classificação proposta; colunas de decisão vazias | Sim | Sim (colunas do revisor vazias; folha atual) | — | **À espera do Bernardo** |

- **Tabela do esperado escrita antes de correr** (`MUTATIONS` no script). Não foi alterada depois da primeira corrida, nem nenhum limite.
- **Resultado da primeira e única corrida: 48 de 49 detetadas (98%).** 8 ficaram fora da taxa porque a regra já disparava nas contas reais (por exemplo, R07 na TAP, R09 na Toyota); 11 outras regras dispararam ao lado, todas consequência plausível da distorção (por exemplo, juros mais altos baixam o lucro e disparam também a R25).
- **Falha 1 (não detetada): TAP, M18.** Fornecedores +20 dias de custo das vendas não disparou a R23, porque nas contas reais o DPO da TAP caiu 96 dias de FY24 para FY25; a regra compara ano com ano e o movimento real esconde a distorção plantada.
- **Falha 2 (alerta a mais num controlo): Amorim, C02.** Um erro de €2k na caixa final da DFC fez a R13 disparar com severidade Medium, quando devia ficar Low. Causa: a reconciliação por descobertos é tudo ou nada; com €2k de diferença deixa de "explicar" e os €29,451k inteiros passam a diferença por explicar.
- **Não afinei nada.** As duas falhas ficam publicadas e em `docs/GAPS.md`; mudar a R13 ou a R23 fica para decidires.
- **O que o benchmark não mede:** distorções que ninguém pensou, mais pequenas, ou várias ao mesmo tempo.

### Depois do benchmark (12 de novembro de 2026): R13 corrigida, R23 mantida

- **Decisão do Bernardo:** corrigir as duas regras que falharam.
- **R13 corrigida.** Quando uma linha identificada (descobertos, caixa restrita) explica pelo menos 90% da diferença de caixa, só o resto fica por explicar; o resto continua a disparar a R13 se passar €1k. Antes, um erro de €2k tornava os €29,451k da Amorim "por explicar". Dois testes novos em `tests/test_cash_reconciliation.py`; a paridade com a planilha não muda (a Duriva não tem descobertos). Benchmark depois da correção: 6 de 6 controlos, as mesmas 48 de 49.
- **R23 não alterada, e porquê.** A distorção plantada na TAP (+20 dias de fornecedores) vale cerca de €12m, abaixo da materialidade de balanço da TAP (€43m), e fica escondida por uma queda real de 96 dias no DPO. Para a apanhar seria preciso mudar a definição do DPO (hoje fornecedores sobre o custo das mercadorias, que numa companhia aérea é só uma pequena parte das compras). O DPO é uma métrica da planilha de referência: mudá-lo quebra a paridade e obriga a alterar a planilha. Não é uma correção para fazer por causa de um teste; fica como falha publicada, dentro da taxa.
- **Transparência:** a história (primeira corrida, o que mudou e o que não mudou) está escrita no `docs/DETECTION.md`.

### C + A5 (12 de novembro de 2026): relatório em slides e ponte de caixa

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| A5 | Ponte de caixa EBITDA → free cash flow (`deal.cash_steps`): variação do NWC pelos dois balanços, o resto até ao fluxo operacional publicado como linha própria, capex, alienações, pagamentos de locação. Na app (Deal view), no material do memo e nos slides | Sim | 2 testes em `tests/test_slides.py` (reconcilia com a DFC e com o FCF das métricas) | Reconcilia por construção com o fluxo operacional publicado | Pendente |
| C | Red Flag Report em PowerPoint (`dd_assistant/slides.py`, `--slides`): 9 slides, títulos com a conclusão e o número montados por regra, 4 gráficos nativos (editáveis), fonte no rodapé; PDF exportado pelo PowerPoint deste PC | Sim | 6 testes (9 slides, rodapé, títulos, cada número no material, gráficos com os passos do motor) | Cada slide das três empresas visto em imagem; barras negativas e rótulos corrigidos | Pendente |

- **Dependência nova, só para produzir os slides:** `python-pptx` 1.0.2, em `requirements-dev.txt` (com o Playwright). A app e a demo publicada não precisam dela: descarregam os ficheiros já gerados em `docs/examples/<empresa>/`.
- **Gráficos nativos:** cascatas feitas com colunas empilhadas (base invisível); o valor de cada barra está no rótulo da categoria, para ficar editável e legível. A parte de uma barra abaixo de zero usa séries próprias por cor, porque o PowerPoint não respeita a cor por ponto em valores negativos.
- **Total de testes:** 262 OK.
- **Não feito:** a ponte de caixa ainda não tem folha no databook (fica em GAPS); os slides da demo refletem a análise por defeito, como o memo.


### Fecho da Fase 3 (docs/archive/FASE3_FINAL.md, 16 de novembro de 2026): site, app e README

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| 1 | Site estático: `scripts/build_site.py` gera `site/index.html`, `tap.html`, `toyota.html`, `amorim.html` (HTML e CSS por página, só fontes Google; cascatas em SVG com posições em %, legíveis a 375 px; tema claro e escuro; Open Graph). Downloads e imagens copiados para `site/files` e `site/img` (fora do git). Workflow `.github/workflows/pages.yml`; passos em `docs/DEPLOY.md` | Sim | 6 testes em `tests/test_site.py`: cada número das partes de empresa está no material do memo para o ano citado; números de verificação contados agora; downloads existem; sem pedidos a terceiros; site atual | Números do motor; nenhum sem fonte | Pendente |
| 2 | App: paleta e tipografia do site (navy #13294b, cobre #b4611a, Inter e Source Serif 4 via `.streamlit/config.toml`); tabelas do memo com scroll horizontal no telemóvel (antes ficavam cortadas a 375 px); menos espaço vazio no fim da página | Sim | `tests/test_demo.py` OK | — | Pendente |
| 3 | README com links para o site e a demo e a imagem da página inicial (`docs/images/site-home.png`, `build_site.py --screenshot`); imagens da demo e GIF refeitos com a paleta nova (`scripts/demo_screenshots.py`) | Sim | — | — | Pendente |

- **Zona em branco na TAP (~800 px): não reproduzida.** Varri os 9 separadores a 760, 800 e 840 px (pontos da janela sem nenhum elemento por baixo, de 300 em 300 px de scroll): nenhum vazio acima de 200 px. O único vazio era o padding do Streamlit depois do rodapé (~140 px), que reduzi. Se voltares a ver a zona, diz-me o separador e a largura exata.
- **Ponte de caixa no databook: não feita.** Precisa de folha com fórmulas, linha no Checks, databooks guardados recalculados pelo Excel e o teste de igualdade; não cabe "sem esforço". Fica em GAPS.
- **Fora deste fecho, por decisão:** slides, kit de candidaturas, regras novas.
- **Pendente:** push com aprovação do Bernardo; ativar o GitHub Pages (passos em `docs/DEPLOY.md`); nome público ("DD Assistant" mantido).

## Fase 4 (docs/archive/FASE4_SPEC.md, 16 de novembro de 2026)

### Fase A — gráficos (feita, à espera de aprovação)
- `dd_assistant/charts.py`: um só modelo e um só desenho (SVG) para as pontes; o site e a app usam o SVG, os slides usam o mesmo modelo em gráficos nativos do PowerPoint. Cor pelo efeito para o comprador (vermelho pior, verde melhor, totais cinzentos), maior item em cor plena e os outros a 45%, no máximo 7 colunas (itens abaixo de 1% do maior total em "Others", capex e alienações em "Net capex", depois saem os subtotais intermédios), action title e anotação por regra a partir do motor, nota de arredondamento. Paleta escura no site.
- Testes: `tests/test_charts.py` (10); títulos e anotações passam pelo verificador do memo; as somas agrupadas (Net capex, Others) não estão no material e são testadas como soma das partes (marcadas `data-nocheck` no site).
- Na app, o SVG vai por `st.markdown` (o `st.html` remove SVG). Slides e PDF da demo regenerados.
- Nota: no telemóvel, os gráficos com mais colunas deslizam para manter o texto a 11 px; a anotação do total final fica do lado direito, visível ao deslizar.

### Fase B — camada de deal (feita a 16 de novembro de 2026, à espera da revisão)

**Feito**
- Antes da B (decisão do Bernardo sobre a A): no telemóvel, a anotação do gráfico aparece por baixo do título, fora do SVG; o número de destaque já estava no título. Ponto 7 (mapa de cobertura) acrescentado à `docs/archive/FASE4_SPEC.md`.
- `dd_assistant/deal_layer.py` (pontos 1–7): valuation impact (EBITDA × 6x/8x/10x + itens de net debt + NWC contra o peg indicativo, "Illustrative, not a valuation"); top 5 deal issues com proteção típica e momento; risk score 0–100 com fórmula e decomposição por 5 áreas; encaminhamentos (Legal, HR, Tax, Regulatory) a partir das notas; open items em 3 grupos; ações por momento; mapa de cobertura com o documento que desbloqueia cada regra. Uma só request list (`request_list`) para o databook e os open items, com as regras bloqueadas, sem duplicados.
- Databook: folhas Top Issues, Valuation Impact (fórmulas; Excel = Python nas três empresas) e Open Items (com a grelha de cobertura). Material do memo: secção 1c, para o verificador conhecer os números novos. Gráfico `charts.valuation` (mesmo gerador). Site: secção "Deal view" em cada página de empresa. `docs/examples/<empresa>/deal_layer.md` gerado por `scripts/demo_examples.py`.
- Resultados: risk score TAP 50, Toyota 62, Amorim 30; Duriva 100 (problemas plantados), Velmora 0. Cobertura: 22 de 30 regras nas três cotadas, 29 de 30 na Duriva. Impacto a 8x: TAP −€2,547m, Toyota +€16,013k, Amorim −€79,293k (sem ajustes de EBITDA: igual a qualquer múltiplo).
- Testes: `tests/test_deal_layer.py` (16; 294 testes no total, todos OK), incluindo a dupla contagem, a fórmula do score, a Duriva a correr mais regras e um pedido por regra bloqueada.

**Decisões (a opção mais conservadora)**
- Score: pesos High 3 / Medium 2 / Low 1 × materialidade (material 1, não quantificável 0,75, abaixo 0,5); 100 = 30 pontos (dez achados High materiais); teto 100. A R18 (documentos em falta) fica fora do score e entra na cobertura e nos open items. Os itens de net debt não contam: o score mede achados das regras.
- Top 5: ordem pelo montante em causa (não pelo montante × múltiplo, para não depender de um múltiplo ilustrativo).
- Proteção típica por implicação: Price: EBITDA → ajuste de preço; Price: net debt → debt-like no SPA; Price: working capital → completion accounts; SPA protection → indemnity, ou escrow/retention quando material e sem explicação nas notas; Further diligence e Post-deal → pedir mais informação. Momento: Price/Further → antes do signing; net debt e SPA protection → SPA; NWC → completion accounts; Post-deal → pós-closing.
- Valuation impact: o lado EBITDA só tem ajustes já aceites ou aplicados por regra (visão prudente do comprador), a partir do EBITDA do vendedor (o ajustado pela gestão, quando existe). NWC só com dois fechos ou mais, contra a média dos fechos, rotulada como peg indicativo. Dupla contagem: cada linha entra uma vez; os itens de net debt já estão fora do NWC (deal.py).
- Áreas: as regras de consistência vão para a demonstração que testam (R12, R17 → Net debt; R13, R14 → Cash flow; R15, R16, R30 → Quality of earnings).
- Encaminhamentos só por palavras das notas transcritas; garantias a clientes (provisão operacional) não são encaminhadas; uma nota fiscal fica em Tax mesmo com processos judiciais. Não há análise jurídica: só o item e a pergunta.
- Open items: "Confirm with the auditor" = o que uma nota publicada explica (o número é público, o tratamento não está confirmado); os pedidos de achados totalmente explicados pela nota saem de "Ask the company".
- Modo do mapa de cobertura: "outside-in" quando os ficheiros são contas publicadas ou há notas transcritas; senão "data room".

**Por fazer / limites**
- A app Streamlit ainda não mostra a camada de deal (é a Fase C: Resumo, Áreas, Impacto com slider de múltiplo, Evidência).
- A página inicial do site ainda não tem o risk score por empresa (Fase D).
- Os encaminhamentos dependem das notas transcritas; sem notas, só a pensão (item de net debt) é encaminhada.

### Revisão da Fase B (16 de novembro de 2026, `docs/archive/FABLE_REVIEW.md`)
- **Corrigido:** o valuation impact só conta ajustes de diligence. Os leasings passam a "Standard EV-to-equity item" (o EBITDA é pós-IFRS 16) e o NWC contra o peg a "Price mechanism" (completion accounts): mostram-se, não contam. Impacto a qualquer múltiplo: TAP −€177m (antes −€2,547m), Toyota −€1,508k (antes +€16,013k), Amorim −€7,779k (antes −€79,293k). Os resultados da Fase B acima ficam como registo histórico.
- **Risk score novo:** severidade × materialidade × evidência (aberto 1, parcialmente explicado 0,75, explicado 0,5), sobre achados e itens de balanço por classificar. TAP 61, Toyota 52, Amorim 32, Duriva 100, Velmora 0.
- **Testes:** 297 OK. Databooks, `deal_layer.md` e site regenerados; slides não mudam.
- **Linhas 5 a 8, aprovadas e feitas:** coluna "Protection or next step"; a receita diferida de uma companhia aérea é um item de working capital (`sectors.OPERATING_ITEMS`, com a razão à vista; NWC e net debt não mudam); a R25 só dá escrow com uma nota de contingências fiscais; R05 e R06 ficam "not applicable" em contas publicadas. TAP: score 54 (Toyota 52, Amorim 32). 299 testes OK; databooks, slides, site e `deal_layer.md` regenerados.

**Próximo passo exato:** com aprovação do Bernardo, a Fase C segundo `docs/archive/FASE5_DESIGN.md`.

## Fase 5 — fases C e D (docs/archive/FASE5_DESIGN.md, 16 de novembro de 2026)

**Feito**
- **C, ferramenta** (`tool.py`, chamada pelo `app.py` em modo demo): cabeçalho (empresa, FY, unidade, modo, download), quatro vistas (Summary, Findings, Impact, Evidence), tema escuro com a paleta única (`.streamlit/config.toml`). Summary: faixa de estado, 4 KPIs com a fonte, 5 chips de área que abrem Findings filtrado, top 5. Findings: filtros, cartões com evidência citada, pergunta, documento, proteção e momento, decisão do revisor e comentário (na sessão). Impact: ponte de net debt em duas camadas (leasings a cinzento), valuation impact com slider 4x–12x, "Shown, not counted", ponte de caixa. Evidence: mapa de cobertura, open items, ações por momento, encaminhamentos, downloads (a request list só exporta os aceites).
- **D, site**: página inicial com hero, três cartões (score, adjusted net debt, action title), verificação em 4 números e limites numa linha; página de empresa com faixa de estado, top 3, ponte de net debt e mapa de cobertura, e o botão para a ferramenta.
- **Motor (sem mexer em métricas nem regras):** `charts` marca os leasings como item standard (cinzento, fora do destaque); título da ponte em duas camadas; anotações longas por baixo do título. `deal_layer.issue_title` e `coverage_title` geram os títulos dos visuais 2 e 3.
- **Testes:** 304 OK. `tests/test_tool.py` (critérios 3 a 8 na ferramenta), `tests/test_site.py` (critérios 3, 7 e 9 no site); os testes da app antiga (página inicial, visita, glossário) saíram de `tests/test_demo.py`. `scripts/demo_review.py` mede os critérios 1, 2 e 9 no browser.

**Critérios de aceitação (secção 6)**
1. Summary a 1440×900 sem scroll: cumprido (top 5 acaba aos 817 px, nas três empresas).
2. 375 px sem scroll horizontal, score e primeiro KPI no primeiro ecrã, tabelas em cartões: cumprido (ferramenta e site).
3. Só as cores da paleta: cumprido (teste no CSS, nos SVG e no tema).
4. Severidade com forma e cor; leasings a cinzento: cumprido.
5. Cada cartão com fonte e documento a pedir: cumprido (teste nas três empresas).
6. Slider: muda na Duriva, não muda na TAP, e a anotação diz que os leasings não contam: cumprido.
7. Sem "Go", "No-Go", "recommend", "should buy": cumprido ("not a recommendation" fica, por ser o rótulo pedido; o teste procura a palavra "recommend" isolada).
8. Números visíveis no material; títulos gerados: cumprido.
9. Sem tabelas repetidas; página de empresa em 3 ecrãs: cumprido (1642 px).
10. Suite OK, paridade e Velmora sem mudança: cumprido.

**Decisões**
- O modo local (upload e IA) continua com a app antiga; só o modo demo (o publicado) é a ferramenta nova. Com o tema escuro, os cartões brancos da app antiga ficam claros sobre fundo escuro (em GAPS).
- A ferramenta usa um seletor de vistas (não separadores) para os chips e o top 5 poderem abrir Findings já filtrado.
- Os números de ordem (1 a 5) e as somas agrupadas ficam fora da verificação de números (`data-nocheck`), como no site.

**Próximo passo exato:** aprovação do Bernardo para o push; depois, ativar o GitHub Pages se ainda não estiver (passos em `docs/DEPLOY.md`).

## Fase 6 (docs/archive/FASE6_DESIGN.md, 17 de novembro de 2026)

**Feito** (três commits locais, sem push)
- **Erro do R11 corrigido.** O 4.º top issue da TAP (R11, €450m, High) era de FY23; em FY25 a dívida a menos de um ano é 2,8%. Um achado que só disparou antes do último ano testado passa a *historical*: Low, com o ano, em Findings; fora do top, do score e das ações. Teste `CurrentYearTest` (falha se um achado antigo entrar no top 5 como atual). Também históricos: R24 da TAP, R11/R27/R29/R25 da Toyota, R11/R10 da Amorim, R13/R14 da Duriva.
- **Scores novos:** TAP 40, Toyota 35, Amorim 21, Duriva 100, Velmora 0 (antes 54, 52, 32). Faixas: <25 *Few open points* (verde), 25–59 *Several* (âmbar), ≥60 *Many* (vermelho).
- **Top deal issues:** só achados e itens de diligence do último ano, todos os High abertos primeiro, por montante. TAP: R28 · Provisions · R22 · Pensions · R07. Leasings, receita diferida da TAP e o NWC contra o peg passam a **"Already in the price"** (`deal_layer.in_price`).
- **App:** barra do Streamlit escondida; barra própria (marca, TAP/Toyota/Amorim, FY, unidade, databook); herói com o score na cor da faixa, barra por área, frase simples e cada ponto por issue; KPIs coloridos (Leverage ↔ R21, FCF pelo sinal, Reading checks); legenda dos símbolos; linhas e cartões tingidos pela severidade; "blocked" passa a □; Evidence com ações agrupadas por ação e encaminhamentos por workstream; pontes a toda a largura (duas versões do SVG: larga e telemóvel).
- **Site:** o mesmo herói; cartões tingidos; "Already in the price"; "How the score works" em 3 passos com a TAP; verificação com **8 números** contados no build, cada um com a prova (311 testes · 30 regras · 100% das 123 linhas com fonte · 415 números do memo, 0 sem fonte · 10 de 10 subtotais · 48 de 49 distorções · 0 alarmes na Velmora · 27 de 27 totais Excel = Python).
- **Material do memo:** linhas do score com título, faixa, contagens, "Already in the price" e "Reading checks passed: N of M" (para o verificador conhecer cada número novo).
- **Bug antigo encontrado:** o teste de palavras proibidas do site tinha caracteres de controlo em vez de `\b` e não verificava nada; corrigido (agora igual ao da ferramenta).

**Critérios (secção 7), medidos por `scripts/demo_review.py`:** 1 topo legível (primeiro controlo aos 24 px, barra do Streamlit invisível) · 2 Summary sem scroll a 1440×900 nas três empresas (top 5 acaba aos 890 px); telemóvel sem scroll horizontal, score aos 257 px · 8 pontes ≥ 96% do cartão · 9 página de empresa 1958 px (< 3 ecrãs). Testes cobrem 3, 4, 6, 9 e 10. **311 testes OK.**

**Desvios ao desenho:** o Impact ficou empilhado (não em duas colunas) para as pontes ocuparem a largura; os títulos dos gráficos não foram encurtados a 70 caracteres (são gerados pelo motor e verificados no memo).

**Próximo passo exato:** aprovação do Bernardo para o push. Depois: reescrever os três memos de exemplo sem os achados históricos como key issues (GAPS).

## Fase 6b (17 de novembro de 2026, pedidos do Bernardo)

**Feito** (commits locais, sem push)
1. **Verificação em tom neutro** no site (cartões cinzentos, números brancos) e na app (Reading checks, "rules run", grelha de cobertura). O verde fica para o que é bom para o comprador.
2. **"Finding intensity" passa a "Diligence Gap"** (0 = nada em aberto, 100 = muito em aberto; "Higher = more to clarify"). "Not a recommendation" aparece uma vez, junto ao score principal, com tooltip; saiu dos cartões do site. Também no databook, no material e no `deal_layer.md`.
3. **O que fecha o gap:** as 3 questões com mais pontos e o score sem elas, pela mesma fórmula (TAP 40 → 17; Toyota 35 → 13; Amorim 21 → 6). Teste `ClosingTheGapTest`.
4. **Múltiplo:** EV = múltiplo × EBITDA reportado, equity value = EV − adjusted net debt, impacto dos achados em € e em % do equity value; "Illustrative, not a valuation"; sem ajustes ao EBITDA, uma linha diz que o impacto não depende do múltiplo. TAP: 6x EV €4,355m, equity €2,062m, −8.6%; 10x EV €7,258m, equity €4,966m, −3.6%. Valores de 6x, 8x e 10x no material. Teste `EquityViewTest`.
5. **Evidence:** os chips quebram linha dentro dos cartões (0 fora, a 1440 e 375 px, medido pelo `demo_review.py`).
6. **Request list por prioridade** (`deal_layer.prioritised_requests`, regra em `PRIORITY_DETAIL`): P1 "Before signing" (High atual, top deal issue ou item material que mexe no preço/SPA; máx. 10, por montante), P2 "During the diligence" (Medium, itens por classificar, regras bloqueadas que afetam o valor), P3 "To complete the picture" (o resto). Por tema; cada pedido com a ligação. App ("Start with these N" + P2/P3 em secções), site, databook (Issues & Requests), export e material. P1: TAP 7, Toyota 7, Amorim 5 (Duriva 10, com o limite). Teste `PrioritisedRequestsTest`.
7. **Pontas soltas:** históricos contam zero (já estava); os três memos com a tabela de key issues de FY25 gerada pelo motor, verificador sem avisos (143, 133, 138 números); site sem título de gráfico repetido nos cartões, meta description própria, legenda antiga trocada por uma linha sobre a cor; nota de arredondamento por baixo do título do gráfico (TAP 2,292 vs 2,293); cash conversion com a definição ("operating cash flow ÷ EBITDA"); README com o link da demo uma vez no texto; o workflow das Pages publica a cada push a main (sem filtro de caminhos; Pages ativo, `build_type: workflow`, último deploy com sucesso).

**Capturas e critérios** (`scripts/demo_review.py`, 1440 e 375 px): topo legível; Summary sem scroll (top 5 acaba aos 832 px); telemóvel sem scroll horizontal, score aos 257 px; múltiplo 6x vs 10x muda EV e equity; chips do Evidence dentro dos cartões; pontes ≥ 96% do cartão; página da TAP 2609 px (< 3 ecrãs). **317 testes OK.**

**Próximo passo exato:** aprovação do Bernardo para o push.

## Arrumação antes da Fase 7 (21 de novembro de 2026, pedidos do Bernardo)

**Feito** (commits locais, sem push)
1. **Site:** saiu o "Answer these 3: 40 → 17" (página inicial e páginas de empresa); ficam os 3 principais issues, numa lista "Main issues". A app Streamlit não mudou. A verificação "48 of 49" fica neutra: a falha passa a uma linha cinzenta com link para `docs/DETECTION.md`. O teste do site pede agora pelo menos 3 números verificados por cartão (os cartões ficaram com score, ano e net debt).
2. **Repositório:** `tool.py` passou para `dd_assistant/tool.py`; o prompt do memo para `dd_assistant/ai_memo_prompt.md` (é lido pelo código); as especificações antigas (FASE2 a FASE6, DEMO_*, FABLE_REVIEW*, DEMO.md) para `docs/archive/`; `VALIDATION.md` e `REVIEW_SHEET.xlsx` para `docs/examples/validation/`; o memo da Amorim FY2024 para `docs/examples/corticeira-amorim-fy2024/`. Removidos: `scripts/demo_screenshots.py` (já não corria) e seis imagens que nada usava. README curto; o detalhe técnico passou para `docs/ARCHITECTURE.md`. LICENSE (MIT). Links internos verificados por script (0 partidos).
3. **Fase 7 desenhada:** `docs/FASE7_SPEC.md` (A: qualquer cotada da UE pelo ESEF; B: data room desarrumado da Duriva com mapeamento e proof of cash; C: diligence viva com o Diligence Gap a evoluir). Nada construído; a ordem é A, B, C.

**Próximo passo exato:** revisão da especificação pelo Bernardo e aprovação do push; depois, a peça A.

## Fase 7, peça A: qualquer cotada da UE pelo ESEF (22 de novembro de 2026)

**Feito** (commit local, sem push)
- **Pesquisa** (`dd_assistant/registry.py`): o nome dá os LEI pela GLEIF (`fuzzycompletions`); um só pedido ao filings.xbrl.org diz quais têm relatórios (o site limita pedidos: respondeu 429 quando se perguntava LEI a LEI); depois, os relatórios do primeiro, o mais recente primeiro, com país, ano e tamanho (HEAD dos 4 mais recentes). Um LEI salta a GLEIF. Um 429 é repetido com espera (até 3 vezes).
- **Descarga** só com clique ou `--yes`, para `output/esef_cache/` (fora do git), até 300 MB. O SHA-256 é comparado com o que o filings.xbrl.org publica e vai para o Source Register com o URL.
- **Proteção do ZIP** (`esef.check_package`): 300 MB descompactados, rácio de compressão até 200 em cada ficheiro acima de 1 MB, 5 000 ficheiros, nenhum caminho com `..`, absoluto ou com letra de disco. Lacuna do GAPS fechada.
- **Aviso de qualidade** (`dd_assistant/esef_quality.py`): *Complete*; *Notes missing: …* (text blocks IFRS de borrowings, provisions, leases, related parties, other income, segments); *Reading check failed, do not rely* (subtotal que não fecha, balanço que não fecha, a mesma etiqueta com dois valores no mesmo período, nenhum subtotal para verificar, ou D&A em falta). Um quarto estado, *Not analysed*, com o motivo, para o que não chega a ser lido. Aparece na app, no Read Me do databook, no material do memo (secção 7), no JSON e na linha de comandos.
- **Entrada:** "Find a listed company" na app local (barra lateral); `--esef "<nome>"`, `--lei <LEI>`, `--year`, `--yes` na linha de comandos, com o tempo de cada passo.
- **Testes:** `tests/test_registry.py` (8, respostas reais gravadas em `tests/fixtures/registry/`, nenhum pedido à rede) e `tests/test_esef_quality.py` (12: os níveis, o ZIP-bomba, o limite, o caminho fora da pasta). **337 testes**: suite completa corrida uma vez, 336 OK; a falha era o site com o número antigo de testes (317), regenerado com `scripts/build_site.py`, e o `test_site` passou a seguir.

**Três cotadas novas** (`docs/examples/esef_coverage.md`, `scripts/esef_coverage.py --fresh`, tempos com a descarga):

| Empresa | Qualidade | Regras | Reading checks | Tempo |
|---|---|---|---|---|
| Jerónimo Martins (retalho, PT, FY2025) | Complete | 19 de 30 | 4 de 4 | 9,6 s |
| Schneider Electric (industrial, FR, FY2025) | Complete | 21 de 30 | 4 de 4 | 10,3 s |
| Iberdrola (energia, ES, FY2025) | Notes missing: other income | 20 de 30 | 4 de 4 | 2,8 s |
| Siemens (DE) | Not analysed: não está no filings.xbrl.org | — | — | 0,6 s |

**Primeira corrida, antes das correções** (registada também no `esef_coverage.md`): a JM falhava a reading check por €1m (contas em milhões); a Schneider não era lida (ficheiros da taxonomia sem o prefixo `link:`) e depois tinha o balanço em duas partes, D&A em conceitos próprios com nome IFRS e reestruturação e imparidade do goodwill entre o EBITA e o resultado operacional; a Iberdrola era recusada (pacote `.xbri`) e depois tinha os custos com o sinal de ganhos (conceitos próprios definidos como credores).

**Decisões (a opção mais simples e defensável)**
- **Arredondamento em milhões:** a tolerância das reading checks continua a ser meia unidade impressa por linha; quando todas as linhas são múltiplos de €1m, a unidade é o milhão. Não reconheço €100k (milhões com uma casa decimal): nas empresas fictícias, três linhas redondas por acaso alargariam a tolerância.
- **Sinal das extensões:** o esquema da empresa (`.xsd`) dá o saldo dos conceitos próprios; um conceito credor que o dicionário lê como custo (ou devedor lido como rendimento) muda de sinal à entrada, com "(sign turned: credit concept)" no rótulo. Os conceitos IFRS não mudam (o saldo deles condiz com o nome).
- **Balanço em duas partes:** a segunda completa a primeira só quando a primeira tem o ativo sem capital próprio e passivo e a segunda o contrário. Noutros casos, continua a valer a primeira demonstração de cada tipo.
- **Conceito próprio com nome IFRS** (`schneiderelectric:AdjustmentsForDepreciationOfPropertyPlantAndEquipment`): lido como o conceito IFRS; a etiqueta, que é a fonte, mostra que é da empresa.
- **Reestruturação e imparidade do goodwill** entram em "Other expenses (incl. write-downs and provisions)", como no template; o EBITDA fica prudente (inclui a imparidade como custo).
- **SHA-256 diferente do publicado:** a descarga é recusada e apagada (não é o relatório que o registo lista).
- **D&A em falta** passou a falha de leitura: sem ela, as reading checks passavam com o EBITDA igual ao resultado operacional (aconteceu na Schneider a meio das correções).
- **Escolha do relatório:** a primeira empresa da GLEIF com relatórios e o relatório mais recente, salvo `--year`; a app deixa escolher qualquer um da lista.
- **Setor:** nas três, o motor sugeriu mal (JM e Iberdrola "Industrial distribution", pela palavra *distribution*; Schneider "General"). As corridas do `esef_coverage.md` usam o setor que um revisor escolheria; a sugestão fica registada ao lado.

**Critérios de aceitação da especificação**
1. Testes sem rede e sem API: cumprido.
2. Cinco cotadas de cinco países: **3 de 5** (PT, FR, ES). Pedido do Bernardo: 3 empresas de setores diferentes. A Siemens (DE) não está no filings.xbrl.org; IT não foi tentada.
3. EDP FY2025 ao milhar: **cumprido** (reconferido a 22 de novembro de 2026, com autorização do Bernardo). Pesquisa pelo LEI `529900CLC3WDMGI9VH80`, pacote de 91,8 MB descarregado do filings.xbrl.org em 81 s, SHA-256 igual ao publicado (`1b95264f…5c229968`); resultado operacional reconstruído em 2,999,414 (FY25) e 2,261,983 (FY24) milhares de euros, diferença zero; *Complete*; 20 de 30 regras; 2 de 2 reading checks; leitura e análise em 2,8 s.

**Capturas** (1440 px, `scripts/esef_screenshots.py`, Playwright com o Edge): `docs/images/esef-search.png` (pesquisa com a Schneider encontrada) e `docs/images/esef-result.png` (resultado com o aviso "Complete", 21 de 30 regras, 4 de 4 checks).

**Revisão de segurança automática (depois do commit):** dois achados no `registry.py`, ambos corrigidos. (1) Os URLs das respostas dos registos (pacote, página seguinte) e os redirecionamentos eram seguidos sem limite: agora só `https` em `api.gleif.org` e `filings.xbrl.org`; o resto é recusado (ou, numa resposta, ignorado). (2) O nome do ficheiro na cache usava o LEI, a data e o nome do pacote como vinham: agora são validados e o caminho tem de ficar dentro da cache. Três testes novos. Um teste antigo (limite de 300 MB) passou a substituir o opener próprio; antes da correção desse teste, chegou a fazer um pedido real à rede.

**Pesquisa pelo nome antigo:** "EDP Energias de Portugal" não encontra a EDP (o nome legal é "EDP, S.A." desde 2022); "EDP, S.A." e o LEI encontram. Fica em GAPS.

### Revisão da peça A (22 de novembro de 2026, pedidos do Bernardo antes do push)

Só regras gerais, nada ajustado a uma empresa. Commit local, sem push.

1. **EDP reconferida com o leitor novo.** Corri o pacote FY2025 com o leitor de antes da peça A (commit `6c21aa7`, num worktree temporário) e com o atual: todas as linhas, reading checks, EBITDA (reportado e ajustado), net debt (reportada e ajustada), NWC, achados e itens de balanço iguais. Depois das mudanças 2 e 3: net debt ajustada igual (€18,284m: a EDP tem linha de dívida corrente); aviso *Complete* → *Notes missing* (outros passivos financeiros correntes de €1,141m, nenhuma nota lida os classifica); setor sugerido Energy, agora a partir da atividade declarada.
2. **Passivos financeiros correntes por classificar** (`extract._presume_current_debt`, `esef_quality.unclassified`). Regra: se a empresa tem financiamentos mas nenhuma linha de dívida corrente, os passivos financeiros correntes não classificados como dívida passam a "Current financial liabilities (no current borrowings line)", entram na net debt ajustada (visão prudente do comprador) com montante, fonte e a pergunta "No current borrowings line is presented: is this €X the current portion of borrowings…?". Com linha de dívida corrente, ficam "to assess", como antes. Em qualquer caso, um passivo destes material (acima da materialidade de balanço) que nenhuma nota classifique baixa o aviso ESEF para *Notes missing*. **Schneider: net debt ajustada €11,435m → €14,294m** (+€2,859m); NWC −€1,102m → €1,757m (a dívida sai do fundo de maneio).
3. **Setor por fonte objetiva** (`sectors.suggest`, `sectors.declared_activity`). Nem o ESEF nem a GLEIF têm código NACE. A sugestão passou a usar só o que a empresa declara: a etiqueta ESEF das atividades principais ou um campo "Atividade |" do data room (primeira frase, sem os clientes servidos) e a denominação legal; nunca palavras soltas do resto do data room. Expressões mais longas primeiro ("distribuição alimentar" é retalho alimentar, não distribuição grossista). Sugere-se o setor com mais palavras distintas do que qualquer outro; empate ou nada → **"Sector to be confirmed"** (limites gerais até o revisor escolher), na app, na linha de comandos, no JSON e no material do memo. Dicionário: palavras de energia em espanhol, francês, italiano e alemão e expressões de retalho alimentar nas seis línguas.

| Empresa | Setor antes | Setor agora | De onde vem |
|---|---|---|---|
| Jerónimo Martins | Industrial distribution (errado) | Consumer & retail | atividade declarada: "distribuição alimentar" |
| Schneider Electric | General (sem palavra) | Sector to be confirmed | o objeto declarado não aponta para um setor |
| Iberdrola | Industrial distribution (errado) | Energy & utilities | atividade declarada: "electricidad", "renovables" |
| TAP | Transport | Transport | denominação legal: "Transportes" |
| Toyota Caetano | Automotive | Automotive | denominação legal: "Toyota" |
| Corticeira Amorim | Materials | Materials | denominação legal: "Corticeira" |
| EDP (extra) | Energy | Energy | atividade declarada: "energia elétrica", "gás natural" |
| Duriva, Velmora | Distribution | Distribution | "Atividade \| Distribuição B2B…" |

**TAP, Toyota e Amorim não mudam:** comparei o motor de antes (6c21aa7) e o de agora, na análise direta e na da demo (com notas e três anos): setor, EBITDA, net debt ajustada, NWC, reading checks, achados, key issues e Diligence Gap (40, 35, 21) idênticos.

**Testes novos:** `UnclassifiedFinancialLiabilitiesTest` (4, em `tests/test_esef_quality.py`: o pacote sintético com a dívida corrente etiquetada como outros passivos financeiros dá a mesma net debt ajustada, a pergunta, *Notes missing*; a Amorim fica "to assess") e 4 em `tests/test_sectors.py` (as seis empresas e a EDP, palavras fora da declaração não contam, empate). **Suite completa uma vez: 347 testes, 346 OK**; a falha era o site com o número antigo de testes (340), regenerado; o `test_site` passou a seguir.

**`docs/examples/esef_coverage.md`** regenerado com descargas novas (`--fresh`): coluna do setor sugerido e da net debt ajustada, secção da revisão. Os tempos de descarga desta vez foram ~1 s por pacote (o servidor já os tinha em cache), contra 7–8 s na primeira corrida.

**Próximo passo exato:** revisão do Bernardo e aprovação do push; depois, a peça B.

## Definição de net debt (22 de novembro de 2026, antes da peça B)

**Feito** (commit local, sem push)
- **Motor** (`dd_assistant/net_debt_definition.py`): cada componente da net debt (empréstimos não correntes e correntes, caixa e cada item debt-like ou cash-like do balanço) com valor, fonte, grupo (Borrowings, Cash, Leases, Pensions, Taxes, Provisions, Other debt-like, Other cash-like, To assess) e interruptor. Três predefinições: **Buyer (conservative)** (a do motor: dá a net debt ajustada), **Seller** e **Custom** (qualquer interruptor mudado). A tabela `RULES` tem, por categoria, comprador, vendedor e a razão numa linha. `evaluate` recalcula net debt, leverage (sobre o EBITDA *diligence-adjusted*), EV ao múltiplo, equity value e impacto dos achados com as mesmas fórmulas de `deal_layer.equity_view` e `valuation_impact`; a app só escolhe.
- **App** (separador Impact da ferramenta): no topo, net debt do comprador, do vendedor e "In negotiation"; a predefinição; uma tabela com um interruptor e um motivo opcional por componente; os cartões (EV, net debt e leverage, equity value, impacto) recalculam; cada alteração fica registada (quando, item, incluído ou não, motivo); botão "Download databook with this definition". Os gráficos por baixo continuam a ser a visão do comprador (legenda à vista).
- **Databook:** folha **"SPA net debt schedule"** (item, grupo, valor, fonte, comprador, vendedor, escolha a amarelo, motivo, razão das predefinições); totais por SUMIFS para comprador, vendedor e escolha, e a diferença; o registo das alterações por baixo; três controlos novos na Checks. Databooks da demo regenerados e recalculados pelo Excel: **12 de 12 totais = Python** nas três empresas (eram 9).
- **Site:** uma linha na página de cada empresa ("Net debt definition, FY25: seller's view to buyer's view"); os números estão no material do memo (secção 1c), como o teste do site exige.

**Resultados**

| Empresa | Comprador | Vendedor | Em negociação |
|---|---|---|---|
| TAP | €2,293m | €2,073m | €220m |
| Toyota Caetano | €78,039k | €72,385k | €5,654k |
| Corticeira Amorim | €83,638k | €36,597k | €47,041k |

TAP, à mão a partir do balanço publicado (p.152): o vendedor tira as pensões (173,153.669) e o imposto a pagar (3,873.215) e conta como caixa os outros ativos financeiros (680.947 + 13,178.431) e os ativos detidos para venda (28,869.179): 2,292,544.633 − 219,755.441 = 2,072,789.192. Só empréstimos e caixa: −42,784.156 = borrowings less cash. Visto no browser: excluir as pensões dá net debt €2,119m, leverage 2.92x, equity value €3,687m e impacto −€4m a 8x; "Seller" dá €2,073m, 2.86x e impacto +€43m.

**Decisões (a opção mais simples e defensável)**
- **Comprador = o motor**, sem exceção: um teste obriga a coluna do comprador a ser igual às predefinições de `extract.DEBT_LIKE` e `CASH_LIKE`. Assim a net debt ajustada, o Diligence Gap, o databook e o memo não mudam.
- **Vendedor** (a posição habitual de um vendedor, não uma regra de mercado): leasings dentro (o EBITDA é pós-IFRS 16, os dois lados costumam aceitar); pensões, imposto sobre o rendimento, *deferred consideration*, *factoring* e dívida presumida fora; títulos negociáveis, outros ativos financeiros, caixa restrita e ativos detidos para venda dentro como caixa. Provisões e itens "to assess" fora nos dois.
- **"In negotiation"** = net debt do comprador menos a do vendedor, mostrada em valor absoluto e a cinzento (o âmbar é só para Medium).
- **Impacto dos achados** com a definição escolhida: ajustes de EBITDA × múltiplo mais os itens de balanço incluídos que não são empréstimos, caixa ou leasings (o mesmo critério de `valuation_impact`). Com a escolha do vendedor pode ficar positivo (TAP +€43m), porque itens cash-like contam a favor.
- **Registo:** a mudança de predefinição também fica registada. As decisões vivem na sessão do browser, como as outras decisões da ferramenta; saem no databook descarregado.
- **Captura:** `docs/images/tool-impact-net-debt-definition.png` (TAP, 1440 px, Playwright com o Edge).

**Testes:** `tests/test_net_debt_definition.py` (9: predefinições da TAP, só empréstimos e caixa, um interruptor mexe net debt, leverage, equity e impacto mas não o EV, o comprador dá os números de hoje nas três empresas a 6x, 8x e 10x, a tabela, a folha e Excel = Python). `test_databook` e `test_demo` atualizados (folha nova; 3 controlos a mais). **Suite completa uma vez: 356 testes, 355 OK**; a falha era o site com o número antigo de testes (347), regenerado; o `test_site` passou a seguir.

**Próximo passo exato:** revisão do Bernardo e aprovação do push; depois, a peça B.

## Fase 7, peça B: data room desarrumado da Duriva (22 de novembro de 2026)

**Feito** (commits locais por bloco, sem push). Tudo é **FICTITIOUS, synthetic test data**, escrito em cada ficheiro e folha.

| Bloco | Commit | O quê |
|---|---|---|
| 1 | `b3984f7` | `scripts/duriva_messy.py` gera `data/Duriva_messy_data_room/` a partir das contas anuais da Duriva: plano de contas próprio (códigos ERP, nomes abreviados), balancetes anuais 2023–2025, 36 exportações mensais em três formatos (CSV `;` e 1.234,56 com título acima do cabeçalho; CSV `,` e (1,234.56) com 'jan-24' e Windows-1252; Excel com o cabeçalho na linha 5 e as colunas 'Saldo' e 'Movimento' trocadas), a conta de clientes renomeada (4120 → 4121) em julho de 2024, agosto de 2024 em falta, extratos de dois bancos (CSV e PDF de texto), mapas de fornecedores. `ledger.py` e `mapping.py`. |
| — | `dbfd2c3` | `.gitattributes`: PDF, Excel, PowerPoint e PNG como binários (o Git ia converter fins de linha dentro dos PDF). |
| — | `e46341f` | **Estimativa manual fixada antes da corrida do agente** (`docs/examples/duriva-messy/manual_estimate.md`). |
| 2 | `b4b534c` | `proof_of_cash.py`, regras R31 e R32, `ledger_room.py` (o data room lido inteiro), peg de 12 meses e LTM. |
| 3 | `cec405b` | Folhas Mapping, Proof of Cash e Monthly & LTM no databook; `timing.py`; `scripts/duriva_messy_report.py` (databook, `timing.md`, `coverage.md`). |
| 4 | (este commit) | App: modo do data room desarrumado (separadores Mapping, Proof of cash, Time: manual vs agent); capturas. |

**Resultados (Duriva desarrumada)**
- **Leitura:** 36 contas, 36 meses; colunas trocadas detetadas pelo conteúdo (a coluna do saldo é a que continua o saldo do mês anterior); conta renomeada ligada (a nova abre no saldo de fecho da antiga); agosto de 2024 reconstruído a partir de setembro e marcado como derivado; os três balancetes iguais às exportações de dezembro (36 de 36).
- **Mapeamento:** 33 de 36 contas com confiança **High (91,7%)**; Medium: OIN520 (mais-valias; as palavras apontam também para ativos fixos, o comportamento decide); Low: MSC990 ("Diversos") e SUS999 (conta transitória, nula). As Low **nunca entram pelo agente**: ficam pendentes e a ligação às contas anuais mostra a diferença (outros gastos e equity, €13,5k–€16,5k por ano) até o revisor decidir. Com as duas decisões: **78 de 78 linhas iguais às contas anuais ao euro** (3 anos de DRE, 4 fins de ano de balanço).
- **Proof of cash:** 72 meses-banco, todos fecham (saldo inicial + recebimentos − pagamentos = saldo final). As três distorções plantadas foram encontradas e confirmadas contra a chave guardada **fora do projeto** (`projetos/Duriva_messy_gabarito.json`): Banco Meridiano, set-2025, €258,000 ("um recebimento no razão que não está no banco"; aparece também no teste dos recebimentos contra receita + IVA − variação de clientes); Banco Norte, nov-2025, €232,000 ("uma transferência entre bancos contada duas vezes": o montante é o de uma transferência desse mês); fornecedores, 31-12-2025, mapa €227,000 abaixo do razão. Velmora desarrumada, gerada da mesma forma sem nada plantado: **zero diferenças e zero alertas analíticos**.
- **Regras:** os 15 achados da Duriva limpa, iguais (regra, ano, severidade), mais **R31** (High, €490k de caixa sem banco, material) e **R32** (Medium, €227k). Cobertura: só com as três demonstrações anuais, **22 de 32** regras (como a TAP); com o data room inteiro, **31 de 32**: desbloqueiam R01, R02, R05, R06, R16, R17, R20, R31 e R32 (`docs/examples/duriva-messy/coverage.md`).
- **Databook:** folhas Mapping, Proof of Cash e Monthly & LTM com fórmulas; **25 de 25 totais Excel = Python**.
- **Dados mensais:** média dos últimos 12 fins de mês €4,168k (contra €3,742k da média dos fins de ano); LTM a dez-2025 igual ao FY25 (receita €21,400k, EBITDA €1,415k).
- **Tempo:** manual estimado **620 min (10,3 h)** contra agente **1,2 s** medidos no script (1,1 s na app) **+ revisão por cronometrar**; lado a lado por tarefa (`docs/examples/duriva-messy/timing.md` e o separador da app).

**Decisões (a opção mais simples e defensável)**
- **Gabarito.** O `Duriva_gabarito.xlsx` original **não está neste PC** (procurei em todo o perfil). O teste que o lê (`OriginalAnswerKeyTest`) corre quando `DD_GABARITO` aponta para ele; aqui ficou saltado. Em vez dele, um teste exige que os achados vindos do data room desarrumado sejam os da Duriva limpa. As três distorções novas têm a chave escrita pelo gerador fora do projeto. **O gerador, por ter de as plantar, descreve-as no código** (`PLANTED`); o motor e os testes de deteção não o leem.
- **Os números vêm do razão.** As linhas da DRE e do balanço são a soma das contas mapeadas, com ficheiro e linha; as contas anuais verificam o mapeamento e dão a DFC e os mapas que um razão não tem.
- **Confiança:** High = uma regra (palavras da conta, código SNC de 6 dígitos ou dicionário das demonstrações) e o comportamento do saldo concorda; Medium = regras que apontam para linhas diferentes ou comportamento contrário; Low = só o comportamento. O dicionário das demonstrações não conta quando aponta para duas linhas (empréstimos correntes e não correntes têm os mesmos sinónimos).
- **Decisões do revisor.** As do exemplo (`docs/examples/duriva-messy/mapping_decisions.json`) foram tomadas por mim para o exemplo e dizem-no ("to be confirmed by Bernardo"). Na app, cada decisão pede o motivo e fica registada.
- **Regras novas fora do template:** R31 (> €5k, High) e R32 (> €5k, Medium); a materialidade decide o resto. Nas cotadas ficam "não aplicáveis" (extratos e mapas não são públicos), por isso a TAP passou de "22 of 30" para "22 of 32 rules run". IVA a 23% no teste dos recebimentos, numa célula amarela do databook.
- **Velmora "zero alertas":** a R18 (documentos em falta) dispara também na Velmora limpa quando lida pelo data room; o zero é de alertas analíticos, como na Velmora do template.
- **Tempo do revisor:** não estimado. A app tem um campo para o Bernardo pôr os minutos quando os cronometrar.

**Testes novos:** `test_ledger.py`, `test_mapping.py`, `test_proof_of_cash.py` (um saltado sem o gabarito original), `test_databook_ledger.py`. **Suite completa uma vez: 388 testes, 386 OK, 1 saltado**; a falha era o site com o número antigo de testes, regenerado; o `test_site` passou a seguir. Atualizados: `test_rules`, `test_clean_company`, `test_deal_layer`, `test_tool`.

**Capturas (1440 px):** `docs/images/messy-mapping.png` (duas contas à espera do revisor, 92% High, 72 de 78 linhas ligadas), `messy-proof-of-cash.png` (as duas diferenças de caixa com o diagnóstico, o gráfico mês a mês, o mês dos recebimentos), `messy-time.png` (620 min contra 1,1 s, tarefa a tarefa).

**Próximo passo exato:** revisão do Bernardo (estimativa manual, decisões do exemplo, cronometrar a revisão) e aprovação do push; depois, a peça C.
