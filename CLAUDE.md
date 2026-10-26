# Due Diligence Assistant — contexto para o Claude Code

## Quem sou e o que é este projeto
Sou o Bernardo, finalista de Economia na FEP (Porto), com estágio em Transaction Services na EY. Este projeto é um **AI agent para due diligence financeira preliminar em M&A**. Serve três objetivos: mostrar a empresas de M&A e Corporate Finance que domino o tema, aprender a usar IA no trabalho e ter um protótipo para apresentar.

**Sou iniciante em programação.** Fala comigo em português. Explica o que vais fazer antes de mexer em código, em passos pequenos, e diz-me exatamente que comando correr. Os termos de finanças podem ficar em inglês (EBITDA, net debt, quality of earnings).

## Arquitetura (não misturar as camadas)
1. **Dados:** `dd_assistant/input_loader.py` lê a folha `Input` do template Excel. As linhas são encontradas pelo texto da coluna A, não pelo número da linha.
2. **Métricas:** `dd_assistant/metrics.py` faz todas as contas, de forma determinística. `None` = "n.d.".
3. **Regras:** `dd_assistant/rules.py` tem o catálogo R01–R20 (limite, relevância, evidência, pergunta, documento a pedir) e gera os alertas.
4. **Relatório:** `dd_assistant/report.py` grava os red flags em Excel e CSV.
5. **IA (por fazer):** lê os alertas e escreve o memo e as perguntas finais, seguindo `docs/camada_ia_prompt.md`. **A IA nunca faz contas nem cria alertas.**

## Comandos (Windows, PowerShell, na pasta do projeto)
```powershell
py -m venv .venv                      # uma vez: cria o ambiente virtual
.venv\Scripts\Activate.ps1            # sempre que abrir um terminal novo
pip install -r requirements.txt       # uma vez
python -m unittest -v                 # corre os testes
python -m dd_assistant data\DD_template_modulo1.xlsx   # gera os red flags em output\
```
Se o PowerShell bloquear o `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Regras do projeto
- **Paridade com a planilha:** `tests/test_parity.py` compara o Python com os valores calculados no `data/DD_template_modulo1.xlsx`. Os testes têm de passar sempre. Se mudares uma métrica ou uma regra, muda também o template, ou explica-me porque a paridade deixa de fazer sentido.
- **Rastreabilidade:** cada alerta tem evidência com números e a fonte no data room.
- **Evidência antes de conclusão:** o agente aponta pontos a investigar; não dá recomendações de investimento.
- **Nunca pôr o gabarito no projeto:** `Duriva_gabarito.xlsx` lista os problemas plantados na empresa de teste e fica fora desta pasta. Se a IA o vir, o teste deixa de valer.
- **Segredos:** a chave da Claude API vai para a variável de ambiente `ANTHROPIC_API_KEY` ou para um ficheiro `.env` (já no `.gitignore`). Nunca no código.
- Antes de cada alteração grande, corre os testes; depois, corre-os outra vez.

## Ficheiros de dados
- `data/DD_template_modulo1.xlsx`: template preenchido com a Duriva (empresa fictícia). É o input de exemplo e a referência da paridade.
- `data/Duriva_data_room.xlsx`: o data room da Duriva (DRE, balanço, DFC, clientes, EBITDA ajustado, dívida, relatório de gestão).

## Próximos passos (roadmap)
1. **Git e GitHub:** `git init`, primeiro commit, repositório público para o portfólio.
2. **App em Streamlit:** carregar o template → ver os red flags → descarregar Excel/CSV. O revisor marca cada alerta como Aceite, Descartado ou Pendente.
3. **Camada de IA com a Claude API:** enviar os alertas, as métricas e os textos do data room com o prompt de `docs/camada_ia_prompt.md`; receber o memo de duas páginas e a request list.
4. **Segunda empresa fictícia "limpa":** para medir alarmes falsos.
5. **v3 (opcional):** ler PDFs de demonstrações financeiras para preencher o Input, com verificação humana.
