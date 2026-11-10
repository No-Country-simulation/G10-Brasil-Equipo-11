from contextlib import contextmanager
from datetime import date

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

    monkeypatch.setattr(
        repository.database,
        "connection",
        fake_connection,
    )

    return conn


def test_consultar_interacoes_insights_usa_data_original(monkeypatch):
    dados = [
        (
            "lote-1",
            date(2026, 10, 5),
            "Comunidade A",
            "#geral",
            "Positivo",
            "Python",
            "faq",
        )
    ]

    conn = conectar_fake(monkeypatch, dados)

    resultado = repository.consultar_interacoes_insights(
        inicio=date(2026, 10, 1),
        fim=date(2026, 10, 31),
        modo="mock",
        comunidades=["Comunidade A"],
        canais=["#geral"],
    )

    assert len(resultado) == 1
    assert resultado[0]["data"] == date(2026, 10, 5)
    assert resultado[0]["sentimento"] == "Positivo"

    sql = conn.fake_cursor.sql
    params = conn.fake_cursor.params

    assert "i.DATA_INTERACAO >= :inicio" in sql
    assert "i.DATA_INTERACAO < :fim_exclusivo" in sql
    assert "JSON_VALUE" in sql

    assert params["inicio"] == date(2026, 10, 1)
    assert params["fim_exclusivo"] == date(2026, 11, 1)

    assert params["comunidade_0"] == "Comunidade A"
    assert params["canal_0"] == "#geral"


def test_consultar_ativos_insights_usa_exists(monkeypatch):
    dados = [
        ("lote-1", "post", "POST_LINKEDIN", "aprovado"),
        ("lote-1", "faq_0", "FAQ", "pendente"),
    ]

    conn = conectar_fake(monkeypatch, dados)

    resultado = repository.consultar_ativos_insights(
        inicio=date(2026, 10, 1),
        fim=date(2026, 10, 31),
        modo="gemini",
        canais=["#duvidas"],
    )

    assert len(resultado) == 2
    assert resultado[0]["status"] == "aprovado"
    assert resultado[1]["status"] == "pendente"

    sql = conn.fake_cursor.sql

    assert "EXISTS" in sql
    assert "CL_ATIVO_INTERACOES" in sql
    assert "i.DATA_INTERACAO" in sql
    assert conn.fake_cursor.params["canal_0"] == "#duvidas"


def test_rejeitar_intervalo_invertido():
    with pytest.raises(ValueError, match="data inicial"):
        repository.consultar_interacoes_insights(
            inicio=date(2026, 10, 31),
            fim=date(2026, 10, 1),
            modo="mock",
        )


def test_rejeitar_modo_insights_invalido():
    with pytest.raises(ValueError, match="Modo de IA"):
        repository.opcoes_filtros_insights("outro")