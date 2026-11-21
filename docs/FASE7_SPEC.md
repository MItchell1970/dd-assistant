# Fase 7: três peças sobre o mesmo motor

**Princípio.** O motor (leitura → reading checks → métricas → regras → deal view → deal layer) mantém o contrato. A e B são entradas novas e dão o mesmo `Analysis`; C acrescenta um estado por cima. A ordem é A, B, C, com um commit por peça e uma paragem para revisão no fim de cada uma. A paridade com a planilha e os zero alertas da Velmora não mudam. Os testes não usam a rede nem a Claude API.

## A. Qualquer cotada da UE

**Objetivo:** escolher uma cotada por nome ou LEI e analisá-la a partir do ESEF público, sem custo de API.

**Passos**
1. **Pesquisa** (`registry.py`): o nome dá o LEI pela API pública da GLEIF; o LEI dá os relatórios anuais no filings.xbrl.org, o mais recente primeiro, com país, ano e tamanho.
2. **Descarga** com autorização para `output/esef_cache/`, fora do git; o SHA-256 vai para o Source Register.
3. **Proteção do ZIP**, que fecha a lacuna aberta: limites ao tamanho descompactado (300 MB) e ao rácio de compressão, nenhum caminho com `..`. Acima disso, recusa com mensagem.
4. **Leitura** pelo `esef.py` atual e o `pipeline`. Outra moeda é recusada, como hoje.
5. **Aviso de qualidade** (`esef_quality.py`), em três níveis: *Complete*; *Notes missing: …* (faltam os text blocks de borrowings, provisions, leases, related parties, other income ou segments); *Reading check failed, do not rely* (um subtotal não fecha ou há etiquetas suspeitas, como na Toyota FY25). Aparece na app, no databook e no material do memo.
6. **Entrada:** "Find a listed company" na app local; `--esef "<nome>"` ou `--lei <LEI>` na linha de comandos.

**Ficheiros:** `dd_assistant/registry.py`, `esef_quality.py`; alterações em `esef.py`, `pipeline.py`, `__main__.py` e `app.py`; `tests/test_registry.py`, `tests/test_esef_quality.py`, respostas gravadas em `tests/fixtures/`.

**Testes:** pesquisa e descarga com respostas gravadas; um ZIP-bomba sintético recusado; um pacote sem notas dá *Notes missing* e um com o subtotal trocado dá *Reading check failed*; o pacote de `test_esef.py` dá os números de hoje.

**Aceitação**
1. Os testes passam sem rede e sem chamadas à API.
2. Cinco cotadas de cinco países (PT, ES, FR, DE, IT), pesquisadas pelo nome, chegam à análise ou param com um aviso que diz porquê. O resultado fica em `docs/examples/esef_coverage.md`.
3. A EDP FY2025 continua a reconstruir o resultado operacional ao milhar de euros.

## B. Data room desarrumado (Duriva, fictício)

**Objetivo:** mostrar o agente a fazer o trabalho que num deal consome horas (mapear um balancete e o proof of cash), com a confiança de cada linha e o tempo medido.

**Dados.** `scripts/duriva_messy.py` gera `data/Duriva_messy_data_room/` a partir dos números atuais da Duriva, por isso os anuais têm de bater. Cada ficheiro e cada folha dizem "FICTITIOUS, synthetic test data".
- Balancetes de 2023 a 2025 com plano de contas próprio: códigos fora do SNC e descrições abreviadas ("Forn. c/c").
- 36 meses de exportações do ERP em formatos misturados: CSV com `;` e com `,`, cabeçalhos em linhas diferentes, datas `31.01.2024` e `jan-24`, valores `1.234,56` e `(1,234.56)`, uma conta renomeada a meio.
- Extratos de dois bancos, em CSV e num PDF de texto.
- Três distorções plantadas: receita sem recebimento, uma transferência entre bancos contada duas vezes e um saldo de fornecedores que não bate. O gabarito fica fora do projeto.

**Passos**
1. **`ledger.py`:** normaliza os formatos, junta os meses e liga a conta renomeada. Cada saldo mensal guarda o ficheiro e a célula.
2. **`mapping.py`:** liga cada conta a uma linha do template pela descrição (dicionário de `extract.py`), pelo código quando parece SNC e pelo comportamento do saldo. Cada linha tem confiança High, Medium ou Low e a razão. As Low vão ao utilizador pela skill, e a decisão fica registada. Uma reading check nova compara os totais mapeados com as demonstrações anuais.
3. **`proof_of_cash.py`:** em cada mês, saldo inicial + recebimentos − pagamentos = saldo final do extrato. Compara também a caixa do razão com o extrato e os recebimentos com receita + IVA − variação de clientes. Acima da materialidade, a diferença vira achado com mês, montante e fonte.
4. **Dados mensais:** dão o peg com 12 a 24 meses e o LTM, duas lacunas abertas.
5. **Databook:** folhas novas "Mapping" e "Proof of Cash", com fórmulas e controlo no Checks; a "Monthly & LTM" passa a ter dados.
6. **Tempo** (`docs/examples/duriva-messy/timing.md`): o manual é estimado por tarefa, com a hipótese escrita e fixada antes da corrida; o do agente é o relógio do pipeline mais a revisão humana cronometrada. Aparecem lado a lado, nunca só o rácio.

**Ficheiros:** `dd_assistant/ledger.py`, `mapping.py`, `proof_of_cash.py`, `scripts/duriva_messy.py`, folhas em `databook.py`, um passo na skill; `tests/test_ledger.py`, `test_mapping.py`, `test_proof_of_cash.py`.

**Testes:** os anuais mapeados iguais ao template da Duriva, ao euro; um caso por formato misturado; a conta renomeada junta; cada distorção apanhada; uma Velmora desarrumada, gerada da mesma forma, sem diferenças; nenhuma conta sem mapeamento ou decisão.

**Aceitação**
1. Paridade ao euro nos três anos e pelo menos 90% das contas com confiança High.
2. As 3 distorções detetadas; 0 na Velmora.
3. O databook recalculado pelo Excel igual ao Python, também nas folhas novas.
4. O tempo manual e o do agente publicados com as hipóteses, e "fictitious" visível em tudo.

## C. Diligence viva

**Objetivo:** cada resposta a um pedido muda a evidência de um achado, e o Diligence Gap mostra a evolução.

**Passos**
1. **`diligence_log.py`:** cada caso tem um `diligence_log.json` com eventos: pedido (id de `prioritised_requests`), estado (`requested → received → answered → closed`), data, documento recebido e achados ligados.
2. **Efeito da resposta, decidido pelo revisor:** *partly explained* (0,75), *explained* (0,5), *resolved* (sai do score e fica em Findings com a razão) ou *confirmed* (fica a 1 e passa a item de preço ou de SPA). A fórmula do score não muda; muda só o fator de evidência.
3. **Série temporal:** cada evento recalcula o score. A Duriva está no teto (33 pontos dão 100), por isso a série mostra também os pontos: o score só desce de 100 quando os pontos ficam abaixo de 30.
4. **Sobre A e B:** em A, os pedidos são notas e perguntas ao IR; em B, documentos do data room.
5. **Onde aparece:** o estado e o gráfico da evolução na Evidence da app; colunas de estado e uma folha "Diligence log" no databook; o estado atual no material do memo, para o verificador.
6. **Demo:** `docs/examples/duriva-live/`, três rondas de respostas fictícias e rotuladas: aging e contrato do cliente principal; faturas dos ajustes; mapa da dívida assinado.

**Ficheiros:** `dd_assistant/diligence_log.py`, `scripts/duriva_live.py`; alterações em `deal_layer.py`, `tool.py`, `app.py` e `databook.py`; `tests/test_diligence_log.py`.

**Testes:** transições inválidas recusadas (`closed → requested`, `answered` sem documento); um evento sem achado ligado não mexe no score; o score de cada ronda igual à fórmula à mão; o registo vazio dá o score de hoje; a request list exportada mostra o estado.

**Aceitação**
1. A evolução da Duriva em três rondas, com pontos e score por data, reproduzível a partir do JSON.
2. Cada mudança do score ligada a um pedido, a um documento e a uma decisão do revisor.
3. Com o registo vazio, todos os números atuais iguais.
4. Funciona num caso de A e no data room de B, com um teste para cada.

## Regras comuns

Suite completa antes e depois de cada peça. Descargas e chamadas à API só com autorização do Bernardo. O que é fictício diz que é, e o gabarito nunca entra no projeto. O agente aponta o que investigar e não faz recomendações de investimento.
