# DD Assistant — Fase 3: mais profundo, medido e visível

Lê este ficheiro inteiro antes de mexer em código. Vale junto com o `CLAUDE.md` e com as regras de trabalho e de rigor do `docs/FASE2_SPEC.md` (secções 3 e 4: incrementos pequenos, `PROGRESS.md`, quatro estados, ausência ≠ zero, proveniência, sem push sem aprovação).

## 1. Objetivo

O projeto já lê contas reais, monta as três pontes, tem 29 regras, um databook e uma demo publicada. Esta fase leva-o de "bom projeto de estudante" a "trabalho que um manager de Transaction Services reconhece como seu ofício", em três frentes:

1. **Mais profundo:** a análise passa a fazer o que uma primeira passagem de FDD (financial due diligence) faz sobre informação pública: três anos, notas às contas, materialidade, implicações para o deal.
2. **Medido:** a precisão deixa de ser uma afirmação e passa a ser um número, obtido por um teste que qualquer pessoa pode repetir.
3. **Visível:** quem abre o link (recrutador, talent acquisition, manager) percebe o valor em 30 segundos, numa página que abre de imediato, e leva um entregável em slides.

Nunca escrevas "padrão Big Four", "nível EY" ou parecido. O que podemos dizer é "segue a estrutura de um relatório de FDD" e mostrar os números medidos.

## 2. Estado verificado (10 de novembro de 2026)

Conferido no repositório público: 52 commits, 203 testes, 29 regras (R01–R29), demo em https://dd-assistant-tickmark.streamlit.app com TAP, Toyota Caetano e Corticeira Amorim (FY24–FY25). Confirma antes de começar.

O que um revisor de FDD ainda apontaria:

| Lacuna | Exemplo na demo |
|---|---|
| Só dois anos | FDD trabalha com três anos e o período mais recente; com dois anos não há tendência |
| As notas quase não são lidas | Toyota: outros rendimentos são 60,5% do EBITDA e o achado diz "sem detalhe", mas o detalhe está numa nota do relatório público |
| Sem materialidade | TAP: o primeiro red flag (R07, clientes a crescer mais do que as vendas, "High") pesa pouco numa companhia aérea; a dívida de leasing, que é a história, não é o primeiro achado |
| Achados sem consequência para o deal | Cada achado tem pergunta e documento, mas não diz se mexe no preço, no contrato ou só pede mais análise |
| Precisão não medida | `VALIDATION.md`: 27 achados classificados pelo agente, nenhum revisto por uma pessoa; nenhuma taxa de deteção |
| Sem entregável em slides | Equipas de deal e consultores trabalham em PowerPoint; só há Excel e Markdown |
| A demo adormece | No plano gratuito do Streamlit, uma app sem visitas mostra "This app has gone to sleep" até alguém carregar num botão: é o que um recrutador pode ver primeiro |
| Numa janela estreita, vi uma zona em branco ao fazer scroll na página da TAP | Confirma a 800 px de largura; pode ser só atraso de carregamento |

## 3. Bloco A — análise mais profunda

### A1. Materialidade e ordem dos achados (primeiro: barato e muda tudo)
- Um limiar de materialidade visível e editável (proposta: 5% do EBITDA reportado para itens de resultados; 1% das vendas para itens de balanço; confirma comigo).
- Cada achado passa a ter um **montante em causa em euros**, calculado pelo motor a partir das linhas que o disparam (por exemplo, R07: o excesso de clientes face ao crescimento das vendas; R04: os outros rendimentos; R19: o ganho). Quando não há montante calculável, diz "not quantifiable from the accounts".
- A severidade "High" exige que o montante passe o limiar. Abaixo dele, o achado fica "Low" com a nota "below materiality". A ordem no ecrã, no databook e no material do memo é por montante.
- Os itens "to assess" e debt-like das pontes entram na mesma lista ordenada: na TAP, os leasings têm de aparecer no topo.
- A paridade com a planilha da Duriva muda (severidades). Mantém o teste de paridade para métricas, valores e disparos; para a severidade, explica a mudança no `PROGRESS.md` e ajusta o teste com essa razão. A Velmora continua com zero achados analíticos.

### A2. Implicações para o deal
Num relatório de FDD, cada questão-chave diz o que fazer com ela. Acrescenta a cada achado e a cada item das pontes um campo **Deal implication**, atribuído por regra e editável pelo revisor:

| Categoria | Quando | Exemplo |
|---|---|---|
| Price: EBITDA | o achado muda o EBITDA sobre o qual se aplica o múltiplo | ganho de alienação, ajuste não suportado |
| Price: net debt | item debt-like ou cash-like | leasings, pensões, imposto a pagar |
| Price: working capital / peg | o achado mexe no NWC normal | stock acumulado no fecho |
| SPA protection | risco que se cobre com garantia, indemnização específica ou condição | contingência fiscal, covenant |
| Further diligence | falta informação para concluir | sem aging, sem detalhe |
| Post-deal | tema para o plano dos 100 dias | investimento adiado |

Texto sempre como "typical treatment; for the deal team and its lawyers to decide". Nunca aconselhamento jurídico nem recomendação de preço. Nova folha no databook (**Key Issues**: achado · montante · implicação · pergunta · documento · estado) e um separador na app.

### A3. Três anos e reexpressões
- Junta o relatório do ano anterior de cada empresa para ter **FY23–FY25** (a Toyota e a Amorim de 2024 já estão em `data/`; falta o relatório de 2024 da TAP).
- Quando dois relatórios dão o mesmo ano (FY24 como publicado em 2024 e como comparativo em 2025), compara linha a linha. Diferença acima da tolerância é uma **reexpressão**: nova regra R30 ("Comparatives restated"), com as duas fontes, e a política visível de usar o comparativo mais recente. Nunca misturar as duas versões em silêncio.
- Métricas, regras de tendência, gráficos e databook passam a três anos. CAGR só com os três anos presentes.

### A4. Ler as notas que resolvem achados
A maior diferença entre um rastreio automático e uma primeira passagem de FDD é ler as notas. Para as três empresas da demo, transcreve tal como impressas (folha por nota, com a página) as notas que respondem aos achados em aberto:

- detalhe de **outros rendimentos e outros gastos**;
- **empréstimos** por tipo e por maturidade; covenants divulgados;
- **locações** (passivos por maturidade, pagamentos, opções);
- **provisões e contingências**;
- **partes relacionadas** (saldos e transações);
- **segmentos** (vendas e resultado por segmento ou geografia);
- **pessoal** (número médio e custos), para o custo por colaborador.

Depois:
- cada achado ganha um estado de evidência: `open` · `explained by note N (p.X)` · `partly explained`. A explicação é uma frase com os números da nota. Exemplo esperado na Toyota: que parte dos outros rendimentos são rendas, subsídios ou incentivos do fabricante, se a nota o disser.
- Itens das notas alimentam as pontes (provisões por natureza no net debt "to assess"; leasings por maturidade).
- A request list deixa de pedir o que o relatório público já responde e passa a pedir o nível seguinte (balancete, contrato).
- Regras novas só onde uma nota dá um facto verificável: saldo com partes relacionadas acima da materialidade; contingências divulgadas sem provisão; concentração num segmento. Cada uma com teste e com zero disparos na Velmora.
- Uma nota ilegível ou ausente fica "not read", nunca inventada.

Usa subagentes em paralelo, um por empresa, para a transcrição; um subagente separado, sem acesso ao código, confere 10 valores por empresa contra o relatório.

### A5. Ponte de caixa
A secção de cash flow de um relatório de FDD: **EBITDA → fluxo de caixa livre**, por ano (EBITDA − variação de NWC − capex − impostos pagos − pagamentos de locação − juros = free cash flow, reconciliado com a DFC; a diferença não explicada aparece como linha própria). Gráfico em cascata, folha no databook, material para o memo.

### A6. Opcional, só com a minha aprovação depois do resto
- **LTM real:** a Toyota Caetano e a Amorim publicam contas semestrais. LTM jun-26 = FY25 + S1 2026 − S1 2025, com períodos compatíveis (o teste do `FASE2_SPEC`, secção 6, já define o esperado). Dados reais, não sintéticos.
- **TAP e os candidatos:** quadro de 6 indicadores (margem EBITDA, dívida líquida ajustada/EBITDA, conversão de caixa…) da TAP ao lado da Air France-KLM e da Lufthansa, tirados dos relatórios anuais, cada número com página. Só contexto: nenhuma conclusão sobre as propostas.

## 4. Bloco B — precisão medida

### B1. Benchmark de deteção por mutação
Um script (`scripts/detection_benchmark.py`) que, sobre cada conjunto de contas reais, planta **uma distorção conhecida de cada vez** e corre o motor:

- exemplos: clientes +25%; um ganho de alienação movido para outros rendimentos; 30% da dívida passada para curto prazo; stock +30%; uma linha da DFC alterada para a caixa deixar de reconciliar; D&A cortada a metade; um ajuste da gestão repetido três anos; uma linha de custo apagada (para a reading check falhar).
- esperado para cada mutação: a regra (ou reading check) que tem de disparar, escrita à mão numa tabela antes de correr.
- resultado: **deteções / mutações** (recall) e **alertas novos não esperados** por mutação. Mutações abaixo da materialidade contam à parte ("below materiality by design").
- as contas originais nunca são alteradas; cada mutação é feita em memória ou numa cópia temporária.

O resultado vai para `docs/VALIDATION.md`, para o README e para a página. Publica o número que sair, incluindo as falhas, e lista as mutações não detetadas. Não afines as regras para o benchmark sem me mostrares primeiro o que falhou.

### B2. Auditoria independente da leitura
Um subagente sem acesso ao código nem aos ficheiros transcritos recebe só o relatório de cada empresa e uma lista de 20 linhas (demonstrações e notas, anos diferentes) e devolve os valores com a página. Compara com o que o motor leu. Matriz: esperados · iguais · diferentes · ausentes. Sem tirar falhas do denominador.

### B3. A minha revisão
Gera `docs/REVIEW_SHEET.xlsx`: os achados das três empresas, cada um com evidência, fonte, classificação proposta e uma coluna vazia para a minha decisão e comentário. Só depois de eu a preencher é que o `VALIDATION.md` pode dizer "reviewed by a person". Não a preenchas por mim.

## 5. Bloco C — relatório em slides

Um **Red Flag Report** por empresa, em PowerPoint (`python-pptx`; regista a dependência nova no `PROGRESS.md`), gerado pelo motor, com versão PDF quando houver PowerPoint neste PC para exportar:

1. Capa: empresa, contas, fonte, data, "Preliminary: for an analyst to review".
2. Key issues: os 5 achados por montante, com a implicação para o deal.
3. Financial overview: três anos, 6 indicadores.
4. Quality of earnings: cascata do EBITDA.
5. Net debt: cascata, com os itens "to assess".
6. Working capital: evolução e referência para o peg.
7. Cash flow: ponte EBITDA → FCF.
8. Information requests: os 10 pedidos prioritários.
9. Scope, sources and limits.

Regras de qualidade: cada slide tem um **título que diz a conclusão** com o número ("Adjusted net debt is €2,293m, against a reported net cash position"), montado por regra a partir dos valores do motor; gráficos nativos do PowerPoint (editáveis), não imagens; fonte e página no rodapé de cada slide; a mesma paleta da app; nada de texto a transbordar (confere com capturas de cada slide). Teste: cada número dos slides existe no material do motor.

## 6. Bloco D — montra

### D1. Página estática que abre sempre
O link que vai no CV e no LinkedIn passa a ser uma página estática no **GitHub Pages** (grátis, abre em menos de um segundo, nunca adormece). A app Streamlit fica a um clique, como "interactive demo".

- Gerada por um script (`scripts/build_site.py`) a partir das saídas do motor e dos ficheiros de `docs/examples/`, para os números baterem; um teste confirma que cada número da página existe no material.
- HTML e CSS num só ficheiro por página, sem frameworks nem pedidos a terceiros além de fontes.
- **Conteúdo, por ordem:** frase de valor e quem fez → o GIF → três casos, cada um com um número grande, um gráfico em cascata (SVG) e os downloads (databook, slides, memo) → "How it works" em 5 passos → "How it is verified", com os números medidos do bloco B → limites → sobre mim e contactos → botão para a demo interativa (com a nota "may take a few seconds to wake up").
- **Uma página por empresa** com a case note, os gráficos, a tabela de key issues e os downloads.
- **Desenho:** segue a skill de frontend design se existir; tipografia com carácter (um tipo serifado para títulos e números grandes, sans para texto), navy como cor principal e uma cor de destaque, muito espaço em branco, números tabulares, tema claro e escuro, leitura perfeita a 375 px. Sem imagens de banco, sem ícones decorativos, sem gradientes de "landing page de IA".
- Metadados Open Graph e a imagem de pré-visualização, para o link ficar bem no LinkedIn e no WhatsApp.
- `docs/DEPLOY.md` ganha os passos para ativar o GitHub Pages. Não o ativo eu nem fazes push sem a minha aprovação.

### D2. App Streamlit
- CSS próprio com a mesma paleta e tipografia da página; cartões e tabelas alinhados; a zona em branco da secção 2 investigada.
- O novo separador Key issues, os três anos, o estado de evidência de cada achado, a ponte de caixa e o download dos slides.
- Verificação visual por capturas a 1440, 800 e 375 px depois de cada incremento.

### D3. Kit para candidaturas (rascunhos para eu rever; nunca publiques em meu nome)
Em `docs/portfolio/`:
- `INTERVIEW.md`: 15 perguntas prováveis de um manager de Transaction Services e de um consultor de estratégia, cada uma com uma resposta de 4 linhas e o sítio do código, teste ou folha que a sustenta. Inclui as difíceis ("foste tu que programaste?", "e se a IA errar?", "porque é que isto não é só pôr o PDF num chat?").
- `PITCH.md`: versões de 15 segundos, 30 segundos e 2 minutos, em inglês e em português.
- `LINKEDIN_POST.md`: dois rascunhos de publicação (um centrado na TAP, outro no método), em inglês, sem exageros e com os números medidos.
- `CV_BULLETS.md`: três formulações para o CV.
- `VIDEO_SCRIPT.md`: roteiro de 90 segundos para eu gravar com a minha voz.
- `ONE_PAGER.pdf`: uma página A4 do projeto, com o link e um QR code.

Tudo com os factos certos sobre mim: estágio em **International Tax and Transaction Services** na EY; licenciatura em Economia na FEP. A linha "ex-EY Transaction Services intern" que está na página publicada tem de ser confirmada comigo antes de continuar no ar.

## 7. Ordem e pontos de paragem

1. **A1 + A2** (materialidade e implicações) → para e mostra-me a TAP antes e depois.
2. **A3** (três anos) → **A4** (notas) → para e mostra-me o que cada nota resolveu.
3. **B1** (benchmark) e **B3** (folha de revisão) → para e mostra-me os números, incluindo o que falhou.
4. **C** (slides) → para e mostra-me o PDF da TAP.
5. **D1** (página) → **D2** (app) → para e mostra-me as capturas.
6. **D3** (kit), **B2** (auditoria), **A5** (ponte de caixa, se ainda não entrou nos slides).
7. **A6** só se eu pedir.

Se o tempo apertar, o mínimo que vale a pena publicar é 1 + 3 + 5.

## 8. Regras

- Todos os testes atuais continuam a passar; cada incremento traz os seus. Zero achados analíticos na Velmora.
- Nenhum número na app, nos slides, na página ou no kit que não venha do motor, de uma nota transcrita com página ou do benchmark.
- Os memos guardados são reescritos pelo agente (sem API) quando o material mudar, e voltam a passar no verificador.
- Sem chamadas pagas. Sem push, sem publicar, sem ativar o Pages sem a minha aprovação.
- Um commit local por incremento; `PROGRESS.md` e `GAPS.md` atualizados.
- No fim de cada bloco: o que mudou, o benefício para um analista, testes corridos, falhas, comando para eu ver, e um exercício de verificação de 5 minutos para mim, com a explicação da decisão financeira em 3 a 5 linhas.

## 9. Decisões que são minhas (pergunta no início, de uma vez)

1. Limiar de materialidade por defeito (proposta na A1).
2. A linha "Built by" e a descrição do estágio.
3. O nome público: manter "DD Assistant" ou passar a "Tickmark" (o endereço da demo já o usa; em auditoria, um tick mark é a marca de um número conferido com a fonte).

## Mensagem para colar no Claude Code

```
Lê integralmente docs/FASE3_SPEC.md e usa-o como especificação, junto com o CLAUDE.md e as regras de trabalho do docs/FASE2_SPEC.md. Confirma o estado da secção 2, faz-me as três perguntas da secção 9 de uma vez e começa pelo bloco A1 + A2 enquanto eu respondo. Segue a ordem e os pontos de paragem da secção 7. Usa subagentes para as transcrições e para as verificações independentes. Fala comigo em português. Não faças push, não publiques e não faças chamadas pagas sem a minha aprovação.
```
