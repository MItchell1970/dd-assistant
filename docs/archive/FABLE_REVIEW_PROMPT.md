# Prompt para a revisão da Fase B (colar numa sessão nova)

```
Revisão só de leitura: não edites ficheiros nem faças commits. Lê docs/archive/FASE4_SPEC.md (fase B), docs/PROGRESS.md e os resultados gerados para TAP, Toyota Caetano e Corticeira Amorim (risk score, top 5 deal issues, valuation impact bridge, open items, mapa de cobertura). Revê como um manager de Transaction Services: 1) o risk score faz sentido entre as três empresas e a fórmula é defensável? 2) os top deal issues estão na ordem certa e a proteção típica está correta? 3) há dupla contagem entre EBITDA e net debt? 4) algum achado é ruído ou falta algum óbvio? 5) o mapa de cobertura pede os documentos certos? Responde em português, numa tabela: Problema | Onde | Porquê | Correção proposta. No máximo 10 linhas.
```

Onde estão os resultados gerados: `docs/examples/tap/deal_layer.md`, `docs/examples/toyota-caetano/deal_layer.md`, `docs/examples/corticeira-amorim/deal_layer.md` (e as folhas Top Issues, Valuation Impact e Open Items de cada `databook.xlsx`; secção "Deal view" de `site/tap.html`, `site/toyota.html`, `site/amorim.html`). Código: `dd_assistant/deal_layer.py`.
