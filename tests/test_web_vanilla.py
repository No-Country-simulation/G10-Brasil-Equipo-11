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
    assert "COMMUNITYLAB_DB_MODE=oracle" in dados["mensagem"]


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
        ("/js/organisms/landing-hero.js", "Explorar Telemetria"),
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





# ---------------------------------------------------------------------------
# Tela Importar: leitura do arquivo (CSV e JSON) e mensagens sem autor
# ---------------------------------------------------------------------------
CSV_PONTO_E_VIRGULA = (
    "autor;canal;tipo;data;texto\n"
    'Camila Rocha;#conquistas;depoimento;2026-11-09;Consegui minha primeira vaga!\n'
    ';#geral;outro;2026-11-12;bom dia pessoal\n'
    'Paulo Henrique;#duvidas-java;pergunta_tecnica;2026-11-12;"Lista; com ""aspas"" e acentuação: ção"\n'
)


def _enviar_arquivo(nome, conteudo):
    return cliente.post("/api/importar/arquivo", files={"arquivo": (nome, conteudo, "application/octet-stream")})


def test_importar_arquivo_le_csv_com_ponto_e_virgula_acentos_e_autor_vazio():
    resposta = _enviar_arquivo("mensagens.csv", ("﻿" + CSV_PONTO_E_VIRGULA).encode("utf-8"))
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert (dados["formato"], dados["total"], dados["anonimas"]) == ("CSV", 3, 1)
    assert dados["origem_do_arquivo"] is False and dados["periodo_do_arquivo"] is False
    interacoes = dados["lote"]["interacoes"]
    assert interacoes[1]["autor"] == "anônimo_002"
    assert interacoes[2]["texto"] == 'Lista; com "aspas" e acentuação: ção'
    assert interacoes[0]["data"] == "2026-11-09"


def test_importar_arquivo_le_json_e_preenche_autor_anonimo():
    lote = {"origem_comunidade": "Discord_Teste", "periodo_referencia": "2026-11", "interacoes": [
        {"autor": "Ana", "canal": "#geral", "tipo": "outro", "texto": "oi"},
        {"autor": "", "canal": "#geral", "tipo": "outro", "texto": "bom dia"},
    ]}
    resposta = _enviar_arquivo("lote.json", json.dumps(lote).encode("utf-8"))
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert (dados["formato"], dados["total"], dados["anonimas"]) == ("JSON", 2, 1)
    assert dados["origem_do_arquivo"] is True and dados["lote"]["origem_comunidade"] == "Discord_Teste"
    assert dados["lote"]["interacoes"][1]["autor"] == "anônimo_002"


@pytest.mark.parametrize("nome, conteudo, trecho", [
    ("notas.txt", b"qualquer coisa", "Formato não suportado"),
    ("quebrado.json", b"{isto nao e json", "JSON inválido"),
    ("vazio.csv", b"autor;canal;tipo;texto\n", "não contém interações"),
    ("sem_texto.csv", b"autor;canal;tipo;texto\nAna;#geral;outro;\n", "texto"),
])
def test_importar_arquivo_recusa_com_mensagem_clara(nome, conteudo, trecho):
    resposta = _enviar_arquivo(nome, conteudo)
    assert resposta.status_code == 422
    assert isinstance(resposta.json()["detail"], str)
    assert trecho in resposta.json()["detail"]


def test_importar_arquivo_exige_login_quando_admin_configurado(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "senha_forte")
    sem_sessao = TestClient(app)
    resposta = sem_sessao.post("/api/importar/arquivo", files={"arquivo": ("a.csv", CSV_PONTO_E_VIRGULA.encode("utf-8"))})
    assert resposta.status_code == 401


def test_processar_json_sem_autor_vira_anonimo_em_vez_de_derrubar_o_lote():
    lote = {"origem_comunidade": "Discord_Teste", "periodo_referencia": "2026-11", "interacoes": [
        {"autor": "Ana", "canal": "#duvidas", "tipo": "pergunta_tecnica", "texto": "Como instalo o Python?"},
        {"autor": "   ", "canal": "#geral", "tipo": "outro", "texto": "bom dia"},
    ]}
    resposta = cliente.post("/processar", json=lote)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["resumo_comunidade"]["total_interacoes_processadas"] == 2
    assert [a["autor"] for a in resposta.json()["analises"]] == ["Ana", "anônimo_002"]


def test_tela_importar_usa_o_backend_para_ler_o_arquivo_e_trata_o_soltar():
    app_js = cliente.get("/js/app.js").text
    assert "api.lerArquivo(file)" in app_js
    assert "addEventListener('drop'" in app_js and "addEventListener('dragover'" in app_js
    assert "JSON.parse(evt.target.result)" not in app_js  # leitura antiga, que recusava CSV
    assert "/api/importar/arquivo" in cliente.get("/js/api.js").text


# ---------------------------------------------------------------------------
# Curadoria: baixar os aprovados em PDF, CSV ou JSON
# ---------------------------------------------------------------------------
def _pedido_de_download(autorizado=True, decisoes=None):
    lote = json.loads(cliente.get("/api/exemplo").text)
    resultado = cliente.post("/processar", json=lote).json()
    faqs = len(resultado["ativos_distribuicao_gerados"]["sugestao_conteudo_faq"])
    if decisoes is None:
        decisoes = {"post": "a", "newsletter": "a", **{f"faq_{i}": "a" for i in range(faqs)}}
    return {
        "resultado": resultado, "origem_comunidade": "Discord_Grupo_ONE_G10", "periodo_referencia": "2026-11",
        "decisoes": decisoes, "autorizado": autorizado,
        "textos": {"post_copy": "Texto editado pela curadoria: ação, coração — “aspas” 🚀", "faq_0_conteudo": "=SOMA(A1:A9)"},
    }, faqs


def test_baixar_aprovados_em_csv_abre_no_excel_e_neutraliza_formulas():
    import csv, io
    pedido, faqs = _pedido_de_download()
    resposta = cliente.post("/api/curadoria/baixar?formato=csv", json=pedido)
    assert resposta.status_code == 200, resposta.text
    assert resposta.headers["content-type"].startswith("text/csv")
    assert 'filename="aprovados_2026-11.csv"' in resposta.headers["content-disposition"]
    assert resposta.content.startswith(b"\xef\xbb\xbf")  # BOM: o Excel reconhece os acentos
    linhas = list(csv.DictReader(io.StringIO(resposta.content.decode("utf-8-sig")), delimiter=";"))
    assert [l["tipo"] for l in linhas] == ["Post LinkedIn", "Newsletter"] + ["FAQ"] * faqs
    assert linhas[0]["conteudo"].startswith("Texto editado pela curadoria: ação")
    assert linhas[0]["autorizacao_do_membro"] == "sim"
    assert linhas[2]["conteudo"] == "'=SOMA(A1:A9)"  # não vira fórmula na planilha


def test_baixar_aprovados_em_pdf_devolve_um_pdf():
    from app.exportacao_arquivos import _texto_pdf
    pedido, _ = _pedido_de_download()
    resposta = cliente.post("/api/curadoria/baixar?formato=pdf", json=pedido)
    assert resposta.status_code == 200, resposta.text
    assert resposta.headers["content-type"] == "application/pdf"
    assert 'filename="aprovados_2026-11.pdf"' in resposta.headers["content-disposition"]
    assert resposta.content.startswith(b"%PDF") and len(resposta.content) > 1500
    # Acentos e aspas ficam; emoji sai (as fontes padrão do PDF não têm); < e & não quebram o PDF.
    assert _texto_pdf("ação — “ok” 🚀 <b> & fim\nlinha") == "ação — “ok” &lt;b&gt; &amp; fim<br/>linha"


def test_baixar_aprovados_em_pdf_tem_os_textos_com_acentos():
    PdfReader = pytest.importorskip("pypdf").PdfReader  # só confere o texto se o leitor de PDF estiver instalado
    import io
    pedido, faqs = _pedido_de_download()
    resposta = cliente.post("/api/curadoria/baixar?formato=pdf", json=pedido)
    assert resposta.status_code == 200, resposta.text
    texto = " ".join(pagina.extract_text() for pagina in PdfReader(io.BytesIO(resposta.content)).pages)
    for trecho in ("Conteúdos aprovados", "2026-11", "ação, coração", "Autorização do membro: sim", f"FAQ {faqs}"):
        assert trecho in texto, trecho


def test_baixar_aprovados_em_json_traz_so_o_que_foi_aprovado():
    pedido, _ = _pedido_de_download(decisoes={"newsletter": "a", "faq_0": "d", "post": "p"})
    resposta = cliente.post("/api/curadoria/baixar?formato=json", json=pedido)
    assert resposta.status_code == 200, resposta.text
    pacote = resposta.json()
    assert pacote["post_linkedin"] is None and pacote["sugestao_conteudo_faq"] == []
    assert pacote["destaque_newsletter_semanal"]["chamada"]
    assert pacote["descartados"] == ["faq_0"]


def test_baixar_aprovados_respeita_as_regras_da_exportacao(monkeypatch):
    pedido, _ = _pedido_de_download(autorizado=False)
    sem_autorizacao = cliente.post("/api/curadoria/baixar?formato=pdf", json=pedido)
    assert sem_autorizacao.status_code == 422 and "autorização do membro" in sem_autorizacao.json()["detail"]

    nada, _ = _pedido_de_download(decisoes={})
    assert cliente.post("/api/curadoria/baixar?formato=csv", json=nada).status_code == 422

    pedido["autorizado"] = True
    assert cliente.post("/api/curadoria/baixar?formato=docx", json=pedido).status_code == 400
    assert cliente.post("/api/curadoria/baixar?formato=pdf", json={**pedido, "periodo_referencia": "../../fora"}).status_code == 400

    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "senha_forte")
    assert TestClient(app).post("/api/curadoria/baixar?formato=pdf", json=pedido).status_code == 401


def test_painel_abre_na_visao_geral_e_carrega_do_banco():
    store = cliente.get("/js/store.js").text
    assert "activeTab: 'visao'" in store and "activeTab: 'importar'" not in store
    assert "sender_ai_menu_recolhido" in store
    assert "/api/visao-geral" in cliente.get("/js/api.js").text
    assert "export async function carregarVisaoGeral" in cliente.get("/js/visao-geral.js").text


def test_visao_geral_sem_pacote_de_distribuicao_e_com_lotes_pendentes():
    view = cliente.get("/js/views/overview-view.js").text
    assert "Pacote de distribuição" not in view
    assert "renderPendingBatches" in view and "visaoGeral" in view
    assert "btn-revisar-lote" in cliente.get("/js/organisms/pending-batches.js").text
    assert "data-lote-id" in cliente.get("/js/molecules/alert-card.js").text


def test_menu_lateral_substitui_o_header_na_ordem_certa():
    assert cliente.get("/js/organisms/header-bar.js").status_code == 404
    sidebar = cliente.get("/js/organisms/sidebar.js").text
    ordem = [sidebar.index(f"'{t}'") for t in ("visao", "importar", "curadoria", "insights")]
    assert ordem == sorted(ordem)
    assert "btn-recolher-menu" in sidebar and "btn-abrir-menu" in sidebar
    assert "06-sidebar.css" in cliente.get("/").text
    css = cliente.get("/css/06-sidebar.css").text
    assert "@media (max-width: 768px)" in css and "prefers-reduced-motion" in css


def test_lotes_iguais_se_distinguem_pela_data_de_processamento():
    lotes = cliente.get("/js/organisms/pending-batches.js").text
    assert "processado_em" in lotes and "processado " in lotes


def test_erros_da_visao_geral_aparecem_mesmo_com_dados_na_tela():
    view = cliente.get("/js/views/overview-view.js").text
    assert "cl-visao-erro" in view
    carga = cliente.get("/js/visao-geral.js").text
    assert "salvo_no_banco !== true" in carga  # 401/409/503 não somem em silêncio


def test_abrir_lote_salvo_vai_para_a_curadoria():
    assert "abaDestino = 'curadoria'" in cliente.get("/js/lotes.js").text
    assert "'visao')" not in cliente.get("/js/insights-controller.js").text
