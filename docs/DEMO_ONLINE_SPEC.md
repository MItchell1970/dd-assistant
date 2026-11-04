# DD Assistant — demo online com empresas portuguesas reais

Lê este ficheiro inteiro antes de mexer em código. Vale junto com o `CLAUDE.md` e o `docs/FASE2_SPEC.md` (regras de rigor, rastreabilidade, ausência ≠ zero, quatro estados).

## 1. Objetivo

Uma versão pública e gratuita da app, para mostrar o projeto a recrutadores, professores e no LinkedIn. Quem abre o link vê, em minutos, o que o agente faz com as contas publicadas de três empresas portuguesas conhecidas, e descarrega o databook em Excel.

É uma demonstração de um trabalho preliminar, não um produto final. Tudo o que o visitante vê vem de contas publicadas e do motor, com a fonte à vista.

Regras desta demo:
- **Só empresas reais** e só contas publicadas. A Duriva e a Velmora continuam no projeto para os testes, mas não aparecem na demo.
- **Zero custos:** nenhuma chamada à Claude API no servidor, nenhuma chave configurada. O memo de cada empresa é escrito antes, neste computador, pelo agente (sem API), passa no verificador e fica guardado no repositório.
- **Sem upload:** o visitante não carrega ficheiros. Isto evita custos e evita que alguém envie documentos de clientes para um site público.
- **Sem opinião de investimento** nem preço sugerido, também nas empresas reais.

## 2. As três empresas

| Empresa | Porque é boa para conversar numa entrevista |
|---|---|
| **TAP Air Portugal** | Privatização em curso (propostas vinculativas da Air France-KLM e da Lufthansa; o Governo prorrogou o prazo até ao fim de 2026). É uma operação de M&A real e atual. Nas contas: dívida de leasing de aviões (IFRS 16), net debt e debt-like items, capital próprio e geração de caixa depois da reestruturação. |
| **Toyota Caetano Portugal** | Já está no projeto. Os outros rendimentos valem quase metade do EBITDA, as amortizações sobem muito mais do que o imobilizado, há rubricas "outras" grandes no working capital e dependência do contrato com a Toyota. |
| **Corticeira Amorim** | Já está no projeto. Líder mundial da cortiça, grupo familiar cotado. Caixa líquida de descobertos bancários, dívida de curto prazo, sazonalidade de compra de cortiça e stocks altos. |

Para cada uma:
1. Usa as **contas consolidadas mais recentes publicadas** (FY2025 com comparativos de FY2024, se já existirem; senão FY2024). Prefere o pacote ESEF quando a empresa for cotada e o pacote estiver disponível. Se não houver ESEF, transcreve o PDF do relatório e contas para Excel no formato de `scripts/real_*.py`, linha a linha como impresso, com a página de cada demonstração na folha `Source` (URL, páginas, data de obtenção).
2. Confirma que é em euros, que as reading checks passam e que o balanço fecha. Se uma reading check falhar, corrige a transcrição, nunca o motor para a fazer passar.
3. Acrescenta um teste em `tests/test_real_companies.py` como os que já existem (EBITDA ou resultado operacional publicado reconstruído; alertas esperados classificados como verdadeiro positivo, alarme falso conhecido ou por rever).
4. Se não conseguires obter as contas da TAP (ficheiro inacessível, contas noutro formato), diz-me qual o ficheiro exato e o link, e segue com as outras duas. Não troques de empresa sem me perguntares.

Os factos sobre a privatização só entram no texto da demo como contexto, numa frase, com a fonte (notícia com data). Nunca no memo, que só usa as contas.

## 3. O que o visitante vê na app (modo demo)

Um modo demo ativado por uma variável de ambiente ou um ficheiro de configuração (por exemplo `DD_DEMO=1`), com o mesmo código da app normal. Nada de uma segunda app.

1. **Página inicial:** o nome, uma frase sobre o que faz ("A first-pass financial due diligence on published accounts: every figure traced to its source"), um aviso visível ("Demo on published accounts. Preliminary analysis, not an opinion.") e três cartões, um por empresa, cada um com uma frase sobre o achado mais interessante.
2. **Ao escolher uma empresa:** a app atual, com overview, deal view (pontes de EBITDA, net debt e working capital), red flags com a fonte, setor, rulebook e preço.
3. **Pode mexer:** aceitar ou rejeitar um item, mudar o tratamento de um debt-like, escolher completion accounts ou locked box e meter um EV, e ver o efeito. As decisões ficam só na sessão do visitante.
4. **Memo:** o memo guardado, com o resultado do verificador ("N figures checked, 0 without a source"). Diz claramente que foi escrito pelo agente e verificado automaticamente, antes de ser publicado.
5. **Downloads em destaque:** o **databook Excel** (é o que os profissionais vão abrir), a tabela de red flags e a request list.
6. **Rodapé:** quem fez, link do GitHub e do LinkedIn, e os limites (contas anuais, só euros, só due diligence financeira, primeira passagem para um analista rever).

Escondidos no modo demo: upload, botões de memo e PDF pela API, qualquer campo de chave.

## 4. Os memos e os databooks de exemplo

- Para cada empresa, segue a skill `.claude/skills/due-diligence`: corre o motor, escreve o memo sem API, corre o `--check-memo` até passar sem erros. Guarda o memo, o resultado do verificador e o databook em `docs/examples/<empresa>/`.
- A app em modo demo lê esses ficheiros. Os números do memo, do databook e da app têm de bater (testa isto).
- O databook tem de abrir limpo no Excel: sem erros de fórmula, painéis congelados, unidades visíveis. Se não houver motor de recálculo neste ambiente, diz-mo e eu abro-o no meu PC.

## 5. O GitHub tem de chamar a atenção

Quem chega ao repositório decide em 30 segundos. O `README.md` começa assim:
1. Nome, uma frase sobre o que faz e um botão/link **"Live demo"** (o link fica como marcador até eu publicar).
2. Um GIF curto ou uma imagem da app (gera as imagens com o Playwright, a partir da app a correr localmente) e uma imagem do databook em Excel.
3. Uma tabela **"What it found"** com as três empresas: dois achados por empresa, cada um com o número e a fonte.
4. "How it works" em cinco linhas e um diagrama simples das camadas (ler → calcular → regras → deal view → memo verificado).
5. "How it is verified": número de testes, reconstrução dos totais publicados, verificador do memo.
6. "Limits" e "Built by", com a nota sobre a assistência de IA e o que eu fiz e aprendi.

Os detalhes técnicos atuais do README passam para baixo ou para `docs/`.

Cria ainda, por empresa, um **case note** de uma página em `docs/examples/<empresa>/case_note.md`: contexto, três pontos para conversar numa entrevista (o número, porque importa num deal, a pergunta que faria à gestão) e os limites da análise. É o que vou ler antes de uma entrevista.

## 6. Publicação

Prepara tudo para o Streamlit Community Cloud (ficheiro principal `app.py`, `requirements.txt` com versões fixas, nenhum segredo necessário em modo demo) e escreve em `docs/DEPLOY.md` os passos exatos que eu faço em share.streamlit.io. **Não publiques nem faças push sem a minha aprovação.**

## 7. Testes e verificação

- Todos os testes atuais continuam a passar.
- Testes novos: as três empresas reais; o modo demo não mostra upload nem botões de API e funciona sem a biblioteca `anthropic` configurada; os números do memo, do databook e da app batem.
- Abre a app em modo demo localmente e percorre as três empresas e os downloads. Se não conseguires abrir, diz que a inspeção visual ficou pendente.
- Atualiza `docs/PROGRESS.md` e faz um commit local por incremento.

## 8. No fim

Mostra-me, em português: o que mudou; os testes corridos; as fontes de cada empresa (URL, páginas, data); os dois achados mais interessantes de cada uma; o que ficou pendente; e o comando para eu ver a demo no meu PC (`$env:DD_DEMO=1; streamlit run app.py`).

## Mensagem para colar no Claude Code

```
Lê integralmente docs/DEMO_ONLINE_SPEC.md e usa-o como especificação, junto com o CLAUDE.md. Começa por confirmar o que já existe (app, databook, exemplos, testes das empresas reais) e por obter as contas da TAP. Depois implementa por incrementos, com testes e um commit local por incremento. Fala comigo em português. Não faças push nem publiques sem a minha aprovação.
```
