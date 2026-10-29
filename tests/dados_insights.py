"""Dados montados à mão para os testes das agregações de Insights."""
import pandas as pd

COLUNAS = ["lote_id", "processado_em", "periodo_referencia", "comunidade", "canal", "sentimento", "topico", "rota"]


def vazio() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUNAS})


def df_exemplo() -> pd.DataFrame:
    """2 lotes em dias distintos, canais #a e #b, 6 linhas, 1 alerta e nenhum case de sucesso."""
    t1 = pd.Timestamp("2026-10-20 15:00", tz="UTC")
    t2 = pd.Timestamp("2026-10-21 15:00", tz="UTC")
    return pd.DataFrame({
        "lote_id": ["l2", "l2", "l1", "l1", "l1", "l2"],
        "processado_em": [t2, t2, t1, t1, t1, t2],
        "periodo_referencia": ["semana 2", "semana 2", "semana 1", "semana 1", "semana 1", "semana 2"],
        "comunidade": ["c"] * 6,
        "canal": ["#a", "#b", "#a", "#b", "#a", "#b"],
        "sentimento": ["Altamente Positivo", "Positivo", "Neutro", "Negativo", "Altamente Negativo", "Positivo"],
        "topico": ["t1", "t2", "t1", "t3", "t3", "t1"],
        "rota": ["faq", "faq", "nenhuma", "faq", "alerta", "nenhuma"],
    })


def df_com_12_topicos() -> pd.DataFrame:
    df = df_exemplo().iloc[:1]
    df = pd.concat([df] * 12, ignore_index=True)
    df["topico"] = [f"t{i}" for i in range(12)]
    extra = df.iloc[:3].copy()
    extra["topico"] = ["t5", "t5", "t7"]
    return pd.concat([df, extra], ignore_index=True)
