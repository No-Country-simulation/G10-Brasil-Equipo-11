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


def test_obter_exemplo_demo_endpoint():
    resposta = cliente.get("/api/exemplo?tipo=demo")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["origem_comunidade"] == "Discord_Grupo_ONE_G10"
    assert len(dados["interacoes"]) == 20


def test_obter_fontes_endpoint():
    resposta = cliente.get("/api/fontes")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert "Discord" in dados["canais"]
    assert "Grupo ONE G10" in dados["canais"]["Discord"]
    assert len(dados["meses"]) == 12
    assert len(dados["anos"]) >= 3


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


# ---------------------------------------------------------------------------
# Testes de Autenticação Admin e Histórico / Insights
# ---------------------------------------------------------------------------
def test_auth_status_sem_admin_configurado(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "")
    monkeypatch.setenv("ADMIN_SENHA", "")
    resposta = cliente.get("/api/auth/status")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["configurado"] is False
    assert dados["logado"] is False


def test_auth_login_recusa_sem_admin_configurado(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "")
    monkeypatch.setenv("ADMIN_SENHA", "")
    resposta = cliente.post("/api/auth/login", json={"usuario": "admin", "senha": "qualquer"})
    assert resposta.status_code == 400
    assert "Login não configurado" in resposta.json()["detail"]


def test_auth_fluxo_completo_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "segredo")

    # 1. Status inicial: configurado mas não logado
    resp_status = cliente.get("/api/auth/status")
    assert resp_status.status_code == 200
    assert resp_status.json()["configurado"] is True
    assert resp_status.json()["logado"] is False

    # 2. Login com senha errada
    resp_errada = cliente.post("/api/auth/login", json={"usuario": "admin", "senha": "errada"})
    assert resp_errada.status_code == 401

    # 3. Login com sucesso
    resp_ok = cliente.post("/api/auth/login", json={"usuario": "admin", "senha": "segredo"})
    assert resp_ok.status_code == 200
    corpo = resp_ok.json()
    assert corpo["status"] == "ok"
    assert corpo["usuario"] == "admin"
    token = corpo["token"]

    # 4. Status com cookie ou token
    resp_logado = cliente.get("/api/auth/status", cookies=resp_ok.cookies)
    assert resp_logado.status_code == 200
    assert resp_logado.json()["logado"] is True

    resp_com_header = cliente.get("/api/auth/status", headers={"X-Sender-Token": token})
    assert resp_com_header.status_code == 200
    assert resp_com_header.json()["logado"] is True

    # 5. Logout
    resp_logout = cliente.post("/api/auth/logout", cookies=resp_ok.cookies)
    assert resp_logout.status_code == 200

    resp_pos_logout = cliente.get("/api/auth/status", cookies=resp_ok.cookies)
    assert resp_pos_logout.json()["logado"] is False


def test_api_insights_sem_banco(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    resposta = cliente.get("/api/insights")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["banco_configurado"] is False
    assert "DATABASE_URL" in dados["mensagem"]


def test_api_insights_demo_mode():
    resposta = cliente.get("/api/insights?demo=true")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["modo_demo"] is True
    assert "numeros" in dados
    assert dados["numeros"]["total"] >= 12
    assert "topicos" in dados and len(dados["topicos"]) > 0
    assert "rotas" in dados and len(dados["rotas"]) > 0
    assert "sentimento_por_dia" in dados
    assert "volume_por_canal" in dados
    assert "aproveitamento" in dados

