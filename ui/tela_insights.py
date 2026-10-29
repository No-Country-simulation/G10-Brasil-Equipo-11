"""Tela Insights do painel: o histórico das mensagens gravadas no Supabase, dia a dia, pela data de cada mensagem.

Lê só do banco (via `app.repositorio`), nunca de `st.session_state["resultado"]`.
As contas ficam em `ui/insights.py`; aqui só filtros e desenho.
"""
import math
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

from app import llm, repositorio
from ui import insights as ins
from ui.estilo import AZUL, AZUL_ESCURO, CINZA, ROTAS, SENTIMENTOS, TINTA

MODOS = {"Gemini": "gemini", "Simulado": "mock"}
SEMANAS_PADRAO = 8
MAX_ROTULOS_DIA = 16
NOMES_SENT = [nome for nome, _ in SENTIMENTOS]
ORDEM_SENT = {nome: i for i, nome in enumerate(NOMES_SENT)}
ESCALA_SENT = alt.Scale(domain=NOMES_SENT, range=[cor for _, cor in SENTIMENTOS])
# Na barra centrada no neutro a legenda segue a leitura da barra: do negativo (esquerda) ao positivo (direita).
ESCALA_SENT_DIVERGENTE = alt.Scale(domain=list(ins.ESCALA_SENTIMENTO),
                                   range=[dict(SENTIMENTOS)[s] for s in ins.ESCALA_SENTIMENTO])
ESTADOS_ATIVOS = [("Aprovados", "aprovados", AZUL), ("Descartados", "descartados", CINZA),
                  ("Pendentes", "pendentes", "#C3C8D1")]
EIXO_INTEIRO = alt.Axis(tickMinStep=1, format="d")


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
    hoje = repositorio.hoje()
    padrao = (hoje - timedelta(weeks=SEMANAS_PADRAO), hoje)
    c_com, c_per, c_can, c_modo = st.columns([3, 2, 3, 2], vertical_alignment="bottom")
    no_simulado = list(MODOS).index("Simulado") if llm.modo_mock() else 0  # começa no modo em que o app roda
    modo = MODOS[c_modo.radio("Modo", list(MODOS), index=no_simulado, key="ins_modo", horizontal=True)]
    opcoes = repositorio.opcoes_filtros(modo)
    comunidades = c_com.multiselect("Comunidade", opcoes["comunidades"], key="ins_comunidades", placeholder="Todas")
    inicio, fim = _periodo(c_per.date_input("Período", value=padrao, key="ins_periodo", format="DD/MM/YYYY"), padrao)
    canais = c_can.multiselect("Canal", opcoes["canais"], key="ins_canais", placeholder="Todos")
    return inicio, fim, modo, comunidades or None, canais or None


# ---------- Eixo de dias ----------
def _dias(df: pd.DataFrame, fim) -> list[str]:
    """Todos os dias, da primeira mensagem do período até o fim dele, inclusive os sem mensagem."""
    primeiro = pd.to_datetime(df["data"]).min()
    return [d.strftime("%d/%m") for d in pd.date_range(primeiro, max(pd.Timestamp(fim), primeiro))]


def _eixo_dia(dias: list[str]) -> alt.X:
    passo = math.ceil(len(dias) / MAX_ROTULOS_DIA)  # rótulo a cada `passo` dias, sempre centrado na barra
    return alt.X("dia:O", title=None, scale=alt.Scale(domain=dias, paddingInner=0.2),
                 axis=alt.Axis(values=dias[::passo], labelAngle=0))


def _com_dia(t: pd.DataFrame) -> pd.DataFrame:
    return t.assign(dia=pd.to_datetime(t["data"]).dt.strftime("%d/%m"),
                    data_longa=pd.to_datetime(t["data"]).dt.strftime("%d/%m/%Y"))


# ---------- Gráficos ----------
def _grafico_sentimento_por_dia(df: pd.DataFrame, dias: list[str]) -> alt.Chart:
    t = _com_dia(ins.sentimento_por_dia(df))
    t["ordem"] = t["sentimento"].map(ORDEM_SENT)
    return alt.Chart(t).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=_eixo_dia(dias),
        y=alt.Y("sum(quantidade):Q", title="Mensagens", axis=EIXO_INTEIRO),
        color=alt.Color("sentimento:N", scale=ESCALA_SENT, title="Sentimento",
                        legend=alt.Legend(orient="top", direction="horizontal")),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("data_longa:N", title="Dia"), alt.Tooltip("sentimento:N", title="Sentimento"),
                 alt.Tooltip("sum(quantidade):Q", title="Mensagens")],
    ).properties(height=280)


def _grafico_volume_por_canal(df: pd.DataFrame, dias: list[str]) -> alt.Chart:
    t = _com_dia(ins.volume_por_canal(df))
    canais = list(t.groupby("canal")["quantidade"].sum().sort_values(ascending=False).index)
    return alt.Chart(t).mark_rect(cornerRadius=2).encode(
        x=_eixo_dia(dias),
        y=alt.Y("canal:N", sort=canais, title=None, scale=alt.Scale(paddingInner=0.15), axis=alt.Axis(labelLimit=0)),
        # A escala parte de zero: 1 mensagem num mês calmo já aparece escura, em vez de num tom médio.
        color=alt.Color("quantidade:Q", title="Mensagens",
                        scale=alt.Scale(domainMin=0, range=["#E8EEFB", AZUL_ESCURO]),
                        legend=alt.Legend(format="d", tickMinStep=1, orient="top", direction="horizontal")),
        tooltip=[alt.Tooltip("data_longa:N", title="Dia"), alt.Tooltip("canal:N", title="Canal"),
                 alt.Tooltip("quantidade:Q", title="Mensagens")],
    ).properties(height=alt.Step(34))


def _grafico_sentimento_por_canal(df: pd.DataFrame) -> alt.LayerChart:
    t = ins.sentimento_divergente(df)
    resumo = ins.resumo_por_canal(df)
    canais = list(resumo["canal"])
    y = alt.Y("canal:N", sort=canais, title=None, axis=alt.Axis(labelLimit=0))
    barras = alt.Chart(t).mark_bar(height={"band": 0.7}).encode(
        y=y,
        x=alt.X("inicio:Q", title="← negativas · % das mensagens do canal · positivas →",
                scale=alt.Scale(domain=[-118, 118]),
                axis=alt.Axis(values=[-100, -50, 0, 50, 100], labelExpr="abs(datum.value) + '%'")),
        x2="fim:Q",
        color=alt.Color("sentimento:N", scale=ESCALA_SENT_DIVERGENTE, title="Sentimento",
                        legend=alt.Legend(orient="top", direction="horizontal")),
        tooltip=[alt.Tooltip("canal:N", title="Canal"), alt.Tooltip("sentimento:N", title="Sentimento"),
                 alt.Tooltip("percentual:Q", title="%", format=".1f")],
    )
    centro = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=TINTA, strokeWidth=1).encode(x="x:Q")
    rotulos = resumo.assign(neg=resumo["pct_negativas"].map(lambda v: f"{v:.0f}%"),
                            pos=resumo["pct_positivas"].map(lambda v: f"{v:.0f}%"), x_neg=-110, x_pos=110)
    base = alt.Chart(rotulos).encode(y=y)
    negativos = base.mark_text(color=TINTA, fontSize=12).encode(x="x_neg:Q", text="neg:N")
    positivos = base.mark_text(color=TINTA, fontSize=12).encode(x="x_pos:Q", text="pos:N")
    return alt.layer(barras, centro, negativos, positivos).properties(height=alt.Step(40))


def _grafico_topicos(df: pd.DataFrame) -> alt.LayerChart:
    t = ins.topicos_mais_falados(df)
    base = alt.Chart(t).encode(y=alt.Y("topico:N", sort=list(t["topico"]), title=None, axis=alt.Axis(labelLimit=0)),
                               x=alt.X("quantidade:Q", title="Mensagens", axis=EIXO_INTEIRO))
    barras = base.mark_bar(color=AZUL, cornerRadiusTopRight=3, cornerRadiusBottomRight=3, height={"band": 0.7}).encode(
        tooltip=[alt.Tooltip("topico:N", title="Tópico"), alt.Tooltip("quantidade:Q", title="Mensagens")])
    valores = base.mark_text(align="left", dx=6, color=TINTA, fontSize=12).encode(text="quantidade:Q")
    return alt.layer(barras, valores).properties(height=alt.Step(34))


def _rosca(t: pd.DataFrame, cores: list[str], total: int, rotulo_total: str) -> alt.LayerChart:
    """Rosca com o total no centro. `t` tem nome e quantidade, na ordem das fatias; a legenda traz número e %."""
    soma = max(int(t["quantidade"].sum()), 1)
    t = t.assign(legenda=[f"{n} · {q} ({round(100 * q / soma)}%)" for n, q in zip(t["nome"], t["quantidade"])],
                 ordem=range(len(t)))
    fatias = alt.Chart(t).mark_arc(innerRadius=72, outerRadius=118, padAngle=0.012, cornerRadius=3).encode(
        theta=alt.Theta("quantidade:Q", stack=True),
        color=alt.Color("legenda:N", scale=alt.Scale(domain=list(t["legenda"]), range=cores), title=None,
                        legend=alt.Legend(orient="right", labelFontSize=13, symbolType="circle")),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("nome:N", title="Categoria"), alt.Tooltip("quantidade:Q", title="Quantidade")],
    )
    meio = {"x": {"expr": "width / 2"}, "y": {"expr": "height / 2"}, "color": TINTA}
    numero = alt.Chart(pd.DataFrame({"t": [str(total)]})).mark_text(**meio, dy=-8, fontSize=30,
                                                                     fontWeight="bold").encode(text="t:N")
    rotulo = alt.Chart(pd.DataFrame({"t": [rotulo_total]})).mark_text(**meio, dy=18, fontSize=13).encode(text="t:N")
    return alt.layer(fatias, numero, rotulo).properties(height=260)


def _grafico_rotas(df: pd.DataFrame) -> alt.LayerChart:
    t = ins.rotas_geradas(df)
    return _rosca(t, [ROTAS[r]["barra"] for r in t["rota"]], len(df), "mensagens")


def _grafico_ativos(numeros: dict) -> alt.LayerChart:
    t = pd.DataFrame({"nome": [n for n, _, _ in ESTADOS_ATIVOS], "quantidade": [numeros[c] for _, c, _ in ESTADOS_ATIVOS]})
    return _rosca(t, [c for _, _, c in ESTADOS_ATIVOS], numeros["gerados"], "conteúdos")


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
    st.markdown('<p class="cl-sub">Como a comunidade evoluiu dia a dia, pela data de cada mensagem.</p>',
                unsafe_allow_html=True)
    try:
        inicio, fim, modo, comunidades, canais = _filtros()
        df = repositorio.consultar_interacoes(inicio, fim, modo, comunidades=comunidades, canais=canais)
        ativos = repositorio.consultar_ativos(inicio, fim, modo, comunidades=comunidades, canais=canais)
    except Exception as e:
        st.warning(f"Não foi possível consultar o histórico: {e}")
        return
    st.caption("Cada número conta mensagens, não pessoas. O período segue a data em que cada mensagem foi escrita.")
    if df.empty:
        st.info("Nenhuma mensagem nesse período com esses filtros.")
        return

    n = ins.numeros_periodo(df)
    k1, k2, k3, k4 = st.columns(4)
    for coluna, rotulo, valor in ((k1, "Interações", n["total"]), (k2, "Positivas", _pct(n["pct_positivas"])),
                                  (k3, "Negativas", _pct(n["pct_negativas"])), (k4, "Alertas", n["alertas"])):
        with coluna.container(border=True):
            st.metric(rotulo, valor)

    dias = _dias(df, fim)
    _quadro("Sentimento por dia", "Mensagens escritas em cada dia, por sentimento.",
            _grafico_sentimento_por_dia(df, dias))
    _quadro("Volume por canal", "Mensagens de cada canal, dia a dia. Quanto mais escuro, mais mensagens.",
            _grafico_volume_por_canal(df, dias))
    _quadro("Sentimento por canal", "Negativas à esquerda, positivas à direita, o neutro dividido ao meio. "
            "Canais do mais positivo ao mais negativo.", _grafico_sentimento_por_canal(df))
    _quadro("Tópicos mais falados", "Os 10 tópicos com mais mensagens no período.", _grafico_topicos(df))
    a, b = st.columns(2)
    with a:
        _quadro("Rotas geradas", "O que aconteceu com cada mensagem.", _grafico_rotas(df))
    with b:
        aproveitamento = ins.aproveitamento_ativos(ativos)
        rodape = "A newsletter não tem canal de origem e fica de fora com o filtro de canal." if canais else None
        _quadro("Aproveitamento dos conteúdos", "Conteúdos gerados pela IA no período, pela decisão da equipe.",
                _grafico_ativos(aproveitamento), rodape)
