"""App Streamlit — carregar o template, ver e rever os red flags, descarregar.

Correr (com o ambiente virtual ativo):
    streamlit run app.py

A app só junta as camadas que já existem (input_loader → metrics → rules → report).
Não faz contas nem cria alertas: o revisor marca cada alerta como Aceite, Descartado ou Pendente.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from dd_assistant.input_loader import load_input
from dd_assistant.metrics import LABELS, compute_metrics
from dd_assistant.report import REVIEW_STATES, csv_bytes, write_excel
from dd_assistant.rules import alerts, evaluate

DATA = Path(__file__).parent / "data"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_resource(max_entries=5, show_spinner=False)
def analyse(content: bytes):
    """Camadas 1 a 3 sobre o ficheiro carregado (em cache pelo conteúdo do ficheiro)."""
    data = load_input(io.BytesIO(content))
    metrics = compute_metrics(data)
    return data, metrics, evaluate(data, metrics)


def fmt(v) -> str:
    """Mostra uma métrica como na evidência: None = 'n.d.', até 4 casas decimais."""
    if v is None:
        return "n.d."
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


st.set_page_config(page_title="Due Diligence Assistant", layout="wide")

# ---------------------------------------------------------------- escolher o ficheiro
with st.sidebar:
    st.header("Template")
    uploaded = st.file_uploader("Carregar o template preenchido", type="xlsx",
                                help="Um ficheiro com a mesma estrutura de DD_template_modulo1.xlsx (folha Input).")
    examples = sorted(DATA.glob("DD_template_*.xlsx"))
    example = st.selectbox("…ou usar um exemplo", examples, format_func=lambda p: p.name,
                           disabled=uploaded is not None)
    st.caption("A análise corre neste computador. O ficheiro não é enviado para lado nenhum.")

if uploaded is not None:
    name, content = uploaded.name, uploaded.getvalue()
elif example is not None:
    name, content = example.name, example.read_bytes()
else:
    st.info("Carregue um template na barra lateral.")
    st.stop()

try:
    data, metrics, results = analyse(content)
except Exception as e:   # ficheiro sem folha Input ou com outra estrutura
    st.error(f"Não consegui ler a folha Input de {name}: {e}")
    st.stop()

al = alerts(results)
file_key = hashlib.sha1(content).hexdigest()[:12]   # a revisão fica guardada por ficheiro

st.title("Due Diligence Assistant")
st.caption(f"{name} · exercícios {data.pl_years[0]}–{data.pl_years[-1]} · € milhares · "
           "pontos a investigar, não conclusões")

tab_rf, tab_m = st.tabs(["Red flags", "Métricas"])

# ---------------------------------------------------------------- red flags e revisão
with tab_rf:
    summary = st.container()   # preenchido depois da tabela, porque "Por rever" depende dela

    if al:
        table = pd.DataFrame([{"Nº": i, "Regra": r.rule.id, "Alerta": r.rule.name, "Relevância": r.rule.relevance,
                               "Anos": r.years_text, "Estado": "Pendente", "Comentário": ""}
                              for i, r in enumerate(al, 1)])
        st.subheader("Revisão")
        st.caption("Clique duas vezes em Estado ou Comentário para editar. O detalhe de cada alerta está mais abaixo.")
        edited = st.data_editor(
            table, key=f"review-{file_key}", hide_index=True, width="stretch",
            height=35 * (len(table) + 1) + 3,   # todas as linhas visíveis, sem barra de deslocação
            disabled=["Nº", "Regra", "Alerta", "Relevância", "Anos"],
            column_config={
                "Nº": st.column_config.NumberColumn(width="small"),
                "Regra": st.column_config.TextColumn(width="small"),
                "Alerta": st.column_config.TextColumn(width="large"),
                "Relevância": st.column_config.TextColumn(width="small"),
                "Anos": st.column_config.TextColumn(width="small"),
                "Estado": st.column_config.SelectboxColumn(options=REVIEW_STATES, required=True, width="small"),
                "Comentário": st.column_config.TextColumn(width="medium"),
            })
        reviews = {row["Regra"]: (row["Estado"], row["Comentário"] or "") for row in edited.to_dict("records")}
    else:
        reviews = {}
        st.success("Nenhuma regra disparou para este template.")

    by = {k: sum(r.rule.relevance == k for r in al) for k in ("Alta", "Média", "Baixa")}
    with summary:
        c = st.columns(5)
        c[0].metric("Alertas", len(al))
        c[1].metric("Alta", by["Alta"])
        c[2].metric("Média", by["Média"])
        c[3].metric("Baixa", by["Baixa"])
        c[4].metric("Por rever", sum(state == "Pendente" for state, _ in reviews.values()))

    stem = Path(name).stem
    buf = io.BytesIO()
    write_excel(results, metrics, data.years, buf, reviews)
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Descarregar Excel", buf.getvalue(), f"{stem}_red_flags.xlsx", mime=XLSX_MIME)
    d2.download_button("Descarregar CSV", csv_bytes(results, reviews), f"{stem}_red_flags.csv", mime="text/csv")

    if al:
        st.subheader("Detalhe dos alertas")
        for i, r in enumerate(al, 1):
            rule = r.rule
            state = reviews[rule.id][0]
            with st.expander(f"{i}. {rule.id} · {rule.name} ({r.years_text}) — {rule.relevance} · {state}"):
                st.markdown(f"**Evidência:** {r.evidence}")
                st.markdown(f"**Cálculo:** {rule.calc}  \n**Regra:** {rule.rule_text()}")
                st.markdown(f"**Ponto a investigar:** {rule.ponto}")
                st.markdown(f"**Porque importa:** {rule.porque}")
                st.markdown(f"**Pergunta para a empresa:** {rule.pergunta}")
                st.markdown(f"**Documento a pedir:** {rule.documento}")

# ---------------------------------------------------------------- métricas
with tab_m:
    rows = [[label] + [fmt(metrics[key].get(y)) for y in data.years] for key, label in LABELS.items()]
    st.dataframe(pd.DataFrame(rows, columns=["Métrica"] + [str(y) for y in data.years]),
                 hide_index=True, width="stretch", height=35 * (len(rows) + 1) + 3)
    st.caption("Percentagens em decimal (0.238 = 23,8%); variações de margem em pontos percentuais. "
               "'n.d.' = não disponível (falta o ano anterior ou o dado).")
