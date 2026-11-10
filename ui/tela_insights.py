"""Tela de Insights alimentada pela API Oracle do CommunityLab."""

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from app.api_client import (
    APIClientError,
    request as api_request,
)
from app.llm import modo_mock
from ui import insights as ins
from ui.estilo import (
    AZUL,
    AZUL_ESCURO,
    CINZA,
    ROTAS,
    SENTIMENTOS,
    TINTA,
)


MODOS = {
    "Gemini": "gemini",
    "Simulado": "mock",
}

SEMANAS_PADRAO = 8
MAX_ROTULOS_DIA = 16

COLUNAS_INTERACOES = [
    "lote_id",
    "data",
    "comunidade",
    "canal",
    "sentimento",
    "topico",
    "rota",
]

COLUNAS_ATIVOS = [
    "lote_id",
    "chave",
    "tipo",
    "status",
]

NOMES_SENT = [
    nome for nome, _ in SENTIMENTOS
]

ORDEM_SENT = {
    nome: indice
    for indice, nome in enumerate(NOMES_SENT)
}

ESCALA_SENT = alt.Scale(
    domain=NOMES_SENT,
    range=[cor for _, cor in SENTIMENTOS],
)

ESCALA_SENT_DIVERGENTE = alt.Scale(
    domain=list(ins.ESCALA_SENTIMENTO),
    range=[
        dict(SENTIMENTOS)[sentimento]
        for sentimento in ins.ESCALA_SENTIMENTO
    ],
)

ESTADOS_ATIVOS = [
    ("Aprovados", "aprovados", AZUL),
    ("Descartados", "descartados", CINZA),
    ("Pendentes", "pendentes", "#C3C8D1"),
]

EIXO_INTEIRO = alt.Axis(
    tickMinStep=1,
    format="d",
)


def _pct(valor: float) -> str:
    return f"{valor:.1f}%".replace(".", ",")


def _hoje() -> date:
    return datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).date()


def _periodo(valor, padrao: tuple) -> tuple:
    """Normaliza o retorno do date_input."""
    datas = (
        tuple(valor)
        if isinstance(valor, (tuple, list))
        else (valor,)
    )

    datas = tuple(
        data for data in datas
        if data is not None
    )

    if not datas:
        return padrao

    if len(datas) == 1:
        return datas[0], datas[0]

    return datas[0], datas[-1]


def _filtros():
    """Desenha os filtros e consulta as opções pela API."""
    hoje = _hoje()

    padrao = (
        hoje - timedelta(weeks=SEMANAS_PADRAO),
        hoje,
    )

    c_com, c_per, c_can, c_modo = st.columns(
        [3, 2, 3, 2],
        vertical_alignment="bottom",
    )

    indice_modo = (
        1 if modo_mock() else 0
    )

    modo = MODOS[
        c_modo.radio(
            "Modo",
            list(MODOS),
            index=indice_modo,
            key="ins_modo",
            horizontal=True,
        )
    ]

    opcoes = api_request(
        "GET",
        "/insights/opcoes",
        params={"modo": modo},
    )

    comunidades = c_com.multiselect(
        "Comunidade",
        opcoes.get("comunidades", []),
        key="ins_comunidades",
        placeholder="Todas",
    )

    inicio, fim = _periodo(
        c_per.date_input(
            "Período",
            value=padrao,
            key="ins_periodo",
            format="DD/MM/YYYY",
        ),
        padrao,
    )

    canais = c_can.multiselect(
        "Canal",
        opcoes.get("canais", []),
        key="ins_canais",
        placeholder="Todos",
    )

    return (
        inicio,
        fim,
        modo,
        comunidades or None,
        canais or None,
    )


def _parametros_consulta(
    inicio: date,
    fim: date,
    modo: str,
    comunidades: list[str] | None,
    canais: list[str] | None,
) -> dict:
    """Monta parâmetros para os endpoints de Insights."""
    params = {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "modo": modo,
    }

    if comunidades:
        params["comunidades"] = comunidades

    if canais:
        params["canais"] = canais

    return params


def _consultar_dados(
    inicio: date,
    fim: date,
    modo: str,
    comunidades: list[str] | None,
    canais: list[str] | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Busca interações e ativos exclusivamente pela API."""
    params = _parametros_consulta(
        inicio,
        fim,
        modo,
        comunidades,
        canais,
    )

    resposta_interacoes = api_request(
        "GET",
        "/insights/interacoes",
        params=params,
    )

    resposta_ativos = api_request(
        "GET",
        "/insights/ativos",
        params=params,
    )

    df = pd.DataFrame(
        resposta_interacoes.get("items", []),
        columns=COLUNAS_INTERACOES,
    )

    ativos = pd.DataFrame(
        resposta_ativos.get("items", []),
        columns=COLUNAS_ATIVOS,
    )

    if not df.empty:
        df["data"] = pd.to_datetime(
            df["data"],
            errors="raise",
        )

    return df, ativos


# ---------------------------------------------------------------------------
# Eixo de dias
# ---------------------------------------------------------------------------

def _dias(
    df: pd.DataFrame,
    fim: date,
) -> list[str]:
    primeiro = pd.to_datetime(
        df["data"]
    ).min()

    ultimo = max(
        pd.Timestamp(fim),
        primeiro,
    )

    return [
        dia.strftime("%d/%m")
        for dia in pd.date_range(
            primeiro,
            ultimo,
        )
    ]


def _eixo_dia(dias: list[str]) -> alt.X:
    passo = max(
        1,
        math.ceil(len(dias) / MAX_ROTULOS_DIA),
    )

    return alt.X(
        "dia:O",
        title=None,
        scale=alt.Scale(
            domain=dias,
            paddingInner=0.2,
        ),
        axis=alt.Axis(
            values=dias[::passo],
            labelAngle=0,
        ),
    )


def _com_dia(tabela: pd.DataFrame) -> pd.DataFrame:
    datas = pd.to_datetime(tabela["data"])

    return tabela.assign(
        dia=datas.dt.strftime("%d/%m"),
        data_longa=datas.dt.strftime("%d/%m/%Y"),
    )


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def _grafico_sentimento_por_dia(
    df: pd.DataFrame,
    dias: list[str],
) -> alt.Chart:
    tabela = _com_dia(
        ins.sentimento_por_dia(df)
    )

    tabela["ordem"] = tabela[
        "sentimento"
    ].map(ORDEM_SENT)

    return (
        alt.Chart(tabela)
        .mark_bar(
            cornerRadiusTopLeft=2,
            cornerRadiusTopRight=2,
        )
        .encode(
            x=_eixo_dia(dias),
            y=alt.Y(
                "sum(quantidade):Q",
                title="Mensagens",
                axis=EIXO_INTEIRO,
            ),
            color=alt.Color(
                "sentimento:N",
                scale=ESCALA_SENT,
                title="Sentimento",
                legend=alt.Legend(
                    orient="top",
                    direction="horizontal",
                ),
            ),
            order=alt.Order("ordem:Q"),
            tooltip=[
                alt.Tooltip(
                    "data_longa:N",
                    title="Dia",
                ),
                alt.Tooltip(
                    "sentimento:N",
                    title="Sentimento",
                ),
                alt.Tooltip(
                    "sum(quantidade):Q",
                    title="Mensagens",
                ),
            ],
        )
        .properties(height=280)
    )


def _grafico_volume_por_canal(
    df: pd.DataFrame,
    dias: list[str],
) -> alt.Chart:
    tabela = _com_dia(
        ins.volume_por_canal(df)
    )

    canais = list(
        tabela.groupby("canal")["quantidade"]
        .sum()
        .sort_values(ascending=False)
        .index
    )

    return (
        alt.Chart(tabela)
        .mark_rect(cornerRadius=2)
        .encode(
            x=_eixo_dia(dias),
            y=alt.Y(
                "canal:N",
                sort=canais,
                title=None,
                scale=alt.Scale(paddingInner=0.15),
                axis=alt.Axis(labelLimit=0),
            ),
            color=alt.Color(
                "quantidade:Q",
                title="Mensagens",
                scale=alt.Scale(
                    domainMin=0,
                    range=["#E8EEFB", AZUL_ESCURO],
                ),
                legend=alt.Legend(
                    format="d",
                    tickMinStep=1,
                    orient="top",
                    direction="horizontal",
                ),
            ),
            tooltip=[
                alt.Tooltip("data_longa:N", title="Dia"),
                alt.Tooltip("canal:N", title="Canal"),
                alt.Tooltip(
                    "quantidade:Q",
                    title="Mensagens",
                ),
            ],
        )
        .properties(height=alt.Step(34))
    )


def _grafico_sentimento_por_canal(
    df: pd.DataFrame,
) -> alt.LayerChart:
    tabela = ins.sentimento_divergente(df)
    resumo = ins.resumo_por_canal(df)

    canais = list(resumo["canal"])

    eixo_y = alt.Y(
        "canal:N",
        sort=canais,
        title=None,
        axis=alt.Axis(labelLimit=0),
    )

    barras = (
        alt.Chart(tabela)
        .mark_bar(height={"band": 0.7})
        .encode(
            y=eixo_y,
            x=alt.X(
                "inicio:Q",
                title="← negativas · % das mensagens · positivas →",
                scale=alt.Scale(domain=[-118, 118]),
                axis=alt.Axis(
                    values=[-100, -50, 0, 50, 100],
                    labelExpr="abs(datum.value) + '%'",
                ),
            ),
            x2="fim:Q",
            color=alt.Color(
                "sentimento:N",
                scale=ESCALA_SENT_DIVERGENTE,
                title="Sentimento",
                legend=alt.Legend(
                    orient="top",
                    direction="horizontal",
                ),
            ),
            tooltip=[
                alt.Tooltip("canal:N", title="Canal"),
                alt.Tooltip(
                    "sentimento:N",
                    title="Sentimento",
                ),
                alt.Tooltip(
                    "percentual:Q",
                    title="%",
                    format=".1f",
                ),
            ],
        )
    )

    centro = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(
            color=TINTA,
            strokeWidth=1,
        )
        .encode(x="x:Q")
    )

    rotulos = resumo.assign(
        neg=resumo["pct_negativas"].map(
            lambda valor: f"{valor:.0f}%"
        ),
        pos=resumo["pct_positivas"].map(
            lambda valor: f"{valor:.0f}%"
        ),
        x_neg=-110,
        x_pos=110,
    )

    base = alt.Chart(rotulos).encode(y=eixo_y)

    negativos = (
        base.mark_text(
            color=TINTA,
            fontSize=12,
        )
        .encode(
            x="x_neg:Q",
            text="neg:N",
        )
    )

    positivos = (
        base.mark_text(
            color=TINTA,
            fontSize=12,
        )
        .encode(
            x="x_pos:Q",
            text="pos:N",
        )
    )

    return alt.layer(
        barras,
        centro,
        negativos,
        positivos,
    ).properties(height=alt.Step(40))


def _grafico_topicos(
    df: pd.DataFrame,
) -> alt.LayerChart:
    tabela = ins.topicos_mais_falados(df)

    base = alt.Chart(tabela).encode(
        y=alt.Y(
            "topico:N",
            sort=list(tabela["topico"]),
            title=None,
            axis=alt.Axis(labelLimit=0),
        ),
        x=alt.X(
            "quantidade:Q",
            title="Mensagens",
            axis=EIXO_INTEIRO,
        ),
    )

    barras = (
        base.mark_bar(
            color=AZUL,
            cornerRadiusTopRight=3,
            cornerRadiusBottomRight=3,
            height={"band": 0.7},
        )
        .encode(
            tooltip=[
                alt.Tooltip("topico:N", title="Tópico"),
                alt.Tooltip(
                    "quantidade:Q",
                    title="Mensagens",
                ),
            ]
        )
    )

    valores = (
        base.mark_text(
            align="left",
            dx=6,
            color=TINTA,
            fontSize=12,
        )
        .encode(text="quantidade:Q")
    )

    return alt.layer(
        barras,
        valores,
    ).properties(height=alt.Step(34))


def _rosca(
    tabela: pd.DataFrame,
    cores: list[str],
    total: int,
    rotulo_total: str,
) -> alt.LayerChart:
    soma = max(
        int(tabela["quantidade"].sum()),
        1,
    )

    tabela = tabela.assign(
        legenda=[
            f"{nome} · {quantidade} "
            f"({round(100 * quantidade / soma)}%)"
            for nome, quantidade in zip(
                tabela["nome"],
                tabela["quantidade"],
            )
        ],
        ordem=range(len(tabela)),
    )

    fatias = (
        alt.Chart(tabela)
        .mark_arc(
            innerRadius=72,
            outerRadius=118,
            padAngle=0.012,
            cornerRadius=3,
        )
        .encode(
            theta=alt.Theta(
                "quantidade:Q",
                stack=True,
            ),
            color=alt.Color(
                "legenda:N",
                scale=alt.Scale(
                    domain=list(tabela["legenda"]),
                    range=cores,
                ),
                title=None,
                legend=alt.Legend(
                    orient="right",
                    labelFontSize=13,
                    symbolType="circle",
                ),
            ),
            order=alt.Order("ordem:Q"),
            tooltip=[
                alt.Tooltip("nome:N", title="Categoria"),
                alt.Tooltip(
                    "quantidade:Q",
                    title="Quantidade",
                ),
            ],
        )
    )

    meio = {
        "x": {"expr": "width / 2"},
        "y": {"expr": "height / 2"},
        "color": TINTA,
    }

    numero = (
        alt.Chart(pd.DataFrame({"t": [str(total)]}))
        .mark_text(
            **meio,
            dy=-8,
            fontSize=30,
            fontWeight="bold",
        )
        .encode(text="t:N")
    )

    rotulo = (
        alt.Chart(pd.DataFrame({"t": [rotulo_total]}))
        .mark_text(
            **meio,
            dy=18,
            fontSize=13,
        )
        .encode(text="t:N")
    )

    return alt.layer(
        fatias,
        numero,
        rotulo,
    ).properties(height=260)


def _grafico_rotas(
    df: pd.DataFrame,
) -> alt.LayerChart:
    tabela = ins.rotas_geradas(df)

    return _rosca(
        tabela,
        [ROTAS[rota]["barra"] for rota in tabela["rota"]],
        len(df),
        "mensagens",
    )


def _grafico_ativos(
    numeros: dict,
) -> alt.LayerChart:
    tabela = pd.DataFrame({
        "nome": [
            nome
            for nome, _, _ in ESTADOS_ATIVOS
        ],
        "quantidade": [
            numeros[chave]
            for _, chave, _ in ESTADOS_ATIVOS
        ],
    })

    return _rosca(
        tabela,
        [cor for _, _, cor in ESTADOS_ATIVOS],
        numeros["gerados"],
        "conteúdos",
    )


def _quadro(
    titulo: str,
    legenda: str,
    grafico: alt.Chart,
    rodape: str | None = None,
):
    with st.container(border=True):
        st.subheader(titulo)
        st.caption(legenda)
        st.altair_chart(
            grafico,
            width="stretch",
        )

        if rodape:
            st.caption(rodape)


# ---------------------------------------------------------------------------
# Tela principal
# ---------------------------------------------------------------------------

def tela_insights() -> None:
    st.title("Insights")

    st.markdown(
        '<p class="cl-sub">'
        "Como a comunidade evoluiu dia a dia, "
        "pela data de cada mensagem."
        "</p>",
        unsafe_allow_html=True,
    )

    try:
        inicio, fim, modo, comunidades, canais = _filtros()

        if inicio > fim:
            st.warning(
                "A data inicial não pode ser posterior à data final."
            )
            return

        df, ativos = _consultar_dados(
            inicio,
            fim,
            modo,
            comunidades,
            canais,
        )

    except APIClientError as exc:
        st.warning(
            "Não foi possível consultar os Insights pela API: "
            f"{exc}"
        )
        return

    except Exception as exc:
        st.exception(exc)
        return

    st.caption(
        "Cada número conta mensagens, não pessoas. "
        "O período segue a data original de cada mensagem."
    )

    if df.empty:
        st.info(
            "Nenhuma mensagem encontrada nesse período "
            "com os filtros selecionados."
        )
        return

    numeros = ins.numeros_periodo(df)

    k1, k2, k3, k4 = st.columns(4)

    indicadores = (
        (k1, "Interações", numeros["total"]),
        (k2, "Positivas", _pct(numeros["pct_positivas"])),
        (k3, "Negativas", _pct(numeros["pct_negativas"])),
        (k4, "Alertas", numeros["alertas"]),
    )

    for coluna, rotulo, valor in indicadores:
        with coluna.container(border=True):
            st.metric(rotulo, valor)

    dias = _dias(df, fim)

    _quadro(
        "Sentimento por dia",
        "Mensagens escritas em cada dia, por sentimento.",
        _grafico_sentimento_por_dia(df, dias),
    )

    _quadro(
        "Volume por canal",
        "Mensagens de cada canal, dia a dia. "
        "Quanto mais escuro, maior o volume.",
        _grafico_volume_por_canal(df, dias),
    )

    _quadro(
        "Sentimento por canal",
        "Negativas à esquerda, positivas à direita "
        "e neutras distribuídas ao redor do centro.",
        _grafico_sentimento_por_canal(df),
    )

    _quadro(
        "Tópicos mais falados",
        "Os 10 tópicos com mais mensagens no período.",
        _grafico_topicos(df),
    )

    a, b = st.columns(2)

    with a:
        _quadro(
            "Rotas geradas",
            "O que aconteceu com cada mensagem.",
            _grafico_rotas(df),
        )

    with b:
        aproveitamento = ins.aproveitamento_ativos(ativos)

        rodape = (
            "Cada conteúdo é contado uma vez. "
            "Com filtro de canal, entram os conteúdos "
            "que possuem ao menos uma interação de origem "
            "naquele canal."
            if canais
            else None
        )

        _quadro(
            "Aproveitamento dos conteúdos",
            "Conteúdos gerados pela IA no período, "
            "conforme a decisão da equipe.",
            _grafico_ativos(aproveitamento),
            rodape,
        )