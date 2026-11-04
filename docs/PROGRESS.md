# Fase 2 — progresso

Ficheiro de retoma. Especificação: `docs/FASE2_SPEC.md`. Atualizado no fim de cada incremento.

**Estados:** construído · testado automaticamente · conferido contra a fonte · revisto pelo Bernardo. Um estado só aparece quando aconteceu.

## Agora

- **Módulo:** M0, correções de confiança.
- **Feito:** M0.1 (o verificador do memo liga cada número ao ano citado); M0.2 (ausência ≠ zero nas pontes e nas regras de consistência).
- **Próximo passo:** M0.3, R13 com caixa restrita e descobertos bancários (Amorim).
- **Comando para retomar:** `python -m unittest -v` (tem de dar 133 testes OK); depois ler a secção "Próximo passo" acima.

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

## Incrementos

| # | Incremento | Construído | Testado | Conferido contra a fonte | Revisto |
|---|---|---|---|---|---|
| M0.1 | `memo_check` liga cada número ao ano citado | Sim | 127 testes OK (3 novos em `PeriodTest`) | Valores da Toyota conferidos na DRE publicada (outros rendimentos FY23 27.739.438 €, FY24 34.746.983 €) | Pendente |
| M0.2 | Ausência ≠ zero: net debt, NWC, FCF, R12, R14, mapa da dívida; avisos "incompleto" na app, no Excel, no memo e no JSON | Sim | 133 testes OK (6 novos em `tests/test_absence.py`); app headless sem erros nas 4 amostras | Não aplicável (casos construídos a partir da Velmora) | Pendente |
