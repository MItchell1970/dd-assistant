# Due Diligence Assistant

Protótipo de um agente para **due diligence financeira preliminar em M&A**. Lê as demonstrações financeiras de uma empresa-alvo, calcula as métricas de Transaction Services, aplica 20 regras com limites explícitos e gera uma tabela de red flags: evidência com fonte → ponto a investigar → pergunta para a empresa. Uma camada de IA escreve depois o memo de duas páginas e a information request list, sem fazer contas nem criar alertas.

> Exemplos incluídos (empresas fictícias): **Duriva Distribuição Industrial, S.A.**, com problemas plantados, e **Velmora Material Elétrico, S.A.**, uma empresa "limpa" para medir alarmes falsos.

## Porquê
Em due diligence, boa parte do trabalho inicial é mecânica: cruzar demonstrações, calcular rácios, procurar variações e montar a lista de pedidos. Este projeto automatiza essa parte e deixa ao analista o julgamento.

## Como funciona
| Camada | Ficheiro | O que faz |
|---|---|---|
| Dados | `input_loader.py` | Lê a folha `Input` do template, com a fonte de cada linha |
| Métricas | `metrics.py` | Crescimento, concentração, margens, quality of earnings, DSO/DIO/DPO, conversão de caixa, dívida, consistência |
| Regras | `rules.py` | 20 regras com limites editáveis; cada alerta traz evidência e pergunta-modelo |
| Relatório | `report.py` | Red flags em Excel e CSV, com o estado e o comentário do revisor |
| IA | `ai_memo.py` + `docs/camada_ia_prompt.md` | Junta os alertas em temas e escreve o memo e a request list com a Claude API; não faz contas nem cria alertas |
| Verificação | `memo_check.py` | Confirma, sem IA, que cada número do memo existe no material, que todos os alertas aparecem, que cada pergunta tem um pedido e que não há recomendação de investimento |
| App | `app.py` | Carregar o template → rever os alertas (Aceite / Descartado / Pendente) → descarregar → memo com IA |

As contas são determinísticas e verificáveis: `tests/test_parity.py` confirma que o Python dá exatamente o mesmo resultado que as fórmulas da planilha, nas duas empresas.

## Instalar (Windows, PowerShell)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest -v
```
Em PCs Windows com processador ARM, use o Python **x64**: o Streamlit depende do `pyarrow`, que ainda não tem versão para Windows ARM64.

## Usar
```powershell
# red flags em output\ (Excel e CSV)
python -m dd_assistant data\DD_template_modulo1.xlsx

# app no browser (só neste computador)
streamlit run app.py

# memo e request list com a Claude API (precisa da chave no ficheiro .env; ver .env.example)
python -m dd_assistant data\DD_template_modulo1.xlsx --memo --data-room data\Duriva_data_room.xlsx

# verificar um memo escrito fora do programa (por exemplo, no claude.ai com o mesmo prompt)
python -m dd_assistant data\DD_template_modulo1.xlsx --check-memo memo.md --data-room data\Duriva_data_room.xlsx
```
O memo usa o Claude Opus 5.5 e custa cerca de 0,2 a 0,5 USD por empresa (o valor real aparece no fim). O texto exato enviado à IA fica gravado em `output\*_material_ia.md`, para auditoria. Depois de cada memo, o verificador corre sozinho e grava o resultado em `output\*_verificacao.md`; na app aparece a verde ou a vermelho. Limitação: um número pequeno inventado (por exemplo, 37%) pode coincidir por acaso com outro do material; os números grandes são verificados com segurança.

## Resultados
**Duriva:** 15 alertas (10 de relevância alta), entre eles: venda pontual apresentada como crescimento orgânico, concentração no maior cliente (23,8%), queda de 3,5 p.p. na margem bruta, ganho na venda de ativos dentro do EBITDA, conversão de caixa de 20,5%, 55% da dívida a vencer em 12 meses e uma DFC que não bate com o balanço.

**Velmora (empresa limpa):** 0 alertas, com todas as regras calculadas. A regra mais próxima do limite é a dívida a 12 meses (27% para um limite de 40%). Limitação: a Velmora foi desenhada por quem conhece as regras, por isso é um teste de sanidade e não uma medida independente de alarmes falsos. O teste mais forte seria correr o agente sobre contas reais de empresas saudáveis. A empresa é gerada por `scripts/empresa_limpa.py` (precisa do Excel para recalcular o template).
