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


def test_sentimento_por_dia_ordenado_e_soma_o_total(df):
    s = ins.sentimento_por_dia(df)
    assert s["data"].is_monotonic_increasing and s["quantidade"].sum() == 6
    assert list(s["data"].drop_duplicates().dt.day) == [3, 10, 11]


def test_sentimento_por_dia_junta_lotes_do_mesmo_dia(df):
    s = ins.sentimento_por_dia(df)
    dia_10 = s[s["data"] == pd.Timestamp("2026-10-10")]
    assert dia_10["quantidade"].sum() == 2  # uma mensagem de cada lote


def test_sentimento_por_canal_soma_100_por_canal(df):
    s = ins.sentimento_por_canal(df)
    assert s.groupby("canal")["percentual"].sum().round(6).eq(100).all()


def test_topicos_limita_e_ordena(df_com_12_topicos):
    t = ins.topicos_mais_falados(df_com_12_topicos)
    assert len(t) == 10 and t["quantidade"].is_monotonic_decreasing


def test_volume_por_canal(df):
    v = ins.volume_por_canal(df)
    assert v["quantidade"].sum() == 6 and v["data"].is_monotonic_increasing
    assert v[(v["data"] == pd.Timestamp("2026-10-03"))].set_index("canal")["quantidade"].to_dict() == {"#a": 1, "#b": 1}


def test_rotas_geradas_inclui_zero_e_sem_acao(df):
    r = ins.rotas_geradas(df)
    assert list(r["rota"]) == ["case_sucesso", "faq", "alerta", "nenhuma"]
    assert r.set_index("rota")["quantidade"].to_dict() == {"case_sucesso": 0, "faq": 3, "alerta": 1, "nenhuma": 2}


def test_sentimento_divergente_centra_o_neutro():
    df = pd.DataFrame({"canal": ["#n", "#n", "#m", "#m", "#m", "#m"],
                       "sentimento": ["Neutro", "Neutro", "Negativo", "Neutro", "Positivo", "Altamente Positivo"]})
    t = ins.sentimento_divergente(df).set_index(["canal", "sentimento"])
    assert (t.loc[("#n", "Neutro"), "inicio"], t.loc[("#n", "Neutro"), "fim"]) == (-50, 50)
    # #m: 25% negativo à esquerda, metade do neutro de cada lado, positivos à direita
    assert t.loc[("#m", "Negativo"), "inicio"] == pytest.approx(-37.5)
    assert t.loc[("#m", "Neutro"), "inicio"] == pytest.approx(-12.5)
    assert t.loc[("#m", "Altamente Positivo"), "fim"] == pytest.approx(62.5)


def test_resumo_por_canal_ordena_do_mais_positivo():
    df = pd.DataFrame({"canal": ["#ruim", "#bom", "#bom"], "sentimento": ["Negativo", "Positivo", "Neutro"]})
    r = ins.resumo_por_canal(df)
    assert list(r["canal"]) == ["#bom", "#ruim"]
    assert r.set_index("canal").loc["#bom", "pct_positivas"] == 50 and r.set_index("canal").loc["#ruim", "pct_negativas"] == 100


def test_aproveitamento_ativos():
    ativos = pd.DataFrame({"status": ["pendente", "aprovado", "aprovado", "descartado"]})
    assert ins.aproveitamento_ativos(ativos) == {"gerados": 4, "aprovados": 2, "descartados": 1, "pendentes": 1}


def test_aproveitamento_ativos_vazio():
    assert ins.aproveitamento_ativos(pd.DataFrame({"status": []})) == {
        "gerados": 0, "aprovados": 0, "descartados": 0, "pendentes": 0}


@pytest.mark.parametrize("funcao", [ins.sentimento_por_dia, ins.sentimento_por_canal, ins.topicos_mais_falados,
                                    ins.volume_por_canal, ins.sentimento_divergente, ins.resumo_por_canal])
def test_tabelas_vazias_nao_quebram(funcao):
    assert funcao(vazio()).empty
