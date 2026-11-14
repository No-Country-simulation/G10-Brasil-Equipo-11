"""Consultas do Oracle que alimentam a Visão geral, sem banco de verdade.

Rode com:  python -m pytest tests/test_visao_geral_repository.py -v
"""
from contextlib import contextmanager
from datetime import date, datetime

import pytest

from app import repository


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params or {}

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0]


class FakeConnection:
    def __init__(self, rows):
        self.fake_cursor = FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.fake_cursor


def conectar_fake(monkeypatch, rows):
    conn = FakeConnection(rows)

    @contextmanager
    def fake_connection():
        yield conn

    monkeypatch.setattr(repository.database, "connection", fake_connection)
    return conn


def test_lotes_com_pendencias_conta_por_tipo_e_ordena_do_mais_antigo(monkeypatch):
    conn = conectar_fake(monkeypatch, [
        ("L1", "Discord · ONE", "2026-10", datetime(2026, 10, 3, 9), datetime(2026, 10, 3, 9, 1), 1, 0, 2, 1),
        ("L2", "Telegram · BR", "2026-11", datetime(2026, 11, 2, 9), None, 0, 0, 0, 1),
    ])
    lotes = repository.listar_lotes_com_pendencias("gemini")
    sql = conn.fake_cursor.sql
    assert "STATUS_CURADORIA = 'PENDENTE'" in sql and "STATUS_TRIAGEM = 'PENDENTE'" in sql
    assert "p.STATUS = 'SUCESSO'" in sql and "MODO_IA = :modo" in sql
    assert "ORDER BY" in sql and "CRIADO_EM ASC" in sql
    assert conn.fake_cursor.params == {"modo": "gemini", "lim": 50}
    assert lotes[0] == {
        "id": "L1", "origem_comunidade": "Discord · ONE", "periodo_referencia": "2026-10",
        "criado_em": "2026-10-03T09:00:00", "finalizado_em": "2026-10-03T09:01:00",
        "ativos_pendentes": {"post": 1, "newsletter": 0, "faq": 2}, "alertas_pendentes": 1,
    }
    assert lotes[1]["ativos_pendentes"] == {"post": 0, "newsletter": 0, "faq": 0}  # só alerta: entra
    assert lotes[1]["finalizado_em"] is None


def test_lotes_com_pendencias_recusa_modo_invalido():
    with pytest.raises(ValueError):
        repository.listar_lotes_com_pendencias("outro")


def test_lotes_com_pendencias_limita_entre_1_e_100(monkeypatch):
    conn = conectar_fake(monkeypatch, [])
    repository.listar_lotes_com_pendencias("mock", limite=500)
    assert conn.fake_cursor.params["lim"] == 100


def test_interacoes_recentes_traz_texto_e_relevancia(monkeypatch):
    conn = conectar_fake(monkeypatch, [("L1", date(2026, 11, 12), "Ana", "#geral", "Oi", "Positivo", "faq", "7")])
    linhas = repository.consultar_interacoes_recentes(date(2026, 11, 7), date(2026, 11, 13), "mock")
    sql = conn.fake_cursor.sql
    assert "$.relevancia" in sql and "i.DATA_INTERACAO < :fim_exclusivo" in sql
    assert conn.fake_cursor.params["fim_exclusivo"] == date(2026, 11, 14)
    assert linhas == [{"lote_id": "L1", "data": date(2026, 11, 12), "autor": "Ana", "canal": "#geral",
                       "texto": "Oi", "sentimento": "Positivo", "rota": "faq", "relevancia": 7}]


def test_interacoes_recentes_relevancia_invalida_vira_none(monkeypatch):
    conectar_fake(monkeypatch, [("L1", date(2026, 11, 12), "Ana", "#geral", "Oi", "Positivo", "faq", "alta")])
    linhas = repository.consultar_interacoes_recentes(date(2026, 11, 7), date(2026, 11, 13), "mock")
    assert linhas[0]["relevancia"] is None


def test_interacoes_recentes_recusa_intervalo_invertido():
    with pytest.raises(ValueError):
        repository.consultar_interacoes_recentes(date(2026, 11, 13), date(2026, 11, 7), "mock")


def test_contar_alertas_tratados_na_janela(monkeypatch):
    conn = conectar_fake(monkeypatch, [(3,)])
    assert repository.contar_alertas_tratados(date(2026, 11, 7), date(2026, 11, 13), "gemini") == 3
    assert "STATUS_TRIAGEM <> 'PENDENTE'" in conn.fake_cursor.sql
    assert conn.fake_cursor.params["modo"] == "gemini"
