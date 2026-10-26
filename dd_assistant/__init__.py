"""Due Diligence Assistant — análise financeira preliminar para M&A.

Camadas (sempre separadas):
    1. input_loader  -> lê os dados da folha Input do template Excel
    2. metrics       -> calcula as métricas (determinístico)
    3. rules         -> compara cada métrica com um limite e gera os alertas
    4. report        -> escreve a tabela de red flags (Excel e CSV)
A camada de IA (memo e perguntas finais) vem depois e nunca faz contas.
"""

__version__ = "0.1.0"
