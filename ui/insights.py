"""Agregações da tela Insights, sem Streamlit e sem banco, para poderem ser testadas sozinhas.

Cada função recebe o DataFrame no formato de `consultar_interacoes` (ou `consultar_ativos`)
e devolve números ou tabelas prontas para os gráficos. Entrada vazia dá zeros ou tabela vazia
com as colunas, nunca divisão por zero.
"""
import pandas as pd

from ui.estilo import ROTAS

POSITIVOS = ("Positivo", "Altamente Positivo")
NEGATIVOS = ("Negativo", "Altamente Negativo")
ROTAS_GERADAS = ("case_sucesso", "faq", "alerta", "nenhuma")
# Da ponta negativa à positiva: a barra divergente empilha nesta ordem, com o neutro no meio.
ESCALA_SENTIMENTO = ("Altamente Negativo", "Negativo", "Neutro", "Positivo", "Altamente Positivo")


def _por_dia(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Mensagens por dia (a data em que foram escritas) e por `coluna`, somando todos os lotes daquele dia."""
    d = df.assign(data=pd.to_datetime(df["data"]))
    return (d.groupby(["data", coluna], as_index=False).size()
            .rename(columns={"size": "quantidade"})
            .sort_values(["data", coluna], kind="stable", ignore_index=True))


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


def sentimento_por_dia(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["data", "sentimento", "quantidade"])
    return _por_dia(df, "sentimento")


def sentimento_por_canal(df: pd.DataFrame) -> pd.DataFrame:
    colunas = ["canal", "sentimento", "quantidade", "percentual"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    s = df.groupby(["canal", "sentimento"], as_index=False).size().rename(columns={"size": "quantidade"})
    s["percentual"] = 100 * s["quantidade"] / s.groupby("canal")["quantidade"].transform("sum")
    return s[colunas]


def sentimento_divergente(df: pd.DataFrame) -> pd.DataFrame:
    """Segmentos da barra centrada no neutro: negativos à esquerda de 0, positivos à direita, neutro dividido ao meio."""
    colunas = ["canal", "sentimento", "percentual", "inicio", "fim"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    linhas = []
    for canal, grupo in df.groupby("canal"):
        pct = grupo["sentimento"].value_counts(normalize=True) * 100
        esquerda = -(pct.get("Altamente Negativo", 0) + pct.get("Negativo", 0) + pct.get("Neutro", 0) / 2)
        for sentimento in ESCALA_SENTIMENTO:
            p = float(pct.get(sentimento, 0))
            if p:
                linhas.append({"canal": canal, "sentimento": sentimento, "percentual": p,
                               "inicio": esquerda, "fim": esquerda + p})
                esquerda += p
    return pd.DataFrame(linhas, columns=colunas)


def resumo_por_canal(df: pd.DataFrame) -> pd.DataFrame:
    """% de positivas e de negativas por canal, do canal mais positivo (saldo) ao mais negativo."""
    colunas = ["canal", "pct_positivas", "pct_negativas"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    g = df.groupby("canal")["sentimento"]
    r = pd.DataFrame({"pct_positivas": g.apply(lambda s: 100 * s.isin(POSITIVOS).mean()),
                      "pct_negativas": g.apply(lambda s: 100 * s.isin(NEGATIVOS).mean())}).reset_index()
    saldo = r["pct_positivas"] - r["pct_negativas"]
    return r.assign(saldo=saldo).sort_values(["saldo", "canal"], ascending=[False, True], ignore_index=True)[colunas]


def topicos_mais_falados(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["topico", "quantidade"])
    t = df.groupby("topico", as_index=False).size().rename(columns={"size": "quantidade"})
    return t.sort_values(["quantidade", "topico"], ascending=[False, True], ignore_index=True).head(n)


def volume_por_canal(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["data", "canal", "quantidade"])
    return _por_dia(df, "canal")


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
