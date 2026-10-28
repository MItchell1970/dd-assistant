# Due Diligence Assistant — contexto para o Claude Code

## Quem sou e o que é este projeto
Sou o Bernardo, finalista de Economia na FEP (Porto), com estágio em Transaction Services na EY. Este projeto é um **AI agent para due diligence financeira preliminar em M&A**. Serve três objetivos: mostrar a empresas de M&A e Corporate Finance que domino o tema, aprender a usar IA no trabalho e ter um protótipo para apresentar.

**Sou iniciante em programação.** Fala comigo em português. Explica o que vais fazer antes de mexer em código, em passos pequenos, e diz-me exatamente que comando correr. Os termos de finanças podem ficar em inglês (EBITDA, net debt, quality of earnings).

**Todo o produto (app, regras, relatórios, memo, README) está em inglês**, para apresentar a empresas estrangeiras. Comigo, fala em português.

**Mercado prioritário: Europa, só em euros.** O foco é M&A (buy-side e vendor due diligence), mas a mesma análise serve um banco (crédito) ou uma análise sem transação. As regras são as da due diligence financeira (Big Four), do private equity e do crédito bancário, sempre explicadas em linguagem simples.

## Arquitetura (não misturar as camadas)
1. **Dados:** `dd_assistant/dataroom.py` lê o data room inteiro (pasta ou vários ficheiros): junta os Excel num só conjunto de contas (cada número guarda o ficheiro e a célula), lê o texto dos PDF, Word e txt para o memo (grátis, neste computador) e marca a checklist de documentos. `dd_assistant/esef.py` lê o relatório ESEF (iXBRL) das empresas cotadas, a partir das etiquetas: o pacote .zip traz a ordem das demonstrações, as etiquetas da empresa e a âncora de cada linha própria a um conceito IFRS; cada número fica com a etiqueta como fonte (`ifrs-full:Revenue`). Um .xhtml sozinho é recusado com uma mensagem a pedir o pacote. `dd_assistant/extract.py` identifica cada linha com um dicionário em seis línguas (SNC português, PGC espanhol, PCG francês, HGB alemão, código civil italiano, IFRS em inglês; PDF: o Claude lê com visão e o código converte unidades e sinais). Só euros: um ficheiro noutra moeda é recusado com uma mensagem clara. Lê formatos europeus (1.234,5 · 31.12.2024 · TEUR · miles de euros), DREs por natureza e por função (EBITDA = resultado operacional + D&A da DFC), subtotais antes ou depois das rubricas, para no resultado operacional e marca as linhas *debt-like* e *cash-like* do balanço (pensões, TFR, leasing, suprimentos, títulos). `dd_assistant/input_loader.py` define o modelo `CompanyData` e continua a ler o template Excel antigo (folha `Input`), que é a referência da paridade. `dd_assistant/units.py` formata os valores em euros (€1,415k; €939m nas empresas com receita acima de mil milhões de euros).
2. **Métricas:** `dd_assistant/metrics.py` faz todas as contas, de forma determinística. `None` = "n/a". Inclui as **reading checks**: margem bruta, EBITDA e resultado operacional reconstruídos a partir das linhas lidas e comparados com os subtotais publicados.
3. **Regras:** `dd_assistant/rules.py` tem o catálogo R01–R26 (limite, severidade, evidência, pergunta, documento a pedir, explicação em linguagem simples e a prática de onde vem) e gera os alertas. R01–R20 são as do template; R21–R26 vão além dele (alavancagem, cobertura de juros, prazo de fornecedores, capex abaixo das amortizações, taxa efetiva de imposto, trabalhos para a própria entidade). `dd_assistant/europe.py` tem os 10 países europeus (normativo, taxa de IRC, formas jurídicas que sugerem o país). `dd_assistant/sectors.py` tem os 15 setores: alguns limites calibrados (sempre com a razão à vista), benchmarks Damodaran (Europa, janeiro de 2026), *sector lens* (perguntas de especialista) e as palavras que sugerem o setor. Sem setor ("General"), os limites são os do template.
4. **Deal view:** `dd_assistant/deal.py` faz as três pontes que um deal team pede primeiro: quality of earnings (reportado → gestão → *diligence-adjusted*), net debt (com *debt-like* e *cash-like items*) e working capital (com uma referência indicativa para o *peg*). O revisor decide cada ajuste da gestão e cada item; os ajustes ainda não aceites ficam de fora (visão prudente do comprador).
5. **Relatório:** `dd_assistant/report.py` grava em Excel (red flags, deal view, setor, reading checks, métricas, source data) e CSV, com o estado e o comentário do revisor.
6. **IA:** `dd_assistant/ai_memo.py` envia à Claude API (`claude-opus-5-5`) os alertas, as regras, as métricas, o Input, o deal view, o setor e o data room integral, com `docs/ai_memo_prompt.md` como system prompt, e recebe o memo e a request list. **A IA nunca faz contas nem cria alertas.** Depois, `dd_assistant/memo_check.py` verifica o memo sem IA: números com fonte no material, todos os alertas, perguntas com pedido, nenhuma recomendação de investimento.
7. **Pipeline e app:** `dd_assistant/pipeline.py` corre a análise toda numa chamada (usada pela app, pela linha de comandos e pela skill), com a finalidade (buy, sell, lend, review), o país e o setor. `app.py` (Streamlit) só junta as camadas: arrastar o data room → overview → deal view → red flags → setor → data room → rulebook → memo.
8. **Agente:** `.claude/skills/due-diligence/SKILL.md` transforma o Claude Code num agente que usa o motor como ferramenta: corre a análise, confirma a leitura e o setor, pede ao utilizador as decisões que são dele (ajustes da gestão), escreve o memo sem chave da API e corrige-o até o verificador passar. Exemplo em `docs/examples/`.

## Comandos (Windows, PowerShell, na pasta do projeto)
```powershell
py -m venv .venv                      # uma vez: cria o ambiente virtual
.venv\Scripts\Activate.ps1            # sempre que abrir um terminal novo
pip install -r requirements.txt       # uma vez
python -m unittest -v                 # corre os testes
streamlit run app.py                  # abre a app no browser (só neste computador)
python -m dd_assistant data\Duriva_data_room                   # o data room inteiro (pasta com 5 documentos), em output\
python -m dd_assistant data\Duriva_data_room.xlsx              # também funciona com um só ficheiro
python -m dd_assistant data\Corticeira_Amorim_2024_published.xlsx --country PT --sector materials
python -m dd_assistant <pacote ESEF>.zip                      # relatório ESEF de uma cotada (filings.xbrl.org)
python -m dd_assistant data\Duriva_data_room --purpose lend     # buy (defeito), sell, lend, review
python -m dd_assistant --rules                                 # o livro de regras, em linguagem simples
python -m dd_assistant --sectors                               # lista os 15 setores e os limites calibrados
python -m dd_assistant data\Duriva_data_room.xlsx --adjustment "Custos de arranque=Accepted" --set orend:2025=60 --received "AR ageing"
python -m dd_assistant data\Duriva_data_room.xlsx --json --material   # JSON e material do memo (grátis)
python -m dd_assistant data\Duriva_data_room.xlsx --memo       # memo com IA (custa dinheiro)
python -m dd_assistant data\Duriva_data_room.xlsx --check-memo memo.md   # verifica um memo já escrito (grátis)
python -m dd_assistant data\DD_template_modulo1.xlsx           # o template antigo continua a funcionar
python scripts\empresa_limpa.py       # volta a gerar a Velmora (precisa do Excel)
python scripts\duriva_folder.py data\Duriva_data_room.xlsx data\Duriva_data_room   # volta a gerar a pasta de 5 documentos
python scripts\sector_benchmarks.py <pasta com os .xls>        # atualiza os benchmarks Damodaran (precisa de pip install xlrd)
```
Se o PowerShell bloquear o `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**Este PC é Windows ARM64.** O `.venv` usa o Python 3.13 **x64** (o `py` por defeito), porque o `pyarrow`, de que o Streamlit precisa, não tem versão ARM64. Também está instalado um Python ARM64 (`py -V:3.13-arm64`), que não serve para este projeto. O Git está em `C:\Program Files\Git\cmd`.

## Regras do projeto
- **Paridade com a planilha:** `tests/test_parity.py` compara os números do Python (métricas, valores das regras, disparos, limites, severidade) com os calculados nos templates da Duriva e da Velmora. Os textos não entram, porque o código escreve em inglês e a planilha de referência está em português. As regras R21–R26 e as métricas de `EXTENDED_LABELS` não existem na planilha: têm os seus próprios testes (`tests/test_rules.py`). Os testes têm de passar sempre. Se mudares uma métrica ou uma regra, muda também o template, ou explica-me porque a paridade deixa de fazer sentido.
- **ESEF:** `tests/test_esef.py` cria um pacote pequeno no próprio teste (o da EDP tem 96 MB e fica fora do projeto). Testado à mão com o ESEF FY2025 da EDP: o resultado operacional publicado é reconstruído ao milhar de euros.
- **Extração:** `tests/test_extract.py` exige que ler os data rooms brutos dê exatamente os mesmos números que os templates preenchidos à mão; `tests/test_dataroom.py` exige o mesmo da pasta de 5 documentos; `tests/test_europe.py` exige que as contas espanholas, francesas, alemãs e italianas sejam bem lidas.
- **Só euros:** não converter moedas. Um ficheiro noutra moeda é recusado com uma mensagem clara.
- **Rastreabilidade:** cada alerta tem evidência com números e a fonte no data room.
- **Evidência antes de conclusão:** o agente aponta pontos a investigar; não dá recomendações de investimento.
- **Nunca pôr o gabarito no projeto:** `Duriva_gabarito.xlsx` lista os problemas plantados na empresa de teste e fica fora desta pasta. Se a IA o vir, o teste deixa de valer.
- **Segredos:** a chave da Claude API vai para a variável de ambiente `ANTHROPIC_API_KEY` ou para um ficheiro `.env` (já no `.gitignore`). Nunca no código.
- **Alarmes falsos:** `tests/test_clean_company.py` exige zero alertas na Velmora, com os limites gerais e com os do setor dela (distribuição). Se uma mudança de regra ou de calibração o fizer falhar, mostra-me o alarme antes de mudar o teste.
- **Setores:** uma calibração só muda um limite com uma razão escrita, que aparece ao lado do alerta. Os benchmarks são orientação, nunca um alerta por si só.
- **Custos da API:** os testes nunca chamam a Claude API (usam um cliente falso). Pergunta-me antes de correr o `--memo`, o botão do memo ou a leitura de um PDF.
- Antes de cada alteração grande, corre os testes; depois, corre-os outra vez.

## Ficheiros de dados
- `data/DD_template_modulo1.xlsx`: template preenchido com a Duriva (empresa fictícia). É o input de exemplo e a referência da paridade.
- `data/Duriva_data_room.xlsx`: o data room da Duriva (DRE, balanço, DFC, clientes, EBITDA ajustado, dívida, relatório de gestão).
- `data/Duriva_data_room/`: o mesmo data room em 5 documentos, como um vendedor o enviaria (4 Excel e o relatório de gestão em PDF), gerado por `scripts/duriva_folder.py`.
- `data/DD_template_velmora.xlsx` e `data/Velmora_data_room.xlsx`: a Velmora, empresa fictícia "limpa" (0 alertas), gerada por `scripts/empresa_limpa.py`. Foi desenhada por quem conhece as regras: é um teste de sanidade.
- `data/Toyota_Caetano_2024_published.xlsx` e `data/Corticeira_Amorim_2024_published.xlsx`: contas consolidadas **reais** de 2024, copiadas tal como publicadas (fonte e páginas na folha "Source"; gerados por `scripts/real_*.py`). `tests/test_real_companies.py` exige que o agente reconstrua o EBITDA publicado ao euro, passe as reading checks, feche o balanço e dê os alertas esperados.

## Roadmap
1. ~~**Git e GitHub**~~ feito: repositório público em https://github.com/MItchell1970/dd-assistant (ramo `main`). Os commits usam o email privado do GitHub (`133356273+MItchell1970@users.noreply.github.com`), nunca o Gmail. Para enviar alterações: `git push`.
2. ~~**App em Streamlit**~~ feito e redesenhado: upload dos ficheiros financeiros (sem template) → rever o que foi lido → rever (Accepted / Dismissed / Pending) → descarregar Excel/CSV.
3. ~~**Camada de IA com a Claude API**~~ feita e testada sem chamadas reais. Falta a primeira corrida real com a chave do Bernardo e rever a qualidade do memo.
4. ~~**Segunda empresa fictícia "limpa"**~~ feita: Velmora, 0 alertas. Próximo nível: testar com contas reais de empresas saudáveis.
5. ~~**Ler ficheiros da empresa sem template**~~ feito para Excel (testado com os dois data rooms). **PDF** feito via Claude, mas ainda não testado com uma chamada real; falta experimentar com o PDF de umas contas reais.
6. ~~**Deal view, setores, DRE por função, agente (skill)**~~ feitos.
7. ~~**Foco europeu**~~ feito: só euros, seis formatos nacionais, país (normativo e IRC), data room com vários ficheiros, 26 regras explicadas, finalidade da análise (M&A, VDD, crédito, geral). Exemplo do agente na Amorim em `docs/examples/`.
8. ~~**ESEF**~~ feito: o pacote .zip de qualquer cotada europeia é lido a partir das etiquetas (testado com a EDP, FY2025).
9. **Próximos:** primeira corrida real do memo e do PDF com a chave da API; testar com contas reais espanholas, francesas, alemãs e italianas; levar a skill para o claude.ai; dados mensais (peg e LTM) quando o data room os tiver.
