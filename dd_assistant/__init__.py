"""Due Diligence Assistant — análise financeira preliminar para M&A.

Camadas (sempre separadas):
    1. input_loader  -> lê os dados da folha Input do template Excel
    2. metrics       -> calcula as métricas (determinístico)
    3. rules         -> compara cada métrica com um limite e gera os alertas
    4. report        -> escreve a tabela de red flags (Excel e CSV)
    5. ai_memo       -> a Claude API escreve o memo e a request list (nunca faz contas nem cria alertas)
       memo_check    -> verifica o memo sem IA: números com fonte, alertas, perguntas, sem recomendações
A app (app.py, Streamlit) só junta estas camadas.
"""

__version__ = "0.2.0"
