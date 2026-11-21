# DD Assistant — Fase 4 (especificação do Bernardo, 16 de novembro de 2026)

Executar por fases (A→D). No fim de CADA fase: commit local, capturas, resumo de 5 linhas e PARAR à espera de aprovação. Sem push sem aprovação. Não mexer no motor de regras salvo onde a fase o pede.

## Princípios (não negociáveis)
- O motor calcula; a IA só redige. Nenhum número novo sem fórmula e fonte.
- Nada de veredicto Go/No-Go nem recomendação de investimento.
- Inspiração: relatório de exemplo do dd-agents (zoharbabin.com/due-diligence-agents/sample-report). Usar a estrutura, não copiar código nem texto.
- Menos texto: cada bloco = título + número + no máximo 1 frase. Detalhe em expander.

## Paleta única (site, Streamlit, gráficos, Excel, slides)
- Fundo #0d1117, cartões #161b22, texto #e6edf3, secundário #8b949e, linhas #30363d.
- VERMELHO #f85149 = pior para o comprador. VERDE #3fb950 = melhor para o comprador / bate certo. CINZENTO #8b949e = totais e neutro. Mais nenhuma cor.
- Severidade com forma + cor: ▲ alta (vermelho), ● média (cinzento-claro), ○ baixa (cinzento).

## Fase A — Gráficos (um gerador único usado no site, Streamlit, slides)
- Cascata vertical padrão de banca. Totais: colunas cheias desde a base, cinzento-claro. Itens: cor por EFEITO PARA O COMPRADOR, não pelo sinal aritmético: na net debt bridge, o que aumenta a dívida é vermelho e o que reduz é verde; na ponte EBITDA→FCF, o que reduz o caixa é vermelho e o que aumenta é verde.
- Barras largas (~60% do espaço por coluna), cantos ligeiramente arredondados.
- Altura mínima visível de 6 px; se um item for < 1% do maior total, agrupa em "Outros" com o detalhe no tooltip/aria-label.
- Conectores: 1 px tracejado #30363d, SÓ no espaço entre colunas adjacentes, ao nível do topo acumulado. Nunca atravessam barras nem texto.
- Valores por cima (ou por baixo, se negativa) a negrito, com sinal nos itens; rótulos curtos por baixo, 2 linhas no máximo.
- Linha de base só se houver negativos. Sem grelha, sem eixo numérico.
- Nota de arredondamento quando aplicável.
- Mesmo estilo em Plotly no Streamlit (ou o mesmo SVG embebido).
- Capturas: TAP, Toyota, Amorim (site 1440 e 375 px; Streamlit 1440 px).

### Gráficos que contam uma história (padrão de consultoria)
- Cada gráfico tem um "action title" gerado por regra a partir dos números do motor: uma frase curta que diz a conclusão, com o número principal. Ex. TAP: "Os leasings de aviões levam a net debt de −€43m para €2.293m". Ex. FCF: "Depois dos leasings, o free cash flow passa a −€272m". Por baixo, em pequeno e cinzento, o subtítulo técnico ("Net debt bridge, FY25, €m").
- Destaque: o maior item do gráfico em cor plena; os restantes itens na mesma cor a 45% de opacidade. Totais em cinzento-claro.
- Uma anotação junto ao total final com a perspetiva mais útil (ex.: "3,16x EBITDA", "FCF/EBITDA −37%"), calculada pelo motor.
- No máximo 7 colunas; o resto agrupa em "Outros".
- O título e a anotação vêm sempre de números do motor e passam pelo memo-checker. Nada escrito à mão.
- Teste: alguém que veja o gráfico 5 segundos tem de conseguir dizer o número principal e o porquê.

## Decisões do Bernardo sobre a Fase A
- "Cash conversion 76.6%" aprovado como anotação da ponte de caixa.
- Telemóvel: o número de destaque e a anotação veem-se sem arrastar (anotação por baixo do título em ecrãs estreitos).
- App clara até à fase C e slides com fundo branco: aprovados.

## Fase B — Camada de deal (motor determinístico + testes)
1. Valuation impact bridge: impacto dos achados = (ajustes de diligência ao EBITDA × múltiplo) + ajustes à net debt (debt-like/cash-like) + ajuste de NWC vs peg, quando calculado. Mostrar a 3 múltiplos ilustrativos (6x, 8x, 10x), rotulados "ilustrativo, não é valuation". Cada componente ligado ao achado e à fonte. Evitar dupla contagem: um achado entra em EBITDA OU em net debt, nunca nos dois; testar isto.
2. Top 5 deal issues: ordenados por impacto em €; cada um com uma linha "Proteção típica" (ajuste de preço / debt-like no SPA / indemnity / escrow / completion accounts / pedir mais informação), escolhida por regra a partir da implicação de deal que o motor já tem.
3. Diligence risk score 0–100: fórmula simples e visível no ecrã (ex.: soma de pesos por relevância × materialidade, normalizada, com teto), com a decomposição por área. Rótulo: "Intensidade dos achados, não recomendação". Testes: empresa limpa tem score baixo; casos plantados têm score alto.
4. Áreas: Quality of earnings, Net debt, Working capital, Cash flow, Tax. Achados das notas que pertencem a outro workstream (litígios, garantias, pensões, ambiente) ganham etiqueta "Encaminhar: Legal / HR / Tax / Regulatory" com a pergunta. Não criar análises jurídicas.
5. Open items: contar e agrupar em "Pedir à empresa", "Confirmar com auditor", "Fora do âmbito financeiro".
6. Action items por momento: Antes do signing / SPA / Completion accounts / Pós-closing.
7. Mapa de cobertura: para cada empresa, regras corridas e regras bloqueadas por falta de dados, com o documento que desbloqueia cada uma. Cada regra bloqueada gera um pedido na request list (sem duplicar). Mostrar como contagem ("X de Y regras corridas") e grelha (corrida ✓ / bloqueada ○ + documento a pedir). Uma linha de explicação: "Contas publicadas = modo outside-in (antes do data room); Duriva = modo data room (dados fictícios)." Testes: a Duriva corre mais regras que as empresas reais; cada regra bloqueada tem um pedido.
Atualizar o databook (folhas: Valuation impact, Top issues, Open items) e o memo-checker para os números novos.

## Fase C — Streamlit = ferramenta
- Tema escuro com a paleta. Abre direto na TAP; seletor de empresa no topo.
- Navegação: Resumo / Áreas / Impacto / Evidência.
- Resumo: 4 KPIs (adjusted net debt, leverage, FCF, risk score), chips por área (severidade + nº de achados, clicáveis), top 5 deal issues.
- Áreas: filtro por severidade e área; cartões de achado com severidade, fonte (documento/página/célula), cálculo, confiança, pergunta e documento a pedir.
- Estado do revisor (aceite/descartado/pendente) + comentário, na sessão. A request list exporta só os aceites.
- Impacto: valuation impact bridge, com slider de múltiplo (4x–12x) que atualiza o gráfico.
- Evidência: open items e downloads.
- Remove "How it works", verificação e limites; link discreto para o site.

## Fase D — Site = montra
- Hero: frase de valor + 1 número por empresa + botão "Experimentar a ferramenta".
- Por empresa: risk score, top 3 deal issues e 1 gráfico (o mais revelador).
- Verificação em 4 números e limites numa linha. Corta o resto do texto.
- Nada que esteja no Streamlit em detalhe.
- README e PROGRESS/GAPS atualizados no fim.

## Como trabalhar
- Começar por docs/PROGRESS.md; abrir só os ficheiros da fase.
- Implementar cada fase completa de uma vez.
- Testes: os da fase; suite completa 1x antes de cada commit.
- Capturas só no fim de cada fase.
- Sem subagentes. Respostas curtas, em português.
