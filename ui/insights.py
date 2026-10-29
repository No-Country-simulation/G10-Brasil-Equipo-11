"""Agregações da tela Insights, sem Streamlit e sem banco, para poderem ser testadas sozinhas.

Cada função recebe o DataFrame no formato de `consultar_interacoes` (ou `consultar_ativos`)
e devolve números ou tabelas prontas para os gráficos. Entrada vazia dá zeros ou tabela vazia
com as colunas, nunca divisão por zero.
"""
import pandas as pd

from ui.estilo import ROTAS

FUSO = "America/Sao_Paulo"
POSITIVOS = ("Positivo", "Altamente Positivo")
NEGATIVOS = ("Negativo", "Altamente Negativo")
ROTAS_GERADAS = ("case_sucesso", "faq", "alerta")


def _com_rotulo(df: pd.DataFrame) -> pd.DataFrame:
    """Cópia com `processado_em` em UTC e `rotulo` ("dd/mm HH:MM · período") no fuso local."""
    d = df.copy()
    d["processado_em"] = pd.to_datetime(d["processado_em"], utc=True)
    local = d["processado_em"].dt.tz_convert(FUSO).dt.strftime("%d/%m %H:%M")
    d["rotulo"] = local + " · " + d["periodo_referencia"].astype(str)
    return d


def numeros_periodo(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {"total": 0, "pct_positivas": 0.0, "pct_negativas": 0.0, "alertas": 0}
    return {
        "total": total,
        "pct_positivas": round(100 * df["sentimento"].isin(POSITIVOS).sum() / total, 1),
        "pct_negativas": round(100 * df["sentimento"].isin(NEGATIVOS).sum() / total, 1),
        "alertas": int((df["rota"] == "alerta").sum()),
    }


def sentimento_por_lote(df: pd.DataFrame) -> pd.DataFrame:
    colunas = ["lote_id", "processado_em", "rotulo", "sentimento", "quantidade"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    d = _com_rotulo(df)
    return (d.groupby(["lote_id", "processado_em", "rotulo", "sentimento"], as_index=False).size()
            .rename(columns={"size": "quantidade"})
            .sort_values(["processado_em", "lote_id"], kind="stable", ignore_index=True)[colunas])


def sentimento_por_canal(df: pd.DataFrame) -> pd.DataFrame:
    colunas = ["canal", "sentimento", "quantidade", "percentual"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    s = df.groupby(["canal", "sentimento"], as_index=False).size().rename(columns={"size": "quantidade"})
    s["percentual"] = 100 * s["quantidade"] / s.groupby("canal")["quantidade"].transform("sum")
    return s[colunas]


def topicos_mais_falados(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["topico", "quantidade"])
    t = df.groupby("topico", as_index=False).size().rename(columns={"size": "quantidade"})
    return t.sort_values(["quantidade", "topico"], ascending=[False, True], ignore_index=True).head(n)


def volume_por_canal(df: pd.DataFrame) -> pd.DataFrame:
    colunas = ["processado_em", "rotulo", "canal", "quantidade"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    d = _com_rotulo(df)
    return (d.groupby(["lote_id", "processado_em", "rotulo", "canal"], as_index=False).size()
            .rename(columns={"size": "quantidade"})
            .sort_values(["processado_em", "lote_id", "canal"], kind="stable", ignore_index=True)[colunas])


def rotas_geradas(df: pd.DataFrame) -> pd.DataFrame:
    contagem = df["rota"].value_counts() if len(df) else pd.Series(dtype=int)
    return pd.DataFrame({
        "rota": list(ROTAS_GERADAS),
        "nome": [ROTAS[r]["nome"] for r in ROTAS_GERADAS],
        "quantidade": [int(contagem.get(r, 0)) for r in ROTAS_GERADAS],
    })


def aproveitamento_ativos(ativos: pd.DataFrame) -> dict:
    status = ativos["status"] if len(ativos) else pd.Series(dtype=object)
    return {
        "gerados": len(ativos),
        "aprovados": int((status == "aprovado").sum()),
        "descartados": int((status == "descartado").sum()),
        "pendentes": int((status == "pendente").sum()),
    }
