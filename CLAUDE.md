# Due Diligence Assistant — contexto para o Claude Code

## Quem sou e o que é este projeto
Sou o Bernardo, finalista de Economia na FEP (Porto), com estágio em Transaction Services na EY. Este projeto é um **AI agent para due diligence financeira preliminar em M&A**. Serve três objetivos: mostrar a empresas de M&A e Corporate Finance que domino o tema, aprender a usar IA no trabalho e ter um protótipo para apresentar.

**Sou iniciante em programação.** Fala comigo em português. Explica o que vais fazer antes de mexer em código, em passos pequenos, e diz-me exatamente que comando correr. Os termos de finanças podem ficar em inglês (EBITDA, net debt, quality of earnings).

## Arquitetura (não misturar as camadas)
1. **Dados:** `dd_assistant/input_loader.py` lê a folha `Input` do template Excel. As linhas são encontradas pelo texto da coluna A, não pelo número da linha.
2. **Métricas:** `dd_assistant/metrics.py` faz todas as contas, de forma determinística. `None` = "n.d.".
3. **Regras:** `dd_assistant/rules.py` tem o catálogo R01–R20 (limite, relevância, evidência, pergunta, documento a pedir) e gera os alertas.
4. **Relatório:** `dd_assistant/report.py` grava os red flags em Excel e CSV, com o estado e o comentário do revisor.
5. **IA:** `dd_assistant/ai_memo.py` envia à Claude API (`claude-opus-5-5`) os alertas, as regras, as métricas, o Input e o data room integral, com `docs/camada_ia_prompt.md` como system prompt, e recebe o memo e a request list. **A IA nunca faz contas nem cria alertas.**
6. **App:** `app.py` (Streamlit) só junta as camadas: carregar o template → rever os alertas → descarregar → memo com IA.

## Comandos (Windows, PowerShell, na pasta do projeto)
```powershell
py -m venv .venv                      # uma vez: cria o ambiente virtual
.venv\Scripts\Activate.ps1            # sempre que abrir um terminal novo
pip install -r requirements.txt       # uma vez
python -m unittest -v                 # corre os testes
python -m dd_assistant data\DD_template_modulo1.xlsx   # gera os red flags em output\
streamlit run app.py                  # abre a app no browser (só neste computador)
python -m dd_assistant data\DD_template_modulo1.xlsx --memo --data-room data\Duriva_data_room.xlsx   # memo com IA (custa dinheiro)
python scripts\empresa_limpa.py       # volta a gerar a Velmora (precisa do Excel)
```
Se o PowerShell bloquear o `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**Este PC é Windows ARM64.** O `.venv` usa o Python 3.13 **x64** (o `py` por defeito), porque o `pyarrow`, de que o Streamlit precisa, não tem versão ARM64. Também está instalado um Python ARM64 (`py -V:3.13-arm64`), que não serve para este projeto. O Git está em `C:\Program Files\Git\cmd`.

## Regras do projeto
- **Paridade com a planilha:** `tests/test_parity.py` compara o Python com os valores calculados nos templates da Duriva e da Velmora. Os testes têm de passar sempre. Se mudares uma métrica ou uma regra, muda também o template, ou explica-me porque a paridade deixa de fazer sentido.
- **Rastreabilidade:** cada alerta tem evidência com números e a fonte no data room.
- **Evidência antes de conclusão:** o agente aponta pontos a investigar; não dá recomendações de investimento.
- **Nunca pôr o gabarito no projeto:** `Duriva_gabarito.xlsx` lista os problemas plantados na empresa de teste e fica fora desta pasta. Se a IA o vir, o teste deixa de valer.
- **Segredos:** a chave da Claude API vai para a variável de ambiente `ANTHROPIC_API_KEY` ou para um ficheiro `.env` (já no `.gitignore`). Nunca no código.
- **Alarmes falsos:** `tests/test_clean_company.py` exige zero alertas na Velmora. Se uma mudança de regra o fizer falhar, mostra-me o alarme antes de mudar o teste.
- **Custos da API:** os testes nunca chamam a Claude API (usam um cliente falso). Pergunta-me antes de correr o `--memo` ou o botão do memo.
- Antes de cada alteração grande, corre os testes; depois, corre-os outra vez.

## Ficheiros de dados
- `data/DD_template_modulo1.xlsx`: template preenchido com a Duriva (empresa fictícia). É o input de exemplo e a referência da paridade.
- `data/Duriva_data_room.xlsx`: o data room da Duriva (DRE, balanço, DFC, clientes, EBITDA ajustado, dívida, relatório de gestão).
- `data/DD_template_velmora.xlsx` e `data/Velmora_data_room.xlsx`: a Velmora, empresa fictícia "limpa" (0 alertas), gerada por `scripts/empresa_limpa.py`. Foi desenhada por quem conhece as regras: é um teste de sanidade.

## Roadmap
1. ~~**Git e GitHub**~~ feito: repositório público em https://github.com/MItchell1970/dd-assistant (ramo `main`). Os commits usam o email privado do GitHub (`133356273+MItchell1970@users.noreply.github.com`), nunca o Gmail. Para enviar alterações: `git push`.
2. ~~**App em Streamlit**~~ feito: carregar o template → rever (Aceite / Descartado / Pendente) → descarregar Excel/CSV.
3. ~~**Camada de IA com a Claude API**~~ feita e testada sem chamadas reais. Falta a primeira corrida real com a chave do Bernardo e rever a qualidade do memo.
4. ~~**Segunda empresa fictícia "limpa"**~~ feita: Velmora, 0 alertas. Próximo nível: testar com contas reais de empresas saudáveis.
5. **v3 (opcional):** ler PDFs de demonstrações financeiras para preencher o Input, com verificação humana.
