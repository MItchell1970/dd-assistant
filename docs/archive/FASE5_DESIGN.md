# Fase 5 — desenho do produto final (para o Opus implementar as fases C e D)

Especificação, não código. Vale o que está em `docs/archive/FASE4_SPEC.md` (princípios, paleta, "Como trabalhar"); este ficheiro decide o que lá estava em aberto. Padrão: relatório de Financial Due Diligence de Big Four (conclusão primeiro, número, fonte). Sem Go/No-Go. Todos os números e títulos vêm do motor (`deal_layer.build`, `charts`) e passam pelo memo-checker. Textos do produto em inglês.

## 1. Ecrãs e ordem das secções

**App Streamlit = ferramenta (Fase C).** Abre na TAP. Cabeçalho fixo: empresa (seletor) · FY · unidade · modo (outside-in / data room) · botão Download. Quatro separadores:

| Separador | Secções, por ordem | Objetivo numa linha |
|---|---|---|
| **Summary** | 1. Faixa de estado · 2. Quatro KPIs · 3. Chips de área · 4. Top 5 deal issues | Dizer em 5 segundos quanto há em aberto e onde. |
| **Findings** | 1. Filtros (severidade, área, estado da evidência) · 2. Cartões de achado · 3. Decisão do revisor | Rever um achado de cada vez, com a evidência à frente. |
| **Impact** | 1. Ponte de net debt · 2. Valuation impact com slider 4x–12x · 3. "Shown, not counted" · 4. Ponte de caixa | Ligar os achados ao preço, sem fazer valuation. |
| **Evidence** | 1. Mapa de cobertura · 2. Open items em 3 grupos · 3. Action items por momento · 4. Encaminhamentos · 5. Downloads | Mostrar o que falta pedir, a quem e quando. |

- **Faixa de estado** (substitui o veredicto da referência): `54 / 100 · Finding intensity, not a recommendation` + três contagens do motor: questões em aberto, ações "Before signing", `22 of 30 rules run`. A fórmula abre num popover de uma linha.
- **KPIs:** Adjusted net debt · Leverage (x EBITDA) · Free cash flow after leases · Risk score. Cada um com a fonte por baixo (página ou célula).
- **Chips de área** (5): forma da pior severidade + nome + n.º de questões. Clicar abre Findings já filtrado.
- **Top 5:** uma linha por issue: n.º · título · montante · proteção/próximo passo · momento. Clicar abre o cartão.
- **Action items:** quatro colunas (Before signing · SPA · Completion accounts · Post-closing); a 375 px passam a acordeão.

**Site = montra (Fase D).** Página inicial: 1. Hero (frase de valor, botão "Open the tool") · 2. Três cartões de empresa (score, um número, um action title) · 3. Verificação em 4 números · 4. Limites numa linha · 5. Rodapé. Página de empresa: 1. Faixa de estado · 2. Top 3 deal issues · 3. Um gráfico (ponte de net debt) · 4. Mapa de cobertura · 5. Botão para a app. Mais nada.

## 2. Hierarquia visual

| Tempo | O que se vê | Como |
|---|---|---|
| **5 s** | O score, o maior número e a frase que o explica | Faixa de estado no topo; action title do gráfico em serif 24 px; nada acima deles. |
| **30 s** | Onde estão os problemas e os cinco maiores | Chips de área e Top 5 sem scroll a 1440 px. |
| **2 min** | Um achado até à fonte, e o efeito no preço | Um cartão aberto (evidência citada) e o separador Impact. |

Regra: cada bloco = título + número + no máximo uma frase. O resto fica em `expander`.

## 3. Sistema visual

- **Cor (só estas):** fundo `#0d1117`, cartão `#161b22`, texto `#e6edf3`, secundário `#8b949e`, linhas `#30363d`; vermelho `#f85149` = pior para o comprador; verde `#3fb950` = melhor / bate certo; cinzento `#8b949e` = totais, neutro **e itens standard do bridge** (leasings). O vermelho fica reservado aos ajustes de diligence. Sem cobre nem navy na app.
- **Severidade:** forma + cor: ▲ High (vermelho) · ● Medium (cinzento-claro) · ○ Low (cinzento). Nunca só cor.
- **Tipografia:** Inter para tudo; Source Serif 4 só nos action titles. Tamanhos: 32 (número de KPI) · 24 (action title) · 16 (corpo) · 13 (rótulos e fontes). Números com `tabular-nums`, alinhados à direita. Negativos com "−", nunca parênteses.
- **Espaço:** grelha de 8 px; padding dos cartões 16; 24 entre blocos; 48 entre secções; largura máxima 1120 px; raio 8.
- **Componentes:**
  - *KPI:* rótulo 13 · número 32 · fonte 13 cinzenta. Sem ícones nem setas.
  - *Chip de área:* forma + nome + contagem; contorno 1 px; preenchido quando ativo.
  - *Cartão de achado:* (fechado) forma · ID · título · montante à direita · estado da evidência. (aberto) uma frase em linguagem simples · evidência citada com fonte (`Financial position!C40`, `note 19, p.207`) · pergunta · documento a pedir · proteção e momento · Accepted / Dismissed / Pending + comentário.
  - *Gráfico de ponte:* o gerador da Fase A (`charts.py`), máximo 7 colunas, action title por cima, subtítulo técnico em 13.
  - *Tabela:* sem linhas verticais, cabeçalho 13 cinzento, linha de 40 px, máximo 6 colunas; a 375 px passa a lista de cartões.

## 4. Os três visuais "assinatura" (LinkedIn, 1200×1200, fundo escuro, rodapé com a fonte)

| Visual | O que mostra | Action title para a TAP (gerado pelo motor) |
|---|---|---|
| **1. Net debt bridge em duas camadas** | Reported net debt → itens standard (cinzento) → ajustes de diligence (vermelho) → adjusted net debt | "Leases, a standard item, explain €2,158m of TAP's €2,293m adjusted net debt; diligence adds €177m" |
| **2. Mapa de cobertura** | Grelha de 30 regras: ✓ corrida, ○ bloqueada, com o documento que desbloqueia | "22 of 30 rules run on published accounts; the other 8 name the document that unlocks them" |
| **3. Cartão de deal issue** | Um achado: montante, evidência citada, pergunta, proteção, momento | "Receivables grew €63m ahead of revenue: completion accounts, not price" (R07) |

O visual 1 substitui o valuation impact bridge como assinatura: depois da revisão, a ponte de impacto da TAP tem só duas barras; a história está na separação standard / diligence.

## 5. O que remover

- **Da app:** "How it works", verificação, limites, glossário longo, visita de 60 segundos, a página inicial com cartões, os key insights escritos à mão (o Top 5 substitui-os), os separadores Rulebook e Sector (passam a `expander` dentro do cartão de achado). Fica um link discreto para o site.
- **Do site:** as cascatas de EBITDA, caixa e valuation, a lista de 8 issues, open items em detalhe, encaminhamentos, "Measured / Not measured", os 5 passos. Ficam na app.
- **Regra de não repetição:** o site mostra conclusões (score, top 3, um gráfico); a app mostra evidência. Nenhuma tabela aparece nos dois.
- **Texto:** nenhum parágrafo acima de duas linhas a 1440 px; a fórmula do score e os avisos "illustrative" passam a uma linha em 13.

## 6. Critérios de aceitação (capturas por `scripts/demo_review.py`, a 1440 e 375 px, TAP, Toyota e Amorim)

1. Summary a 1440×900: faixa de estado, 4 KPIs, 5 chips e o Top 5 visíveis sem scroll.
2. A 375 px: nenhum scroll horizontal na página; o score e o primeiro KPI no primeiro ecrã; tabelas em cartões.
3. Só as cores da secção 3 (teste: as cores do CSS e dos SVG pertencem à lista).
4. Cada severidade aparece com forma e cor; os leasings estão a cinzento na ponte de net debt.
5. Cada cartão de achado aberto mostra uma fonte (célula, página ou nota) e um documento a pedir.
6. Mover o slider de 8x para 10x muda o total do valuation impact na Duriva e não muda na TAP (sem ajustes de EBITDA); na TAP a anotação diz que os leasings não contam.
7. "Go", "No-Go", "recommend" e "should buy" não aparecem em nenhum ecrã (teste de texto).
8. Todos os números visíveis passam no memo-checker (como `tests/test_site.py`); os três action titles da secção 4 são gerados, não escritos à mão.
9. O site não tem nenhuma tabela que exista na app; a página de empresa cabe em 3 ecrãs a 1440 px.
10. Suite completa OK; a paridade e a Velmora (0 alertas) não mudam.

**Já no motor (não refazer):** a coluna "Protection or next step", o estado "not applicable –" do mapa de cobertura (terceiro símbolo da grelha) e o tipo "Working capital item" (`docs/archive/FABLE_REVIEW.md`, linhas 5 a 8).
