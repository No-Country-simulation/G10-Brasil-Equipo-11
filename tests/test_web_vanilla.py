import json
from fastapi.testclient import TestClient
import pytest

from app.main import app

cliente = TestClient(app)


def test_servir_index_html_no_root():
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "Sender AI" in resposta.text
    assert '<div id="app-root"></div>' in resposta.text
    assert '<script type="module" src="js/app.js"></script>' in resposta.text


def test_servir_tokens_css():
    resposta = cliente.get("/css/00-tokens.css")
    assert resposta.status_code == 200
    assert "--bg: #050a0e;" in resposta.text
    assert "--accent-lime:" in resposta.text


def test_servir_componentes_js():
    resposta = cliente.get("/js/store.js")
    assert resposta.status_code == 200
    assert "class Store" in resposta.text


def test_obter_exemplo_endpoint():
    resposta = cliente.get("/api/exemplo")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["origem_comunidade"] == "Discord_Grupo_ONE_G10"
    assert len(dados["interacoes"]) == 12


def test_exportar_aprovados_endpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {
        "origem_comunidade": "Discord_Grupo_ONE_G10",
        "periodo_referencia": "Semana_04",
        "aprovado_em": "2026-11-07T18:00:00",
        "post_linkedin": None,
        "destaque_newsletter_semanal": None,
        "sugestao_conteudo_faq": [],
        "descartados": [],
    }
    resposta = cliente.post("/api/curadoria/exportar", json=payload)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert "aprovados.json" in corpo["caminho"]
