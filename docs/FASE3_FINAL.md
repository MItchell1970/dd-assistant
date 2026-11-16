# DD Assistant — fecho da Fase 3 (só o site)

Substitui as secções 6 e 7 do `docs/FASE3_SPEC.md`. Tudo o resto daquele ficheiro (B2, D3, A6, mais slides) **fica fora**. Não faças kit de candidaturas, nem mais PowerPoint, nem novas regras.

## Objetivo

Acabar o projeto com o mínimo de sessões: um site bonito, rápido e bem estruturado que faça um recrutador de Transaction Services querer falar comigo. Os blocos A1–A5, B1, B3 e C já estão feitos e no GitHub (commit b695f79).

## Como trabalhar (poupar tokens)

- Não releias o repositório inteiro: começa por `docs/PROGRESS.md` e pelos ficheiros que vais mudar.
- Não corras a bateria completa de testes a cada passo: corre só os testes do que mudaste; a bateria completa uma vez antes de cada commit.
- Capturas de ecrã só no fim de cada passo, a 1440 e a 375 px, nunca a meio.
- Sem subagentes, salvo para a verificação final.
- Respostas curtas: o que mudou, testes, comando para eu ver. Sem resumos longos.

## Passo 1 — Página estática (GitHub Pages)

O link do CV passa a ser uma página que abre sempre de imediato. A app Streamlit fica a um clique.

- `scripts/build_site.py` gera `site/index.html` e uma página por empresa (`site/tap.html`, `site/toyota.html`, `site/amorim.html`) a partir das saídas do motor e de `docs/examples/`. Um teste confirma que cada número das páginas existe no material.
- HTML e CSS num ficheiro por página, sem frameworks nem pedidos a terceiros além de fontes do Google.
- **Página inicial, por ordem:**
  1. Nome, frase de valor ("A first-pass financial due diligence on published accounts. Every figure traced to its source.") e quem fez (com a linha que eu confirmar).
  2. O GIF da demo.
  3. Os três casos, cada um com um número grande, a cascata principal em SVG e os downloads (databook, red flag report em PDF, memo).
  4. How it works, em 5 passos.
  5. How it is verified: testes, totais publicados reconstruídos, benchmark de deteção (48 de 49, com a falha explicada), números do memo verificados.
  6. Limites.
  7. Botão "Interactive demo" para a app Streamlit, com a nota "may take a few seconds to wake up", e links para o GitHub e o LinkedIn.
- **Página de cada empresa:** key insights, key issues ordenados por montante com a implicação para o deal, as cascatas (EBITDA, net debt, caixa), os downloads.
- **Desenho:** tipo serifado para títulos e números grandes, sans para o texto, navy e uma cor de destaque, muito espaço em branco, números tabulares, tema claro e escuro, perfeito a 375 px. Sem imagens de banco nem ícones decorativos.
- Metadados Open Graph com a social preview, para o link ficar bem no LinkedIn.
- Workflow `.github/workflows/pages.yml` que publica a pasta `site/` no GitHub Pages; passos para eu ativar em `docs/DEPLOY.md`.

## Passo 2 — App Streamlit

- A mesma paleta e tipografia da página estática (CSS próprio).
- Investiga a zona em branco que aparece ao fazer scroll na página da TAP em janelas estreitas (~800 px) e corrige-a se for um erro.
- Confere que a demo mostra o que a Fase 3 acrescentou (key issues com montante e implicação, três anos, estado de evidência das notas, ponte de caixa) sem cortes nem sobreposições.

## Passo 3 — README e fecho

- README: no topo, os links para a página estática e para a demo interativa, e a imagem da página inicial nova.
- `PROGRESS.md` e `GAPS.md` atualizados.
- A ponte de caixa no databook (pendente no `GAPS.md`) só se couber sem esforço; senão, fica registada.
- Mostra-me as capturas finais e pede-me aprovação para o push. Depois do push, diz-me os passos para ativar o GitHub Pages.

## Decisões que são minhas

1. A linha "Built by" (o meu estágio na EY foi em International Tax and Transaction Services).
2. O nome público: "DD Assistant" ou "Tickmark".

Se ainda não tiveres as respostas, usa "DD Assistant" e "Built by Bernardo Espinola, Economics, University of Porto" e segue.

## Mensagem para colar no Claude Code

```
Lê docs/FASE3_FINAL.md e segue-o. Só os passos 1 a 3: nada de slides, kit de candidaturas ou regras novas. Começa pelo docs/PROGRESS.md em vez de releres o repositório todo, e segue as regras de poupança de tokens do ficheiro. Fala comigo em português, com respostas curtas. Não faças push sem a minha aprovação.
```
