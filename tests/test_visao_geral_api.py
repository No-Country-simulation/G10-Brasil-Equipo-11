"""Rota /api/visao-geral: pendências de todos os lotes, lidas do Oracle (com dublês).

Rode com:  python -m pytest tests/test_visao_geral_api.py -v
"""
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import main, repositorio, repository, rotas_web  # noqa: E402

cliente = TestClient(main.app)

LOTES = [
    {"id": "L1", "origem_comunidade": "Discord · ONE", "periodo_referencia": "2026-10",
     "criado_em": "2026-10-03T09:00:00", "finalizado_em": "2026-10-03T09:01:00",
     "ativos_pendentes": {"post": 1, "newsletter": 0, "faq": 2}, "alertas_pendentes": 1},
    {"id": "L2", "origem_comunidade": "Telegram · BR", "periodo_referencia": "2026-11",
     "criado_em": "2026-11-02T09:00:00", "finalizado_em": None,
     "ativos_pendentes": {"post": 0, "newsletter": 0, "faq": 0}, "alertas_pendentes": 1},
    {"id": "L3", "origem_comunidade": "Discord · Dev", "periodo_referencia": "2026-11",
     "criado_em": "2026-11-05T09:00:00", "finalizado_em": "2026-11-05T09:02:00",
     "ativos_pendentes": {"post": 0, "newsletter": 1, "faq": 0}, "alertas_pendentes": 0},
]


def processamento(pid, analises, fontes, alertas):
    return {"id": pid, "resultado": {"analises": analises, "fontes_ativos": fontes}, "ativos": [], "alertas": alertas}


DETALHES = {
    "L1": processamento(
        "L1",
        [{"rota": "faq"}, {"rota": "alerta", "tipo": "reclamacao", "autor": "Bia", "canal": "#suporte", "texto": "Ruim"},
         {"rota": "nenhuma"}, {"rota": "alerta", "tipo": "duvida", "autor": "Caio", "canal": "#geral", "texto": "Ok"}],
        {"alerta_0": ["int-1"], "alerta_1": ["int-3"]},
        [{"id": "a-3", "interacao_id": "int-3", "status": "RESOLVIDO", "autor": "Caio", "canal": "#geral", "texto": "Ok"},
         {"id": "a-1", "interacao_id": "int-1", "status": "PENDENTE", "autor": "Bia", "canal": "#suporte", "texto": "Ruim"}],
    ),
    "L2": processamento(
        "L2",
        [{"rota": "faq"}, {"rota": "alerta", "tipo": "duvida", "autor": "Duda", "canal": "#ajuda", "texto": "Socorro"}],
        {"alerta_0": ["int-9"]},
        [{"id": "a-9", "interacao_id": "int-9", "status": "PENDENTE", "autor": "Duda", "canal": "#ajuda", "texto": "Socorro"}],
    ),
}


@pytest.fixture
def oracle(monkeypatch):
    chamadas = {"detalhe": [], "janela": []}
    monkeypatch.setattr(rotas_web, "oracle_ativo", lambda: True)
    monkeypatch.setattr(rotas_web, "_modo_atual", lambda: "mock")
    monkeypatch.setattr(repositorio, "hoje", lambda: date(2026, 11, 13))
    monkeypatch.setattr(repository, "listar_lotes_com_pendencias", lambda modo: [dict(l) for l in LOTES])

    def detalhe(pid):
        chamadas["detalhe"].append(pid)
        return DETALHES.get(pid)

    def interacoes(inicio, fim, modo):
        chamadas["janela"].append(("interacoes", inicio, fim, modo))
        return [{"lote_id": "L1", "data": date(2026, 11, 12), "autor": "Ana", "canal": "#geral", "texto": "Oi",
                 "sentimento": "Positivo", "rota": "faq", "relevancia": 7}]

    def tratados(inicio, fim, modo):
        chamadas["janela"].append(("tratados", inicio, fim, modo))
        return 2

    monkeypatch.setattr(repository, "obter_processamento", detalhe)
    monkeypatch.setattr(repository, "consultar_interacoes_recentes", interacoes)
    monkeypatch.setattr(repository, "contar_alertas_tratados", tratados)
    return chamadas


def test_visao_geral_lista_lotes_e_soma_ativos(oracle):
    r = cliente.get("/api/visao-geral").json()
    assert r["oracle_configurado"] is True
    assert r["janela"] == {"inicio": "2026-11-07", "fim": "2026-11-13"}
    assert [l["lote_id"] for l in r["lotes_pendentes"]] == ["L1", "L2", "L3"]
    primeiro = r["lotes_pendentes"][0]
    assert primeiro["ativos_pendentes"] == 3
    assert primeiro["ativos_por_tipo"] == {"post": 1, "newsletter": 0, "faq": 2}
    assert primeiro["alertas_pendentes"] == 1
    assert (primeiro["origem"], primeiro["periodo"]) == ("Discord · ONE", "2026-10")
    assert primeiro["processado_em"] == "2026-10-03T09:01:00+00:00"
    assert r["alertas_tratados_janela"] == 2
    assert r["atualizado_em"].endswith("+00:00")
    assert r["interacoes"] == [{"lote_id": "L1", "data": "2026-11-12", "autor": "Ana", "canal": "#geral", "texto": "Oi",
                                "sentimento": "Positivo", "rota": "faq", "relevancia": 7}]


def test_alertas_pendentes_trazem_lote_e_ordem_de_origem(oracle):
    alertas = cliente.get("/api/visao-geral").json()["alertas_pendentes"]
    # o alerta RESOLVIDO do L1 (ordem 3) não aparece; L2 tem alerta na mesma ordem 1 do L1
    assert [(a["lote_id"], a["ordem"], a["tipo"]) for a in alertas] == [("L1", 1, "reclamacao"), ("L2", 1, "duvida")]
    assert alertas[0] | {} == {"lote_id": "L1", "ordem": 1, "origem": "Discord · ONE", "periodo": "2026-10",
                              "autor": "Bia", "canal": "#suporte", "texto": "Ruim", "tipo": "reclamacao"}


def test_so_busca_detalhe_de_lote_com_alerta_pendente(oracle):
    cliente.get("/api/visao-geral")
    assert oracle["detalhe"] == ["L1", "L2"]  # L3 só tem ativo pendente


def test_lote_sem_fontes_ativos_nao_derruba_a_rota(oracle, monkeypatch):
    quebrado = processamento(
        "L1", [{"rota": "alerta", "tipo": "duvida"}], {},
        [{"id": "x1", "interacao_id": "int-1", "status": "PENDENTE"},
         {"id": "x2", "interacao_id": "int-2", "status": "PENDENTE"}],
    )
    monkeypatch.setitem(DETALHES, "L1", quebrado)
    r = cliente.get("/api/visao-geral")
    assert r.status_code == 200
    alertas_l1 = [a for a in r.json()["alertas_pendentes"] if a["lote_id"] == "L1"]
    assert [a["ordem"] for a in alertas_l1] == [0]  # o segundo alerta não tem mensagem correspondente


def test_lote_que_sumiu_do_banco_e_pulado(oracle, monkeypatch):
    monkeypatch.delitem(DETALHES, "L1")
    r = cliente.get("/api/visao-geral")
    assert r.status_code == 200
    assert [a["lote_id"] for a in r.json()["alertas_pendentes"]] == ["L2"]


def test_visao_geral_passa_janela_de_7_dias_e_modo(oracle):
    cliente.get("/api/visao-geral")
    assert sorted(oracle["janela"]) == [
        ("interacoes", date(2026, 11, 7), date(2026, 11, 13), "mock"),
        ("tratados", date(2026, 11, 7), date(2026, 11, 13), "mock"),
    ]


def test_visao_geral_sem_oracle_avisa(monkeypatch):
    monkeypatch.setattr(rotas_web, "oracle_ativo", lambda: False)
    r = cliente.get("/api/visao-geral")
    assert r.status_code == 200
    assert r.json()["oracle_configurado"] is False
    assert "Oracle" in r.json()["mensagem"]


def test_visao_geral_com_banco_fora_do_ar_da_503_sem_vazar_detalhe(oracle, monkeypatch):
    def falha(*a, **k):
        raise RuntimeError("ORA-12541 host interno")
    monkeypatch.setattr(repository, "listar_lotes_com_pendencias", falha)
    r = cliente.get("/api/visao-geral")
    assert r.status_code == 503
    assert "ORA-" not in r.text


def test_visao_geral_exige_login(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "segredo")
    assert cliente.get("/api/visao-geral").status_code == 401
