# DD Assistant — melhorar a demo online (o que um recrutador vê)

Lê este ficheiro inteiro antes de mexer em código. Vale junto com o `CLAUDE.md`, o `docs/DEMO_ONLINE_SPEC.md` e as regras de rigor do `docs/FASE2_SPEC.md`.

## 1. Objetivo

Quem abre https://dd-assistant-tickmark.streamlit.app (um recrutador de Transactions, um consultor de estratégia, um professor) decide em 60 segundos se o projeto é sério. A demo tem de ser **correta, bonita, didática e rápida de perceber**, para alguém de M&A e também para alguém que não é especialista.

Revisão feita a 9 de novembro de 2026 na versão publicada, em 1440×900 e em 375×812. Confirma cada ponto na app antes de o corrigir.

## 2. Primeiro: correções de credibilidade

Corrige estas antes de qualquer melhoria visual, cada uma com um teste.

1. **Normativo errado na TAP.** A barra lateral diz "Framework named in the memo: SNC". As contas consolidadas da TAP são preparadas em IFRS adotadas na UE (confirma na nota de bases de preparação do relatório de 2025). Regra: contas **consolidadas** usam IFRS por defeito (Regulamento IAS da UE para cotadas e prática dos grupos com dívida cotada), e o SNC fica para contas individuais e empresas que o declarem. Confirma também a Toyota Caetano e a Amorim. Se o memo guardado de algum caso disser SNC por engano, reescreve-o e volta a passá-lo no verificador.
2. **Cor do working capital da TAP.** O cartão "Net working capital −€598m" aparece a vermelho ("R07, R28 · High"), mas o working capital negativo é o modelo normal de uma companhia aérea (bilhetes vendidos antes do voo). A cor de cada cartão tem de vir só dos achados dessa métrica e, quando o setor o explica, mostrar uma nota curta ("Negative working capital is normal for airlines: passengers pay before they fly"). Revê também se o R07 (receivables) faz sentido como primeiro achado da TAP. Não mudes limites sem razão escrita (regra do `CLAUDE.md`).
3. **Unidades contraditórias no cabeçalho.** "EUR millions" e "converted to EUR thousands" aparecem na mesma linha. O cabeçalho mostra só a unidade em que os números aparecem.
4. **Texto técnico no topo.** "Excel — dictionary mapping, figures read from the cells…" passa para o separador Data room. O cabeçalho fica com: nome curto da empresa (nome legal em letra pequena), contas e ano, fonte (relatório e páginas).

## 3. Página inicial

Hoje é limpa, mas pequena, com muito espaço vazio, e não mostra o produto. Muda para:

1. **Topo:** "DD Assistant" + uma frase de valor ("A first-pass financial due diligence on published accounts. Every figure traced to its source.") + uma linha de quem fez ("Built by Bernardo Espinola, Economics, University of Porto · ex-EY Transaction Services intern"). Confirma o texto comigo antes de publicar.
2. **Um esquema simples do processo**, em 5 passos com ícones: Read the accounts → Check the reading → Flag what matters → Build the bridges → Export to Excel.
3. **Três cartões de empresa** com: logótipo ou inicial (sem usar marcas registadas se houver dúvida: usa a inicial num círculo), **um número grande** (TAP: "€2,293m adjusted net debt vs −€43m reported"; Toyota: "60.5% of EBITDA is other income"; Amorim: "Cash conversion 155% of EBITDA"), uma frase e o botão "Open the analysis". Todos os números vêm do motor ou do memo guardado.
4. **"What you get"**: uma imagem do databook em Excel (`docs/images/`) com 4 linhas sobre o que tem dentro (QoE, Net debt, NWC, Issues & requests, fórmulas vivas).
5. **"How it is verified"** em três números: testes automáticos, totais publicados reconstruídos, números do memo verificados.
6. **Rodapé** como está (limites, GitHub, LinkedIn).

## 4. Página de cada empresa

1. **"Key insights" no topo**, antes dos cartões: os três pontos da `case_note.md` (o número, porque importa num deal, a pergunta à gestão), em três cartões. É a história que conto numa entrevista e tem de ser a primeira coisa que se vê.
2. **Gráficos em cascata (waterfall)** no Deal view e um resumo no Overview:
   - EBITDA: reportado → ajustes → diligence-adjusted. Na TAP, também reportado → sem IFRS 16 (pagamentos de leasing).
   - Net debt: empréstimos − caixa → + leasings → + pensões → + outros debt-like → ajustado. Na TAP, é o gráfico principal.
   - Working capital por ano, com a média como linha de referência para o peg.
   Usa Plotly ou Altair (o que for mais leve e já for compatível), com as cores da app, os valores escritos nas barras e a unidade no título. Cada valor vem do motor; nenhum é recalculado no gráfico.
3. **"Guided tour" de 60 segundos**: um botão "Take the 60-second tour" que leva por 5 passos (reading check → key insight → bridge → um red flag com a fonte → download do Excel), com uma frase em cada passo. Sem bibliotecas externas pesadas; pode ser um passo-a-passo com botões "Next".
4. **Glossário ao passar o rato** nos termos: QoE, diligence-adjusted EBITDA, net debt, debt-like item, IFRS 16, NWC, peg, locked box, completion accounts, red flag. Uma frase simples cada. Para o consultor de estratégia que não é de Transactions.
5. **Fonte visível em cada número importante**: um pequeno "p.152" ao lado, que abre o Data room nessa linha.
6. **Barra lateral recolhida por defeito no modo demo**, com um bloco "About this demo" (3 linhas) em vez das opções desligadas. As opções avançadas ficam num expander.
7. **Databook em destaque**: o botão do Excel com a descrição do que tem dentro e o tamanho do ficheiro.

## 5. Aparência

- Cores próprias e consistentes (navy como cor principal, verde/âmbar/vermelho só para estado) em `.streamlit/config.toml`; o mesmo esquema nos gráficos e no Excel.
- Esconde o que puderes da barra do Streamlit em modo demo (`client.toolbarMode = "minimal"`, sem menu). O que o Streamlit Community Cloud não deixar esconder, deixa e diz-me.
- Título da página e ícone próprios.
- Largura máxima confortável em ecrãs grandes; nada de colunas apertadas a 1440 px.
- Telemóvel (375 px): cartões em coluna, gráficos legíveis, sem scroll horizontal.
- Acessibilidade: contraste suficiente, estado nunca só pela cor (texto "High", "Medium").

## 6. GitHub

- Atualiza as imagens do README depois das mudanças (Playwright, 1440 px), com uma imagem da página inicial, uma do waterfall de net debt da TAP e uma do Excel.
- Cria uma imagem de "social preview" (1280×640) para o repositório, com o nome, a frase de valor e um número, e diz-me onde a carregar (Settings → Social preview).

## 7. Regras

- Nenhum número novo que não venha do motor ou do memo guardado. Os memos continuam a passar no verificador.
- Modo demo sem upload, sem API, sem custos.
- Todos os testes continuam a passar; acrescenta testes para as correções da secção 2 e para o modo demo (insights, gráficos com os valores do motor, glossário).
- **Verificação visual obrigatória:** depois de cada incremento, corre a app localmente com `DD_DEMO=1`, tira capturas com o Playwright a 1440×900 e 375×812 da página inicial e das três empresas, e olha para elas. Corrige o que estiver desalinhado, cortado ou ilegível antes de seguir.
- Commit local por incremento; atualiza `docs/PROGRESS.md`. **Não faças push sem a minha aprovação** (o push publica o site).

## 8. Ordem

1. Correções da secção 2.
2. Key insights e waterfalls (a maior melhoria por hora de trabalho).
3. Página inicial.
4. Barra lateral, glossário, fontes visíveis, aparência.
5. Guided tour.
6. Imagens do README e social preview.

## 9. No fim

Mostra-me, em português: o que mudou, com as capturas de antes e depois da página inicial e da TAP; os testes corridos; o que o Streamlit não deixou mudar; e o comando para ver no meu PC (`$env:DD_DEMO=1; streamlit run app.py`). Espera pela minha aprovação para o push.

## Mensagem para colar no Claude Code

```
Lê integralmente docs/DEMO_UX_SPEC.md e usa-o como especificação, junto com o CLAUDE.md. Começa por confirmar na app os 4 problemas da secção 2 e corrige-os com testes. Depois segue a ordem da secção 8, com verificação visual por capturas a 1440 e 375 px depois de cada incremento e um commit local por incremento. Fala comigo em português. Não faças push sem a minha aprovação.
```
