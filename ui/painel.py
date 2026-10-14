"""Painel de curadoria do CommunityLab. Dono: pessoa 3.

Rode da raiz do projeto com: streamlit run ui/painel.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.grafo import processar  # noqa: E402
from app.llm import modo_mock  # noqa: E402
from app.schemas import LoteEntrada  # noqa: E402

st.set_page_config(page_title="CommunityLab", page_icon="📣", layout="wide")
st.title("CommunityLab · Painel de Curadoria")
st.caption(f"Modo do LLM: {'simulado' if modo_mock() else 'Gemini'}")

# ---------- Entrada ----------
with st.sidebar:
    st.header("Lote de interações")
    arquivo = st.file_uploader("Envie um JSON no formato do contrato", type="json")
    usar_exemplo = st.button("Usar lote de exemplo")
    processar_btn = st.button("Processar lote", type="primary")

if usar_exemplo:
    st.session_state.lote = json.loads((RAIZ / "data/interacoes_exemplo.json").read_text(encoding="utf-8"))
if arquivo:
    st.session_state.lote = json.load(arquivo)

if "lote" in st.session_state and processar_btn:
    with st.spinner("Analisando a comunidade e gerando ativos..."):
        st.session_state.resultado = processar(LoteEntrada(**st.session_state.lote))
        st.session_state.aprovados = {}

if "resultado" not in st.session_state:
    st.info("Carregue um lote na barra lateral e clique em Processar.")
    st.stop()

r = st.session_state.resultado
resumo = r["resumo_comunidade"]
ativos = r["ativos_distribuicao_gerados"]

# ---------- Saúde da comunidade ----------
c1, c2, c3 = st.columns(3)
c1.metric("Interações processadas", resumo["total_interacoes_processadas"])
c2.metric("Sentimento predominante", resumo["sentimento_predominante"])
c3.metric("Alertas", len(ativos.get("alertas_comunidade", [])))

df = pd.DataFrame(r["analises"])
col_a, col_b = st.columns(2)
col_a.subheader("Sentimento")
col_a.bar_chart(df["sentimento"].value_counts())
col_b.subheader("Rotas")
col_b.bar_chart(df["rota"].value_counts())

with st.expander("Todas as interações analisadas"):
    st.dataframe(df[["autor", "canal", "tipo", "sentimento", "topico", "relevancia", "rota"]],
                 use_container_width=True, hide_index=True)

# ---------- Curadoria ----------
st.header("Ativos para aprovação")


def bloco_aprovacao(chave: str, titulo: str, texto: str):
    st.subheader(titulo)
    editado = st.text_area("Texto", texto, height=220, key=f"txt_{chave}")
    if st.button("Aprovar", key=f"btn_{chave}"):
        st.session_state.aprovados[chave] = editado
    if chave in st.session_state.aprovados:
        st.success("Aprovado")


if post := ativos.get("post_linkedin"):
    bloco_aprovacao("linkedin", f"LinkedIn · {post['titulo']}", post["copy"])

if news := ativos.get("destaque_newsletter_semanal"):
    bloco_aprovacao("newsletter", f"Newsletter · {news['secao']}", f"{news['chamada']}\n\n{news['resumo']}")

for n, faq in enumerate(ativos.get("sugestao_conteudo_faq", [])):
    bloco_aprovacao(f"faq_{n}", faq["tema"], faq["conteudo"])

if alertas := ativos.get("alertas_comunidade"):
    st.header("Membros que precisam de apoio")
    for a in alertas:
        st.warning(f"**{a['autor']}** · {a['motivo']}")

st.divider()
st.caption(f"Pacote salvo em: {r['armazenamento_oci']['caminho_objeto']} ({r['armazenamento_oci']['status']})")
