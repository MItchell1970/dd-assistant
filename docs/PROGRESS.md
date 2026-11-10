# Fase 2 — progresso

Ficheiro de retoma. Especificação: `docs/FASE2_SPEC.md`. Atualizado no fim de cada incremento.

**Estados:** construído · testado automaticamente · conferido contra a fonte · revisto pelo Bernardo. Um estado só aparece quando aconteceu.

## Agora

- **Módulo:** M2, databook.
- **M0 concluído:** M0.1 (o verificador do memo liga cada número ao ano citado), M0.2 (ausência ≠ zero), M0.3 (R13 com descobertos; a Amorim ficou fechada com a nota 19 do relatório publicado, conferida no PDF descarregado com autorização do Bernardo), M0.4 (alertas das empresas reais classificados; contagem em `docs/VALIDATION.md`).
- **M2 feito até agora:** databook com as 12 folhas (`dd_assistant/databook.py`), fórmulas nos totais e pontes, recálculo pelo Excel e comparação com o Python; na app (botão "Download databook") e na linha de comandos (`--databook`).
- **M2e feito:** R27 (D&A muito acima do imobilizado), R28 (rubrica "outra" acima de 10% da receita, listada "a avaliar" no net debt), R29 (crescimento com aquisições), EBITDA antes da IFRS 16 (QoE) e nota IFRS 16 (Net Debt). Dividendos como possível leakage ficam para o M3.
- **M3 feito:** `dd_assistant/price.py` (completion accounts, locked box, leakage, sensibilidade), candidatos a leakage lidos da DFC (dividendos pagos), folhas EV to Equity e Leakage no databook, secção "Price" na app (mecanismo obrigatório, sem escolha por defeito).
- **Parado aqui, como pede a especificação:** fim do M3, à espera do resumo revisto pelo Bernardo. Depois, com aprovação: versão simples do M6.
- **Comando para retomar:** `python -m unittest -v` (tem de dar 192 testes OK) e `python -m dd_assistant data\Duriva_data_room --databook`.

## Diagnóstico (4 de novembro de 2026)

Estado confirmado no repositório: 21 commits no ramo `main`, igual ao GitHub; 124 testes a passar; só `docs/FASE2_SPEC.md` e `docs/FASE2_INICIO.md` por registar. A app foi verificada em sessões anteriores em modo headless (Streamlit AppTest) e no browser; nesta fase ainda não foi aberta.

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
| M6 simples | README atualizado (29 regras, databook, preço, limites); roteiro de demo em `docs/DEMO.md`; fluxo da app visto no browser (Overview → Deal view → Price: CA €7,099k na Duriva, sem erros na consola) | Sim | 165 testes OK | Números do roteiro conferidos na app | Databook revisto pelo Bernardo no Excel (exercício Net Debt → NWC, Toyota); README e roteiro pendentes |
| M3 | EV → equity (completion accounts, locked box), registo de leakage, sensibilidade só com EV derivado; folhas no databook; secção na app | Sim | 165 testes OK (14 em `tests/test_price.py` com os casos da secção 6; 1 no databook recalculado); app headless: sem mecanismo não calcula, CA €7,099k e LB €9,050k na Duriva | Casos da especificação (esperados escritos na especificação); Duriva conferida à mão (EV 10,000 + 603 − 4,350 + 846) | Pendente |
| M2e | Regras R27–R29, item "a avaliar" para rubricas "outras" materiais, EBITDA antes da IFRS 16 | Sim | 149 testes OK; Velmora continua com zero alertas analíticos | Toyota: esperados calculados à mão a partir da DRE, Balanço e DFC publicados (`test_what_a_reviewer_found`) | Pendente |
| M2a–d | Databook: Read Me, Executive Summary, Source Register (com SHA-256), Financials, QoE (registo de ajustes com estado), NWC (política de inclusão), Net Debt (classificação e inclusão), Issues & Requests (pedidos fundidos), Checks; EV to Equity, Leakage e Monthly & LTM dizem que ainda não existem | Sim | 148 testes OK (10 novos em `tests/test_databook.py`, 2 recalculam no Excel); app headless com o botão nas 4 amostras | Totais do Excel = Python na Duriva e na Toyota (11 e 6 controlos) | Pendente (inspeção visual tua) |
| M0.1 | `memo_check` liga cada número ao ano citado | Sim | 127 testes OK (3 novos em `PeriodTest`) | Valores da Toyota conferidos na DRE publicada (outros rendimentos FY23 27.739.438 €, FY24 34.746.983 €) | Pendente |
| M0.4 | Alertas das empresas reais classificados (5 verdadeiros positivos, 4 por rever; o alarme falso da Amorim foi resolvido no M0.3); `scripts/validation_report.py` escreve `docs/VALIDATION.md` | Sim | 138 testes OK | Classificação feita a partir dos números publicados (Toyota DRE/DFC, Amorim DR/DFC) | Pendente: a classificação é uma proposta |
| M0.3 | R13: diferença explicada por descobertos ou caixa restrita passa a reconciliação (memo no net debt) | Sim | 138 testes OK (4 novos em `tests/test_cash_reconciliation.py`); paridade igual | Sim: Amorim, nota 19 (p. 426), igual ao milhar nos dois anos | Pendente |
| M0.2 | Ausência ≠ zero: net debt, NWC, FCF, R12, R14, mapa da dívida; avisos "incompleto" na app, no Excel, no memo e no JSON | Sim | 133 testes OK (6 novos em `tests/test_absence.py`); app headless sem erros nas 4 amostras | Não aplicável (casos construídos a partir da Velmora) | Pendente |

## Demo online (docs/DEMO_ONLINE_SPEC.md)

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

## Demo UX (docs/DEMO_UX_SPEC.md, 9 de novembro de 2026)

A secção 6b referida na mensagem do Bernardo não estava no ficheiro; as 10 lições da mensagem foram aplicadas.

- **Credibilidade (secção 2):** contas consolidadas passam a IFRS por defeito (o SNC fica para contas individuais); cartão do working capital com a nota do setor ("normal for airlines"), a cor continua a vir dos achados de NWC (R07 High, limites sem mudança); cabeçalho com nome curto, nome legal, relatório e páginas e uma só unidade; o método de leitura passou para o separador Data room.
- **Key insights e cascatas:** os três pontos da case note no topo; cascatas de net debt (por categoria: leasings €2,158m na TAP), EBITDA e EBITDA antes da IFRS 16, e NWC com a média. Passos calculados em `deal.py`; o gráfico só desenha.
- **Página inicial:** frase de valor, autor, para quem, limites, três botões (TAP, Excel, código), nota dos dados, 5 passos, cartões com um número grande, o databook, "How it is verified" calculado na página, Measured / Not measured, How you check it, glossário.
- **Barra lateral recolhida** com "About this demo"; glossário ao passar o rato; fonte em cada cartão (p.152, p.153, p.156 na TAP); barra do Streamlit em modo minimal.
- **Visita de 60 segundos** (`st.dialog`, 5 passos, com a página do relatório no red flag).
- **Imagens:** GIF de 23 s, página inicial, cascata da net debt, Excel e social preview 1280×640, por `scripts/demo_screenshots.py`; verificação a 1440 e 375 px por `scripts/demo_review.py`.
- **Testes:** 203 OK.
- **Pendente:** confirmar a linha "Built by … ex-EY Transaction Services intern" (o README diz "International Tax and Transaction Services"); push com aprovação; carregar a social preview no GitHub.

## Fase 3 (docs/FASE3_SPEC.md, 10 de novembro de 2026)

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

