import pytest
from fastapi.testclient import TestClient

from app import main as api


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        api,
        "_require_oracle",
        lambda: None,
    )

    api.app.dependency_overrides[
        api.require_api_access
    ] = lambda: "usuario-teste"

    test_client = TestClient(api.app)

    yield test_client

    api.app.dependency_overrides.clear()
    test_client.close()


def test_obter_opcoes_insights(client, monkeypatch):
    monkeypatch.setattr(
        api.repository,
        "opcoes_filtros_insights",
        lambda modo: {
            "comunidades": ["Comunidade A"],
            "canais": ["#geral"],
        },
    )

    response = client.get(
        "/insights/opcoes",
        params={"modo": "mock"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "comunidades": ["Comunidade A"],
        "canais": ["#geral"],
    }


def test_obter_interacoes_insights(client, monkeypatch):
    recebidos = {}

    def consultar(**kwargs):
        recebidos.update(kwargs)

        return [
            {
                "lote_id": "lote-1",
                "data": "2026-10-05",
                "comunidade": "Comunidade A",
                "canal": "#geral",
                "sentimento": "Positivo",
                "topico": "Python",
                "rota": "faq",
            }
        ]

    monkeypatch.setattr(
        api.repository,
        "consultar_interacoes_insights",
        consultar,
    )

    response = client.get(
        "/insights/interacoes",
        params=[
            ("inicio", "2026-10-01"),
            ("fim", "2026-10-31"),
            ("modo", "mock"),
            ("comunidades", "Comunidade A"),
            ("comunidades", "Comunidade B"),
            ("canais", "#geral"),
        ],
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1

    assert recebidos["comunidades"] == [
        "Comunidade A",
        "Comunidade B",
    ]
    assert recebidos["canais"] == ["#geral"]


def test_obter_ativos_insights(client, monkeypatch):
    monkeypatch.setattr(
        api.repository,
        "consultar_ativos_insights",
        lambda **kwargs: [
            {
                "lote_id": "lote-1",
                "chave": "post",
                "tipo": "POST_LINKEDIN",
                "status": "aprovado",
            }
        ],
    )

    response = client.get(
        "/insights/ativos",
        params={
            "inicio": "2026-10-01",
            "fim": "2026-10-31",
            "modo": "mock",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "aprovado"


def test_rejeitar_modo_invalido_na_api(client):
    response = client.get(
        "/insights/opcoes",
        params={"modo": "outro"},
    )

    assert response.status_code == 422


def test_rejeitar_data_ausente_na_api(client):
    response = client.get(
        "/insights/interacoes",
        params={"modo": "mock"},
    )

    assert response.status_code == 422