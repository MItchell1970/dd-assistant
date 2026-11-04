# Fase 2 — progresso

Ficheiro de retoma. Especificação: `docs/FASE2_SPEC.md`. Atualizado no fim de cada incremento.

**Estados:** construído · testado automaticamente · conferido contra a fonte · revisto pelo Bernardo. Um estado só aparece quando aconteceu.

## Agora

- **Módulo:** M2, databook.
- **M0 concluído:** M0.1 (o verificador do memo liga cada número ao ano citado), M0.2 (ausência ≠ zero), M0.3 (R13 com descobertos; a Amorim ficou fechada com a nota 19 do relatório publicado, conferida no PDF descarregado com autorização do Bernardo), M0.4 (alertas das empresas reais classificados; contagem em `docs/VALIDATION.md`).
- **M2 feito até agora:** databook com as 12 folhas (`dd_assistant/databook.py`), fórmulas nos totais e pontes, recálculo pelo Excel e comparação com o Python; na app (botão "Download databook") e na linha de comandos (`--databook`).
- **M2e feito:** R27 (D&A muito acima do imobilizado), R28 (rubrica "outra" acima de 10% da receita, listada "a avaliar" no net debt), R29 (crescimento com aquisições), EBITDA antes da IFRS 16 (QoE) e nota IFRS 16 (Net Debt). Dividendos como possível leakage ficam para o M3.
- **Próximo passo:** M3, EV → equity, completion accounts, locked box e leakage.
- **Comando para retomar:** `python -m unittest -v` (tem de dar 149 testes OK) e `python -m dd_assistant data\Duriva_data_room --databook`.

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
- **M2, inspeção visual: pendente.** Não consigo ver imagens do Excel neste PC. Exportei o PDF pelo Excel e conferi o texto (28 páginas, sem `####` nem erros de fórmula). Falta abrires o ficheiro.

## Incrementos

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| M2e | Regras R27–R29, item "a avaliar" para rubricas "outras" materiais, EBITDA antes da IFRS 16 | Sim | 149 testes OK; Velmora continua com zero alertas analíticos | Toyota: esperados calculados à mão a partir da DRE, Balanço e DFC publicados (`test_what_a_reviewer_found`) | Pendente |
| M2a–d | Databook: Read Me, Executive Summary, Source Register (com SHA-256), Financials, QoE (registo de ajustes com estado), NWC (política de inclusão), Net Debt (classificação e inclusão), Issues & Requests (pedidos fundidos), Checks; EV to Equity, Leakage e Monthly & LTM dizem que ainda não existem | Sim | 148 testes OK (10 novos em `tests/test_databook.py`, 2 recalculam no Excel); app headless com o botão nas 4 amostras | Totais do Excel = Python na Duriva e na Toyota (11 e 6 controlos) | Pendente (inspeção visual tua) |
| M0.1 | `memo_check` liga cada número ao ano citado | Sim | 127 testes OK (3 novos em `PeriodTest`) | Valores da Toyota conferidos na DRE publicada (outros rendimentos FY23 27.739.438 €, FY24 34.746.983 €) | Pendente |
| M0.4 | Alertas das empresas reais classificados (5 verdadeiros positivos, 4 por rever; o alarme falso da Amorim foi resolvido no M0.3); `scripts/validation_report.py` escreve `docs/VALIDATION.md` | Sim | 138 testes OK | Classificação feita a partir dos números publicados (Toyota DRE/DFC, Amorim DR/DFC) | Pendente: a classificação é uma proposta |
| M0.3 | R13: diferença explicada por descobertos ou caixa restrita passa a reconciliação (memo no net debt) | Sim | 138 testes OK (4 novos em `tests/test_cash_reconciliation.py`); paridade igual | Sim: Amorim, nota 19 (p. 426), igual ao milhar nos dois anos | Pendente |
| M0.2 | Ausência ≠ zero: net debt, NWC, FCF, R12, R14, mapa da dívida; avisos "incompleto" na app, no Excel, no memo e no JSON | Sim | 133 testes OK (6 novos em `tests/test_absence.py`); app headless sem erros nas 4 amostras | Não aplicável (casos construídos a partir da Velmora) | Pendente |
