"""Dados montados à mão para os testes das agregações de Insights."""
from datetime import date

import pandas as pd

COLUNAS = ["lote_id", "data", "comunidade", "canal", "sentimento", "topico", "rota"]


def vazio() -> pd.DataFrame:
    return pd.DataFrame({c: [] for c in COLUNAS})


def df_exemplo() -> pd.DataFrame:
    """Mensagens de 3 dias (fora de ordem), canais #a e #b, 6 linhas, 1 alerta e nenhum case de sucesso."""
    d1, d2, d3 = date(2026, 10, 3), date(2026, 10, 10), date(2026, 10, 11)
    return pd.DataFrame({
        "lote_id": ["l2", "l2", "l1", "l1", "l1", "l2"],
        "data": [d3, d2, d1, d1, d2, d3],
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
