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


# ---------------------------------------------------------------------------
# Painel web: agregações prontas para os gráficos (JSON simples, sem DataFrame)
# ---------------------------------------------------------------------------
NOMES_TIPO_ATIVO = {"post_linkedin": "Post LinkedIn", "newsletter": "Newsletter", "faq": "FAQ"}
ESTADOS_ALERTA = ("PENDENTE", "ENCAMINHADO", "RESOLVIDO")
ANONIMOS = {"", "anônimo", "anonimo", "anonymous", "desconhecido"}
LIMITE_DIAS_POR_DIA = 45  # a partir disso o eixo do tempo passa a ser por semana
MAX_CANAIS_HEATMAP = 8


def _datas(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["data"]).dt.normalize()


def granularidade(df: pd.DataFrame) -> str:
    if df.empty:
        return "dia"
    d = _datas(df)
    return "dia" if (d.max() - d.min()).days < LIMITE_DIAS_POR_DIA else "semana"


def _baldes(df: pd.DataFrame, grao: str) -> tuple[pd.Series, list[pd.Timestamp]]:
    """Início do balde (dia ou segunda-feira da semana) de cada linha e a lista contínua de baldes,
    incluindo os vazios, para o eixo do tempo não esconder dias sem mensagem."""
    d = _datas(df)
    if grao == "semana":
        d = d - pd.to_timedelta(d.dt.weekday, unit="D")
    passo = "7D" if grao == "semana" else "D"
    return d, list(pd.date_range(d.min(), d.max(), freq=passo))


def _rotulo(inicio: pd.Timestamp, grao: str) -> str:
    return ("sem. " if grao == "semana" else "") + inicio.strftime("%d/%m")


def resumo(df: pd.DataFrame, ativos: pd.DataFrame, alertas: list[dict]) -> dict:
    total = len(df)
    pos = int(df["sentimento"].isin(POSITIVOS).sum()) if total else 0
    neg = int(df["sentimento"].isin(NEGATIVOS).sum()) if total else 0
    status = ativos["status"] if len(ativos) else pd.Series(dtype=object)
    gerados, aprovados = len(ativos), int((status == "aprovado").sum())
    return {
        "interacoes": total,
        "lotes": int(df["lote_id"].nunique()) if total else 0,
        "canais": int(df["canal"].nunique()) if total else 0,
        "pct_positivas": round(100 * pos / total, 1) if total else 0.0,
        "pct_negativas": round(100 * neg / total, 1) if total else 0.0,
        "saldo": round(100 * (pos - neg) / total, 1) if total else 0.0,
        "alertas_total": len(alertas),
        "alertas_abertos": sum(1 for a in alertas if a.get("status") == "PENDENTE"),
        "ativos_gerados": gerados,
        "ativos_aprovados": aprovados,
        "ativos_pendentes": int((status == "pendente").sum()),
        "taxa_aprovacao": round(100 * aprovados / gerados, 1) if gerados else 0.0,
    }


def _contagens(serie: pd.Series) -> dict:
    vc = serie.value_counts()
    return {nivel: int(vc.get(nivel, 0)) for nivel in ESCALA_SENTIMENTO}


def sentimento_no_tempo(df: pd.DataFrame) -> dict:
    grao = granularidade(df)
    if df.empty:
        return {"granularidade": grao, "pontos": []}
    baldes, eixo = _baldes(df, grao)
    grupos = df.assign(_balde=baldes.values).groupby("_balde")["sentimento"]
    por_balde = {k: _contagens(v) for k, v in grupos}
    vazio = {nivel: 0 for nivel in ESCALA_SENTIMENTO}
    pontos = []
    for inicio in eixo:
        c = por_balde.get(inicio, vazio)
        pontos.append({"inicio": inicio.date().isoformat(), "rotulo": _rotulo(inicio, grao),
                       "total": sum(c.values()), "contagens": c})
    return {"granularidade": grao, "pontos": pontos}


def canais_sentimento(df: pd.DataFrame) -> list[dict]:
    """Por canal: contagens e % de cada nível e o saldo (positivas menos negativas). Do mais crítico ao melhor."""
    if df.empty:
        return []
    linhas = []
    for canal, grupo in df.groupby("canal"):
        c = _contagens(grupo["sentimento"])
        total = len(grupo)
        pct = {k: round(100 * v / total, 1) for k, v in c.items()}
        saldo = round(pct["Positivo"] + pct["Altamente Positivo"] - pct["Negativo"] - pct["Altamente Negativo"], 1)
        linhas.append({"canal": canal, "total": total, "contagens": c, "percentuais": pct, "saldo": saldo})
    return sorted(linhas, key=lambda x: (x["saldo"], -x["total"], x["canal"]))


def topicos_tom(df: pd.DataFrame, n: int = 10) -> list[dict]:
    """Os tópicos mais falados com a divisão negativas / neutras / positivas de cada um."""
    if df.empty:
        return []
    linhas = []
    for topico, grupo in df.groupby("topico"):
        s = grupo["sentimento"]
        linhas.append({"topico": topico, "total": len(grupo),
                       "negativos": int(s.isin(NEGATIVOS).sum()),
                       "neutros": int((s == "Neutro").sum()),
                       "positivos": int(s.isin(POSITIVOS).sum())})
    return sorted(linhas, key=lambda x: (-x["total"], x["topico"]))[:n]


def atividade_canal_tempo(df: pd.DataFrame) -> dict:
    """Mensagens por canal em cada dia (ou semana). Canais além do limite somam em "Outros"."""
    grao = granularidade(df)
    if df.empty:
        return {"granularidade": grao, "colunas": [], "linhas": [], "maximo": 0}
    baldes, eixo = _baldes(df, grao)
    d = df.assign(_balde=baldes.values)
    ordem = d["canal"].value_counts()
    excede = len(ordem) > MAX_CANAIS_HEATMAP
    principais = list(ordem.index[:MAX_CANAIS_HEATMAP - 1]) if excede else list(ordem.index)
    d["_canal"] = d["canal"].where(d["canal"].isin(principais), "Outros")
    tabela = d.groupby(["_canal", "_balde"]).size()
    nomes = principais + (["Outros"] if excede else [])
    linhas = []
    for nome in nomes:
        valores = [int(tabela.get((nome, b), 0)) for b in eixo]
        linhas.append({"canal": nome, "total": sum(valores), "valores": valores})
    return {
        "granularidade": grao,
        "colunas": [{"inicio": b.date().isoformat(), "rotulo": _rotulo(b, grao)} for b in eixo],
        "linhas": linhas,
        "maximo": max((v for linha in linhas for v in linha["valores"]), default=0),
    }


def aproveitamento_por_tipo(ativos: pd.DataFrame) -> list[dict]:
    if ativos.empty:
        return []
    a = ativos.assign(_tipo=ativos["tipo"].astype(str).str.lower())
    linhas = []
    for tipo, nome in NOMES_TIPO_ATIVO.items():
        grupo = a[a["_tipo"] == tipo]
        if grupo.empty:
            continue
        status = grupo["status"]
        linhas.append({"tipo": tipo, "nome": nome, "total": len(grupo),
                       "aprovados": int((status == "aprovado").sum()),
                       "pendentes": int((status == "pendente").sum()),
                       "descartados": int((status == "descartado").sum())})
    return linhas


def alertas_triagem(alertas: list[dict], limite: int = 8) -> dict:
    """Quantos alertas há em cada estado e os abertos mais antigos (a fila de cuidado)."""
    contagem = {estado: sum(1 for a in alertas if a.get("status") == estado) for estado in ESTADOS_ALERTA}
    abertos = sorted((a for a in alertas if a.get("status") == "PENDENTE"),
                     key=lambda a: (str(a.get("data") or ""), str(a.get("criado_em") or "")))
    return {
        "total": len(alertas),
        "por_estado": contagem,
        "abertos": [{
            "lote_id": a.get("lote_id"),
            "data": str(a.get("data"))[:10] if a.get("data") else None,
            "canal": a.get("canal"),
            "autor": a.get("autor"),
            "motivo": (a.get("motivo") or "")[:180],
        } for a in abertos[:limite]],
        "abertos_restantes": max(0, len(abertos) - limite),
    }


def membros_engajados(df: pd.DataFrame, n: int = 8) -> list[dict]:
    """Quem mais escreveu no período, com quantas mensagens positivas, negativas e cases de sucesso."""
    if df.empty or "autor" not in df.columns:
        return []
    d = df[~df["autor"].fillna("").astype(str).str.strip().str.lower().isin(ANONIMOS)]
    linhas = []
    for autor, grupo in d.groupby("autor"):
        s = grupo["sentimento"]
        linhas.append({"autor": autor, "total": len(grupo),
                       "positivos": int(s.isin(POSITIVOS).sum()),
                       "negativos": int(s.isin(NEGATIVOS).sum()),
                       "cases": int((grupo["rota"] == "case_sucesso").sum())})
    return sorted(linhas, key=lambda x: (-x["total"], -x["positivos"], x["autor"]))[:n]
