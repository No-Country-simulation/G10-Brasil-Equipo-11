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


# ---------------------------------------------------------------------------
# Testes de Segurança Reforçada e Persistência
# ---------------------------------------------------------------------------
def test_endpoints_bloqueados_sem_login_quando_admin_configurado(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "segredo")

    # 1. /processar
    r_proc = cliente.post("/processar", json={"interacoes": []})
    assert r_proc.status_code == 401
    assert "Acesso restrito" in r_proc.json()["detail"]

    # 2. /api/curadoria/exportar
    r_exp = cliente.post("/api/curadoria/exportar", json={"periodo_referencia": "2026-11"})
    assert r_exp.status_code == 401

    # 3. /api/curadoria/decidir
    r_dec = cliente.post("/api/curadoria/decidir", json={"chave": "post", "decisao": "a"})
    assert r_dec.status_code == 401

    # 4. /api/alertas/tratar
    r_alt = cliente.post("/api/alertas/tratar", json={"ordem": 0, "status": "resolvido"})
    assert r_alt.status_code == 401

    # 5. /api/insights
    r_ins = cliente.get("/api/insights")
    assert r_ins.status_code == 401


def test_endpoints_liberados_com_token_autenticado(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "segredo")

    resp_login = cliente.post("/api/auth/login", json={"usuario": "admin", "senha": "segredo"})
    assert resp_login.status_code == 200
    token = resp_login.json()["token"]
    cookies = resp_login.cookies

    # Decidir curadoria
    r_dec = cliente.post("/api/curadoria/decidir", json={"chave": "post", "decisao": "a"}, cookies=cookies)
    assert r_dec.status_code == 200
    assert r_dec.json()["status"] == "ok"

    # Tratar alerta com header
    r_alt = cliente.post("/api/alertas/tratar", json={"ordem": 0, "status": "resolvido"}, headers={"X-Sender-Token": token})
    assert r_alt.status_code == 200
    assert r_alt.json()["status"] == "ok"


def test_exportar_recusa_path_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {
        "origem_comunidade": "Discord_Grupo_ONE_G10",
        "periodo_referencia": "../../pasta_externa",
    }
    r = cliente.post("/api/curadoria/exportar", json=payload)
    assert r.status_code == 400
    assert "inválido" in r.json()["detail"].lower()


def test_exportar_bloqueia_post_sem_autorizacao_do_membro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {
        "origem_comunidade": "Discord_Grupo_ONE_G10",
        "periodo_referencia": "2026-11",
        "post_linkedin": {"titulo": "Destaque", "copy": "Conteúdo...", "membro": "Fulano"},
        "autorizado": False,
    }
    r = cliente.post("/api/curadoria/exportar", json=payload)
    assert r.status_code == 422
    assert "autorização do membro" in r.json()["detail"]


def test_exportar_permite_post_com_autorizacao_do_membro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {
        "origem_comunidade": "Discord_Grupo_ONE_G10",
        "periodo_referencia": "2026-11",
        "post_linkedin": {"titulo": "Destaque", "copy": "Conteúdo...", "membro": "Fulano"},
        "autorizado": True,
    }
    r = cliente.post("/api/curadoria/exportar", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Testes da Landing Page Oficial (Atomic Design + Ponytail + Humanizer)
# ---------------------------------------------------------------------------
def test_servir_landing_page_modulos_e_css():
    r_css1 = cliente.get("/css/03-landing.css")
    assert r_css1.status_code == 200
    assert ".lp-hero" in r_css1.text
    assert ".lp-hero-bird" in r_css1.text
    assert "no-store" in r_css1.headers.get("Cache-Control", "")

    r_css2 = cliente.get("/css/04-landing-sections.css")
    assert r_css2.status_code == 200
    assert ".lp-dashboard" in r_css2.text
    assert ".lp-cta-box" in r_css2.text

    arquivos_js = [
        ("/js/views/landing-view.js", "renderLandingView"),
        ("/js/organisms/landing-header.js", "btn-landing-entrar-topo"),
        ("/js/organisms/landing-hero.js", "btn-landing-entrar-hero"),
        ("/js/organisms/landing-content.js", "01 // O Desafio"),
        ("/js/organisms/landing-demo.js", "btn-landing-entrar-demo"),
        ("/js/organisms/landing-footer.js", "btn-landing-entrar-cta"),
        ("/js/organisms/landing-events.js", "initLandingEvents"),
        ("/js/views/login-view.js", "btn-voltar-landing"),
    ]
    for rota, marcador in arquivos_js:
        resp = cliente.get(rota)
        assert resp.status_code == 200, f"Falha ao carregar {rota}"
        assert marcador in resp.text, f"Marcador {marcador} ausente em {rota}"


def test_landing_page_ponytail_limite_linhas_e_humanizer():
    rotas_componentes = [
        "/css/03-landing.css",
        "/css/04-landing-sections.css",
        "/js/views/landing-view.js",
        "/js/organisms/landing-header.js",
        "/js/organisms/landing-hero.js",
        "/js/organisms/landing-content.js",
        "/js/organisms/landing-demo.js",
        "/js/organisms/landing-footer.js",
        "/js/organisms/landing-events.js",
        "/js/views/login-view.js",
    ]
    cliches_banidos = [
        "Não é sobre falar mais alto",
        "HACKATHON ORACLE EDITION",
        "/api/v1/ingest",
    ]
    for rota in rotas_componentes:
        texto = cliente.get(rota).text
        linhas = texto.splitlines()
        assert len(linhas) < 100, f"Componente {rota} excedeu 100 linhas ({len(linhas)})"
        for cliche in cliches_banidos:
            assert cliche not in texto, f"Clichê ou código obsoleto '{cliche}' encontrado em {rota}"



