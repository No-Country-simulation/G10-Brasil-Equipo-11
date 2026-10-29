"""Tela Insights do painel: o histórico dos lotes gravados no Supabase em 7 gráficos.

Lê só do banco (via `app.repositorio`), nunca de `st.session_state["resultado"]`.
As contas ficam em `ui/insights.py`; aqui só filtros e desenho.
"""
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

from app import llm, repositorio
from ui import insights as ins
from ui.estilo import AZUL, AZUL_ESCURO, CINZA, LARANJA, LARANJA_ESCURO, ROTAS, SENTIMENTOS

MODOS = {"Gemini": "gemini", "Simulado": "mock"}
SEMANAS_PADRAO = 8
CORES_CANAIS = [AZUL, LARANJA, CINZA, AZUL_ESCURO, LARANJA_ESCURO, "#6C8FE0", "#C3C8D1"]
NOMES_SENT = [nome for nome, _ in SENTIMENTOS]
ORDEM_SENT = {nome: i for i, nome in enumerate(NOMES_SENT)}
ESCALA_SENT = alt.Scale(domain=NOMES_SENT, range=[cor for _, cor in SENTIMENTOS])
ESTADOS_ATIVOS = [("Aprovados", "aprovados", AZUL), ("Descartados", "descartados", CINZA),
                  ("Pendentes", "pendentes", "#C3C8D1")]


def _pct(valor: float) -> str:
    return f"{valor:.1f}%".replace(".", ",")


def _periodo(valor, padrao: tuple) -> tuple:
    """O date_input devolve 1 data enquanto a pessoa ainda escolhe o fim do intervalo: vale como inicio = fim."""
    datas = tuple(valor) if isinstance(valor, (tuple, list)) else (valor,)
    datas = tuple(d for d in datas if d is not None)
    if not datas:
        return padrao
    return datas[0], datas[-1]


def _filtros():
    """Desenha os filtros numa linha e devolve (inicio, fim, modo, comunidades, canais)."""
    hoje = pd.Timestamp.now(tz=ins.FUSO).date()
    padrao = (hoje - timedelta(weeks=SEMANAS_PADRAO), hoje)
    c_com, c_per, c_can, c_modo = st.columns([3, 2, 3, 2], vertical_alignment="bottom")
    no_simulado = list(MODOS).index("Simulado") if llm.modo_mock() else 0  # começa no modo em que o app roda
    modo = MODOS[c_modo.radio("Modo", list(MODOS), index=no_simulado, key="ins_modo", horizontal=True)]
    opcoes = repositorio.opcoes_filtros(modo)
    comunidades = c_com.multiselect("Comunidade", opcoes["comunidades"], key="ins_comunidades", placeholder="Todas")
    inicio, fim = _periodo(c_per.date_input("Período", value=padrao, key="ins_periodo", format="DD/MM/YYYY"), padrao)
    canais = c_can.multiselect("Canal", opcoes["canais"], key="ins_canais", placeholder="Todos")
    return inicio, fim, modo, comunidades or None, canais or None


def _ordem_dos_lotes(tabela: pd.DataFrame) -> list:
    return list(dict.fromkeys(tabela["rotulo"]))  # já vem em ordem cronológica


def _grafico_sentimento_por_lote(df: pd.DataFrame) -> alt.Chart:
    t = ins.sentimento_por_lote(df)
    t["ordem"] = t["sentimento"].map(ORDEM_SENT)
    return alt.Chart(t).mark_bar().encode(
        x=alt.X("rotulo:N", sort=_ordem_dos_lotes(t), title=None, axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("sum(quantidade):Q", title="Mensagens"),
        color=alt.Color("sentimento:N", scale=ESCALA_SENT, title="Sentimento"),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("rotulo:N", title="Lote"), alt.Tooltip("sentimento:N", title="Sentimento"),
                 alt.Tooltip("sum(quantidade):Q", title="Mensagens")],
    )


def _grafico_sentimento_por_canal(df: pd.DataFrame) -> alt.Chart:
    t = ins.sentimento_por_canal(df)
    t["ordem"] = t["sentimento"].map(ORDEM_SENT)
    return alt.Chart(t).mark_bar().encode(
        y=alt.Y("canal:N", title=None),
        x=alt.X("percentual:Q", stack="zero", title="% das mensagens do canal", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("sentimento:N", scale=ESCALA_SENT, title="Sentimento"),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("canal:N", title="Canal"), alt.Tooltip("sentimento:N", title="Sentimento"),
                 alt.Tooltip("quantidade:Q", title="Mensagens"),
                 alt.Tooltip("percentual:Q", title="%", format=".1f")],
    )


def _grafico_topicos(df: pd.DataFrame) -> alt.Chart:
    t = ins.topicos_mais_falados(df)
    return alt.Chart(t).mark_bar(color=AZUL).encode(
        y=alt.Y("topico:N", sort=list(t["topico"]), title=None),
        x=alt.X("quantidade:Q", title="Mensagens"),
        tooltip=[alt.Tooltip("topico:N", title="Tópico"), alt.Tooltip("quantidade:Q", title="Mensagens")],
    )


def _grafico_volume_por_canal(df: pd.DataFrame) -> alt.Chart:
    t = ins.volume_por_canal(df)
    canais = sorted(t["canal"].unique())
    cores = [CORES_CANAIS[i % len(CORES_CANAIS)] for i in range(len(canais))]
    return alt.Chart(t).mark_line(point=True).encode(
        x=alt.X("rotulo:N", sort=_ordem_dos_lotes(t), title=None, axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("quantidade:Q", title="Mensagens"),
        color=alt.Color("canal:N", scale=alt.Scale(domain=canais, range=cores), title="Canal"),
        tooltip=[alt.Tooltip("rotulo:N", title="Lote"), alt.Tooltip("canal:N", title="Canal"),
                 alt.Tooltip("quantidade:Q", title="Mensagens")],
    )


def _grafico_rotas(df: pd.DataFrame) -> alt.Chart:
    t = ins.rotas_geradas(df)
    return alt.Chart(t).mark_bar().encode(
        x=alt.X("nome:N", sort=list(t["nome"]), title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("quantidade:Q", title="Mensagens"),
        color=alt.Color("nome:N", scale=alt.Scale(domain=list(t["nome"]), range=[ROTAS[r]["barra"] for r in t["rota"]]),
                        legend=None),
        tooltip=[alt.Tooltip("nome:N", title="Rota"), alt.Tooltip("quantidade:Q", title="Mensagens")],
    )


def _grafico_ativos(numeros: dict) -> alt.Chart:
    t = pd.DataFrame({"estado": [n for n, _, _ in ESTADOS_ATIVOS], "quantidade": [numeros[c] for _, c, _ in ESTADOS_ATIVOS]})
    return alt.Chart(t).mark_bar().encode(
        x=alt.X("estado:N", sort=list(t["estado"]), title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("quantidade:Q", title="Ativos"),
        color=alt.Color("estado:N", scale=alt.Scale(domain=list(t["estado"]), range=[c for _, _, c in ESTADOS_ATIVOS]),
                        legend=None),
        tooltip=[alt.Tooltip("estado:N", title="Situação"), alt.Tooltip("quantidade:Q", title="Ativos")],
    )


def _quadro(titulo: str, legenda: str, grafico: alt.Chart, rodape: str | None = None):
    with st.container(border=True):
        st.subheader(titulo)
        st.caption(legenda)
        st.altair_chart(grafico, width="stretch")
        if rodape:
            st.caption(rodape)


def tela_insights() -> None:
    st.title("Insights")
    if not repositorio.banco_configurado():
        st.info("O histórico precisa do banco Supabase. Basta preencher `DATABASE_URL` no arquivo `.env` "
                "(veja o README) e abrir o painel de novo.")
        return
    st.markdown('<p class="cl-sub">Como a comunidade evoluiu ao longo dos lotes já processados.</p>', unsafe_allow_html=True)
    try:
        inicio, fim, modo, comunidades, canais = _filtros()
        df = repositorio.consultar_interacoes(inicio, fim, modo, comunidades=comunidades, canais=canais)
        ativos = repositorio.consultar_ativos(inicio, fim, modo, comunidades=comunidades, canais=canais)
    except Exception as e:
        st.warning(f"Não foi possível consultar o histórico: {e}")
        return
    st.caption("Cada número conta mensagens, não pessoas.")
    if df.empty:
        st.info("Nenhum lote processado com esses filtros.")
        return

    n = ins.numeros_periodo(df)
    k1, k2, k3, k4 = st.columns(4)
    for coluna, rotulo, valor in ((k1, "Interações", n["total"]), (k2, "Positivas", _pct(n["pct_positivas"])),
                                  (k3, "Negativas", _pct(n["pct_negativas"])), (k4, "Alertas", n["alertas"])):
        with coluna.container(border=True):
            st.metric(rotulo, valor)

    a, b = st.columns(2)
    with a:
        _quadro("Sentimento por lote", "Mensagens de cada lote, por sentimento.", _grafico_sentimento_por_lote(df))
    with b:
        _quadro("Sentimento por canal", "Proporção de cada sentimento dentro do canal.", _grafico_sentimento_por_canal(df))
    a, b = st.columns(2)
    with a:
        _quadro("Tópicos mais falados", "Os 10 tópicos com mais mensagens no período.", _grafico_topicos(df))
    with b:
        _quadro("Volume por canal", "Mensagens de cada canal, lote a lote.", _grafico_volume_por_canal(df))
    a, b = st.columns(2)
    with a:
        _quadro("Rotas geradas", "Mensagens que viraram case de sucesso, FAQ ou alerta.", _grafico_rotas(df))
    with b:
        aproveitamento = ins.aproveitamento_ativos(ativos)
        rodape = "A newsletter não tem canal de origem e fica de fora com o filtro de canal." if canais else None
        _quadro("Aproveitamento dos ativos", f"{aproveitamento['gerados']} ativos gerados pela IA no período.",
                _grafico_ativos(aproveitamento), rodape)
