# Due Diligence Assistant

Protótipo de um agente para **due diligence financeira preliminar em M&A**. Lê as demonstrações financeiras de uma empresa-alvo, calcula as métricas de Transaction Services, aplica 20 regras com limites explícitos e gera uma tabela de red flags: evidência com fonte → ponto a investigar → pergunta para a empresa.

> Exemplo incluído: **Duriva Distribuição Industrial, S.A.**, empresa fictícia criada para testar o método.

## Porquê
Em due diligence, boa parte do trabalho inicial é mecânica: cruzar demonstrações, calcular rácios, procurar variações e montar a lista de pedidos. Este projeto automatiza essa parte e deixa ao analista o julgamento.

## Como funciona
| Camada | Ficheiro | O que faz |
|---|---|---|
| Dados | `input_loader.py` | Lê a folha `Input` do template, com a fonte de cada linha |
| Métricas | `metrics.py` | Crescimento, concentração, margens, quality of earnings, DSO/DIO/DPO, conversão de caixa, dívida, consistência |
| Regras | `rules.py` | 20 regras com limites editáveis; cada alerta traz evidência e pergunta-modelo |
| Relatório | `report.py` | Red flags em Excel e CSV |
| IA (próximo passo) | `docs/camada_ia_prompt.md` | Junta alertas em temas e escreve o memo; não faz contas |

As contas são determinísticas e verificáveis: `tests/test_parity.py` confirma que o Python dá exatamente o mesmo resultado que a planilha.

## Correr
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest -v
python -m dd_assistant data\DD_template_modulo1.xlsx
```

## Resultado na Duriva
15 alertas (10 de relevância alta), entre eles: venda pontual apresentada como crescimento orgânico, concentração no maior cliente (23,8%), queda de 3,5 p.p. na margem bruta, ganho na venda de ativos dentro do EBITDA, conversão de caixa de 20,5%, 55% da dívida a vencer em 12 meses e uma DFC que não bate com o balanço.
