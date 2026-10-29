"""Testes das agregações da tela Insights.

    python -m pytest tests/test_insights.py -v
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.dados_insights import df_com_12_topicos as _doze, df_exemplo, vazio  # noqa: E402
from ui import insights as ins  # noqa: E402


@pytest.fixture
def df():
    return df_exemplo()


@pytest.fixture
def df_com_12_topicos():
    return _doze()


def test_numeros_periodo(df):
    assert ins.numeros_periodo(df) == {"total": 6, "pct_positivas": 50.0, "pct_negativas": 33.3, "alertas": 1}


def test_numeros_periodo_vazio():
    assert ins.numeros_periodo(vazio()) == {"total": 0, "pct_positivas": 0.0, "pct_negativas": 0.0, "alertas": 0}


def test_sentimento_por_lote_ordenado_e_soma_o_total(df):
    s = ins.sentimento_por_lote(df)
    assert s["processado_em"].is_monotonic_increasing and s["quantidade"].sum() == 6


def test_rotulo_usa_fuso_local(df):
    assert ins.sentimento_por_lote(df)["rotulo"].iloc[0] == "20/10 12:00 · semana 1 · c"


def test_sentimento_por_canal_soma_100_por_canal(df):
    s = ins.sentimento_por_canal(df)
    assert s.groupby("canal")["percentual"].sum().round(6).eq(100).all()


def test_topicos_limita_e_ordena(df_com_12_topicos):
    t = ins.topicos_mais_falados(df_com_12_topicos)
    assert len(t) == 10 and t["quantidade"].is_monotonic_decreasing


def test_volume_por_canal(df):
    assert ins.volume_por_canal(df)["quantidade"].sum() == 6


def test_rotas_geradas_inclui_zero(df):
    r = ins.rotas_geradas(df)
    assert list(r["rota"]) == ["case_sucesso", "faq", "alerta"]
    assert r.set_index("rota").loc["case_sucesso", "quantidade"] == 0


def test_aproveitamento_ativos():
    ativos = pd.DataFrame({"status": ["pendente", "aprovado", "aprovado", "descartado"]})
    assert ins.aproveitamento_ativos(ativos) == {"gerados": 4, "aprovados": 2, "descartados": 1, "pendentes": 1}


def test_aproveitamento_ativos_vazio():
    assert ins.aproveitamento_ativos(pd.DataFrame({"status": []})) == {
        "gerados": 0, "aprovados": 0, "descartados": 0, "pendentes": 0}


@pytest.mark.parametrize("funcao", [ins.sentimento_por_lote, ins.sentimento_por_canal, ins.topicos_mais_falados,
                                    ins.volume_por_canal])
def test_tabelas_vazias_nao_quebram(funcao):
    assert funcao(vazio()).empty
