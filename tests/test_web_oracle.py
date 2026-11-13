"""Ponte entre o painel web e o Oracle, sem banco de verdade.

O repositório Oracle é trocado por dublês: os testes conferem só a tradução entre o
que o painel envia (lote_id, chave, decisão, ordem da mensagem) e o que o
`app.repository` espera (ID do ativo, versão, estados em maiúsculas).

Rode com:  python -m pytest tests/test_web_oracle.py -v
"""
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import main, repository, rotas_web  # noqa: E402

cliente = TestClient(main.app)

PROCESSAMENTO = {
    "id": "proc-1",
    "resultado": {
        "analises": [{"rota": "faq"}, {"rota": "alerta"}, {"rota": "nenhuma"}, {"rota": "alerta"}],
        "fontes_ativos": {"alerta_0": ["int-1"], "alerta_1": ["int-3"]},
    },
    "ativos": [
        {"id": "ativo-post", "chave": "post", "versao": 1},
        {"id": "ativo-news", "chave": "newsletter", "versao": 3},
        {"id": "ativo-faq", "chave": "faq_0", "versao": 1},
    ],
    # De propósito fora de ordem: o alerta é achado pela interação de origem, não pela posição.
    "alertas": [
        {"id": "alerta-b", "interacao_id": "int-3", "versao": 2},
        {"id": "alerta-a", "interacao_id": "int-1", "versao": 1},
    ],
}


@pytest.fixture
def oracle(monkeypatch):
    """Liga o caminho Oracle das rotas web e registra as chamadas ao repositório."""
    chamadas = []
    monkeypatch.setattr(rotas_web, "oracle_ativo", lambda: True)
    monkeypatch.setattr(repository, "obter_processamento", lambda pid: PROCESSAMENTO if pid == "proc-1" else None)
    monkeypatch.setattr(repository, "atualizar_curadoria", lambda **k: chamadas.append(("curadoria", k)) or {})
    monkeypatch.setattr(repository, "atualizar_alerta", lambda **k: chamadas.append(("alerta", k)) or {})
    return chamadas


def test_aprovar_newsletter_envia_id_versao_e_campos_do_ativo(oracle):
    r = cliente.post("/api/curadoria/decidir", json={
        "lote_id": "proc-1", "chave": "newsletter", "decisao": "a",
        "textos": {"news_chamada": "Nova chamada", "news_resumo": "  ", "post_copy": "de outro ativo"},
    })
    assert r.json() == {"status": "ok", "salvo_no_banco": True}
    _, k = oracle[0]
    assert (k["asset_id"], k["status"], k["versao_esperada"]) == ("ativo-news", "APROVADO", 3)
    assert k["patch"] == {"chamada": "Nova chamada"}  # campo em branco e texto de outro ativo ficam de fora
    assert k["consentimento"] is None


def test_post_autorizado_registra_consentimento_com_referencia(oracle, monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "")
    r = cliente.post("/api/curadoria/decidir", json={
        "lote_id": "proc-1", "chave": "post", "decisao": "a", "textos": {"post_copy": "Copy"}, "autorizacao": True,
    })
    assert r.json()["salvo_no_banco"] is True
    _, k = oracle[0]
    assert k["patch"] == {"copy": "Copy"}
    assert k["consentimento"] is True
    assert "painel-web" in k["referencia_consentimento"]
    assert k["actor"] == "painel-web"


def test_faq_descartada_usa_o_campo_conteudo(oracle):
    cliente.post("/api/curadoria/decidir", json={
        "lote_id": "proc-1", "chave": "faq_0", "decisao": "d", "textos": {"faq_0_conteudo": "Texto"},
    })
    _, k = oracle[0]
    assert (k["asset_id"], k["status"], k["patch"]) == ("ativo-faq", "DESCARTADO", {"conteudo": "Texto"})


@pytest.mark.parametrize("corpo", [
    {"lote_id": "proc-1", "chave": "faq_9", "decisao": "a"},      # ativo que não existe no lote
    {"lote_id": "nao-existe", "chave": "post", "decisao": "a"},   # lote que não existe
    {"lote_id": "proc-1", "chave": "post", "decisao": "x"},       # decisão inválida
])
def test_decisao_que_nao_pode_ser_gravada_avisa_sem_derrubar_a_tela(oracle, corpo):
    r = cliente.post("/api/curadoria/decidir", json=corpo)
    assert r.status_code == 200
    assert r.json()["salvo_no_banco"] is False
    assert r.json()["detalhe"]
    assert oracle == []


def test_regra_do_banco_recusada_volta_como_detalhe(oracle, monkeypatch):
    def recusa(**_):
        raise repository.InvalidCuration("A aprovação do post exige autorização documentada.")

    monkeypatch.setattr(repository, "atualizar_curadoria", recusa)
    r = cliente.post("/api/curadoria/decidir", json={"lote_id": "proc-1", "chave": "post", "decisao": "a"})
    assert r.json() == {"status": "ok", "salvo_no_banco": False,
                        "detalhe": "A aprovação do post exige autorização documentada."}


def test_falha_inesperada_do_banco_nao_vaza_detalhes(oracle, monkeypatch):
    def explode(**_):
        raise RuntimeError("ORA-12345 senha=segredo")

    monkeypatch.setattr(repository, "atualizar_curadoria", explode)
    r = cliente.post("/api/curadoria/decidir", json={"lote_id": "proc-1", "chave": "post", "decisao": "d"})
    assert r.json()["salvo_no_banco"] is False
    assert "segredo" not in r.text and "ORA-" not in r.text


@pytest.mark.parametrize("status_painel, estado, acao", [
    ("encaminhado", "ENCAMINHADO", "Encaminhado"),
    ("mentoria_oferecida", "ENCAMINHADO", "Mentoria oferecida"),
    ("resolvido", "RESOLVIDO", "Resolvido"),
])
def test_alerta_e_achado_pela_ordem_da_mensagem(oracle, status_painel, estado, acao):
    # A mensagem de ordem 3 é o segundo alerta do lote (alerta_1 -> interação int-3).
    r = cliente.post("/api/alertas/tratar", json={"lote_id": "proc-1", "ordem": 3, "status": status_painel})
    assert r.json() == {"status": "ok", "salvo_no_banco": True}
    _, k = oracle[0]
    assert (k["alert_id"], k["versao_esperada"], k["status"], k["acao"]) == ("alerta-b", 2, estado, acao)


@pytest.mark.parametrize("corpo", [
    {"lote_id": "proc-1", "ordem": 0, "status": "resolvido"},   # a mensagem 0 não é um alerta
    {"lote_id": "proc-1", "ordem": 1, "status": "inventado"},   # estado desconhecido
])
def test_alerta_invalido_nao_grava(oracle, corpo):
    r = cliente.post("/api/alertas/tratar", json=corpo)
    assert r.json()["salvo_no_banco"] is False
    assert oracle == []


@pytest.fixture
def exportacao(oracle, monkeypatch):
    """Dublês da exportação: registra no 'banco' e devolve o resultado de envio escolhido pelo teste."""
    envio = {"bucket": "communitylab-ativos-marketing", "caminho_objeto": "ativos/2026-11/x/aprovados.json",
             "status": "salvo_com_sucesso"}
    monkeypatch.setattr(repository, "criar_exportacao",
                        lambda pid, actor: oracle.append(("exportacao", pid)) or {"id": "exp-1", "pacote": {}})
    monkeypatch.setattr(main, "_upload_export", lambda export_id: dict(envio))
    return envio


def test_exportar_grava_as_decisoes_da_tela_antes_de_gerar_o_pacote(exportacao, oracle):
    r = cliente.post("/api/curadoria/exportar", json={
        "lote_id": "proc-1", "periodo_referencia": "2026-11", "autorizado": True,
        "decisoes": {"post": "a", "faq_0": "d"}, "textos": {"post_copy": "Copy final"},
    })
    assert r.status_code == 200
    assert [nome for nome, _ in oracle] == ["curadoria", "curadoria", "exportacao"]
    assert oracle[0][1]["patch"] == {"copy": "Copy final"} and oracle[0][1]["consentimento"] is True
    dados = r.json()
    assert dados["caminho"] == "oci://communitylab-ativos-marketing/ativos/2026-11/x/aprovados.json"
    assert dados["exportacao_id"] == "exp-1"


def test_exportar_de_novo_sem_mudancas_avisa_que_ja_foi_exportado(exportacao, monkeypatch):
    monkeypatch.setattr(repository, "criar_exportacao", lambda pid, actor: {
        "id": "exp-1", "pacote": {}, "existing": True, "criado_em": "2026-11-12T01:30:00+00:00"})
    dados = cliente.post("/api/curadoria/exportar", json={"lote_id": "proc-1", "periodo_referencia": "2026-11"}).json()
    assert dados["ja_exportado"] is True
    assert dados["exportado_em"] == "2026-11-12T01:30:00+00:00"
    assert dados["exportacao_id"] == "exp-1"


def test_primeira_exportacao_nao_e_marcada_como_repetida(exportacao):
    dados = cliente.post("/api/curadoria/exportar", json={"lote_id": "proc-1", "periodo_referencia": "2026-11"}).json()
    assert dados["ja_exportado"] is False


def test_exportar_em_modo_local_mostra_o_caminho_em_disco(exportacao):
    exportacao.update(bucket="local", status="salvo_localmente")
    r = cliente.post("/api/curadoria/exportar", json={"lote_id": "proc-1", "periodo_referencia": "2026-11"})
    assert Path(r.json()["caminho"]) == Path("saida_local/ativos/2026-11/x/aprovados.json")


def test_exportar_com_falha_no_bucket_nao_finge_que_salvou(exportacao):
    exportacao.update(status="erro", detalhe="Falha no armazenamento (ServiceError).")
    r = cliente.post("/api/curadoria/exportar", json={"lote_id": "proc-1", "periodo_referencia": "2026-11"})
    assert r.status_code == 502
    assert "exp-1" in r.json()["detail"] and "Object Storage" in r.json()["detail"]


def test_exportar_post_sem_autorizacao_e_recusado(exportacao, oracle, monkeypatch):
    def recusa(**_):
        raise repository.InvalidCuration("A aprovação do post exige autorização documentada.")

    monkeypatch.setattr(repository, "atualizar_curadoria", recusa)
    r = cliente.post("/api/curadoria/exportar", json={
        "lote_id": "proc-1", "periodo_referencia": "2026-11", "decisoes": {"post": "a"}})
    assert r.status_code == 422
    assert ("exportacao", "proc-1") not in oracle


MENSAGENS = [
    {"autor": "Ana", "canal": "#geral", "tipo": "pergunta_tecnica", "texto": "Como configuro o Maven?", "data": "2026-11-01"},
    {"autor": "Bia", "canal": "#geral", "texto": "Consegui a vaga, obrigada!"},
]


def test_hash_das_mensagens_ignora_ordem_espacos_e_tipo_padrao():
    outra_ordem = [dict(MENSAGENS[1], tipo="outro", texto="  Consegui a vaga, obrigada!  "), MENSAGENS[0]]
    assert rotas_web.hash_das_mensagens(MENSAGENS) == rotas_web.hash_das_mensagens(outra_ordem)
    mudou = [MENSAGENS[0], dict(MENSAGENS[1], texto="Outro texto")]
    assert rotas_web.hash_das_mensagens(MENSAGENS) != rotas_web.hash_das_mensagens(mudou)


def test_verificar_reconhece_o_mesmo_conteudo_importado_com_outra_origem(oracle, monkeypatch):
    pedido = {}

    def entradas(modo, total):
        pedido.update(modo=modo, total=total)
        return [
            {"id": "outro", "origem_comunidade": "X", "periodo_referencia": "2026-10", "finalizado_em": None,
             "entrada": {"interacoes": [MENSAGENS[0], {"autor": "Zé", "canal": "#x", "texto": "diferente"}]}},
            {"id": "proc-9", "origem_comunidade": "Discord · Dev Brasil", "periodo_referencia": "2026-11",
             "finalizado_em": "2026-11-11T21:57:00+00:00",
             "entrada": {"origem_comunidade": "Discord · Dev Brasil", "interacoes": list(reversed(MENSAGENS))}},
        ]

    monkeypatch.setenv("LLM_MODO", "mock")
    monkeypatch.setattr(repository, "listar_entradas_concluidas", entradas)
    r = cliente.post("/api/lotes/verificar", json={"interacoes": MENSAGENS})
    assert r.json()["existente"] == {"lote_id": "proc-9", "processado_em": "2026-11-11T21:57:00+00:00",
                                     "origem": "Discord · Dev Brasil", "periodo": "2026-11", "total": 2}
    assert pedido == {"modo": "mock", "total": 2}


def test_verificar_conteudo_novo_ou_banco_fora_do_ar_libera_o_processamento(oracle, monkeypatch):
    monkeypatch.setattr(repository, "listar_entradas_concluidas", lambda modo, total: [])
    assert cliente.post("/api/lotes/verificar", json={"interacoes": MENSAGENS}).json() == {"existente": None}

    def explode(modo, total):
        raise RuntimeError("ORA-00001")

    monkeypatch.setattr(repository, "listar_entradas_concluidas", explode)
    assert cliente.post("/api/lotes/verificar", json={"interacoes": MENSAGENS}).json() == {"existente": None}


def test_verificar_sem_oracle_nunca_acusa_duplicado():
    assert cliente.post("/api/lotes/verificar", json={"interacoes": MENSAGENS}).json() == {"existente": None}


def test_abrir_lote_devolve_textos_editados_decisoes_e_alertas(oracle, monkeypatch):
    salvo = {
        "id": "proc-1", "status": "SUCESSO", "origem_comunidade": "Discord · geral", "periodo_referencia": "2026-11",
        "finalizado_em": "2026-11-11T21:57:00+00:00",
        "resultado": {
            "analises": [{"rota": "faq"}, {"rota": "alerta"}, {"rota": "alerta"}, {"rota": "alerta"}],
            "fontes_ativos": {"alerta_0": ["int-1"], "alerta_1": ["int-2"], "alerta_2": ["int-3"]},
            "ativos_distribuicao_gerados": {
                "post_linkedin": {"titulo": "T", "copy": "original"},
                "sugestao_conteudo_faq": [{"tema": "A", "conteudo": "original"}, {"tema": "B", "conteudo": "b"}],
            },
        },
        "ativos": [
            {"chave": "post", "payload": {"titulo": "T", "copy": "editada"}, "status_curadoria": "APROVADO",
             "consentimento_status": "CONFIRMADO"},
            {"chave": "faq_0", "payload": {"tema": "A", "conteudo": "faq editada"}, "status_curadoria": "DESCARTADO"},
            {"chave": "faq_1", "payload": {"tema": "B", "conteudo": "b"}, "status_curadoria": "PENDENTE"},
        ],
        "alertas": [
            {"interacao_id": "int-1", "status": "RESOLVIDO", "acao": "Resolvido"},
            {"interacao_id": "int-2", "status": "ENCAMINHADO", "acao": "Mentoria oferecida"},
            {"interacao_id": "int-3", "status": "PENDENTE", "acao": None},
        ],
    }
    monkeypatch.setattr(repository, "obter_processamento", lambda pid: salvo)
    dados = cliente.get("/api/lotes/proc-1").json()
    ativos = dados["resultado"]["ativos_distribuicao_gerados"]
    assert ativos["post_linkedin"]["copy"] == "editada"
    assert ativos["sugestao_conteudo_faq"][0]["conteudo"] == "faq editada"
    assert dados["decisoes"] == {"post": "a", "faq_0": "d", "faq_1": "p"}
    assert dados["autorizado"] is True
    assert dados["alertas"] == {"1": "resolvido", "2": "mentoria_oferecida"}  # o pendente fica de fora
    assert (dados["lote_id"], dados["resultado"]["lote_id"], dados["origem"]) == ("proc-1", "proc-1", "Discord · geral")


def test_abrir_lote_inexistente_da_404(oracle):
    assert cliente.get("/api/lotes/nao-existe").status_code == 404


def test_reprocessar_usa_chave_propria_para_criar_outro_lote(monkeypatch):
    chaves = []
    monkeypatch.setattr(main.database, "database_mode", lambda: "oracle")

    def iniciar(entrada, chave):
        chaves.append(chave)
        raise repository.ProcessingInProgress("parada proposital do teste")

    monkeypatch.setattr(repository, "iniciar_processamento", iniciar)
    lote = {"origem_comunidade": "Teste", "periodo_referencia": "2026-11", "interacoes": MENSAGENS}
    assert cliente.post("/processar", json=lote).status_code == 409
    assert cliente.post("/processar?reprocessar=true", json=lote).status_code == 409
    assert cliente.post("/processar?reprocessar=true", json=lote).status_code == 409
    normal, novo1, novo2 = chaves
    assert novo1.startswith(normal + ":") and novo2.startswith(normal + ":") and novo1 != novo2
    for chave in chaves:
        main._validar_chave_idempotencia(chave)


def test_insights_le_do_oracle_e_devolve_o_contrato_do_painel(oracle, monkeypatch):
    pedido = {}

    def interacoes(inicio, fim, modo, comunidades, canais):
        pedido.update(inicio=inicio, fim=fim, modo=modo, comunidades=comunidades, canais=canais)
        return [
            {"lote_id": "proc-1", "data": date(2026, 11, 3), "comunidade": "Discord · geral", "canal": "#geral",
             "sentimento": "Positivo", "topico": "Java", "rota": "faq"},
            {"lote_id": "proc-1", "data": date(2026, 11, 4), "comunidade": "Discord · geral", "canal": "#geral",
             "sentimento": "Negativo", "topico": "Prazo", "rota": "alerta"},
        ]

    monkeypatch.setattr(repository, "consultar_interacoes_insights", interacoes)
    monkeypatch.setattr(repository, "consultar_ativos_insights", lambda *a: [
        {"lote_id": "proc-1", "chave": "post", "tipo": "POST_LINKEDIN", "status": "aprovado"},
        {"lote_id": "proc-1", "chave": "faq_0", "tipo": "FAQ", "status": "pendente"},
    ])
    monkeypatch.setattr(repository, "opcoes_filtros_insights",
                        lambda modo: {"comunidades": ["Discord · geral"], "canais": ["#geral"]})
    monkeypatch.setattr(repository, "consultar_alertas_insights", lambda *a: [
        {"lote_id": "proc-1", "data": date(2026, 11, 4), "canal": "#geral", "autor": "Bia",
         "motivo": "Negativo em #geral: prazo", "status": "PENDENTE", "criado_em": None},
    ])

    r = cliente.get("/api/insights", params={"inicio": "2026-11-01", "fim": "2026-11-30", "modo": "mock",
                                             "canal": "#geral"})
    assert r.status_code == 200
    dados = r.json()
    assert pedido == {"inicio": date(2026, 11, 1), "fim": date(2026, 11, 30), "modo": "mock",
                      "comunidades": None, "canais": ["#geral"]}
    assert dados["banco_configurado"] is True and dados["modo_demo"] is False
    assert dados["numeros"]["total"] == 2
    assert dados["aproveitamento"] == {"gerados": 2, "aprovados": 1, "descartados": 0, "pendentes": 1}
    assert len(dados["sentimento_por_dia"]) == 2
    assert dados["opcoes"]["canais"] == ["#geral"]
    # Blocos novos da tela (painel web)
    assert dados["resumo"]["alertas_abertos"] == 1 and dados["resumo"]["saldo"] == 0.0
    assert dados["alertas_triagem"]["abertos"][0]["autor"] == "Bia"
    assert [p["inicio"] for p in dados["sentimento_no_tempo"]["pontos"]] == ["2026-11-03", "2026-11-04"]
    assert dados["periodo"] == {"inicio": "2026-11-01", "fim": "2026-11-30"}


def test_insights_sem_dados_no_oracle_nao_quebra(oracle, monkeypatch):
    monkeypatch.setattr(repository, "consultar_interacoes_insights", lambda *a: [])
    monkeypatch.setattr(repository, "consultar_ativos_insights", lambda *a: [])
    monkeypatch.setattr(repository, "opcoes_filtros_insights", lambda modo: {"comunidades": [], "canais": []})
    monkeypatch.setattr(repository, "consultar_alertas_insights", lambda *a: [])
    r = cliente.get("/api/insights")
    assert r.status_code == 200
    assert r.json()["aproveitamento"]["gerados"] == 0


def test_insights_com_data_invalida_e_recusado(oracle):
    assert cliente.get("/api/insights", params={"inicio": "03/11/2026"}).status_code == 422


def test_chave_automatica_e_estavel_e_muda_com_conteudo_e_modo(monkeypatch):
    lote = {"origem_comunidade": "X", "periodo_referencia": "2026-11", "interacoes": []}
    monkeypatch.setenv("LLM_MODO", "mock")
    chave = main._chave_idempotencia_automatica(lote)
    assert chave == main._chave_idempotencia_automatica(dict(lote))
    assert chave != main._chave_idempotencia_automatica({**lote, "periodo_referencia": "2026-12"})
    main._validar_chave_idempotencia(chave)  # no formato aceito pela API
    monkeypatch.setattr(main, "modo_mock", lambda: False)
    assert main._chave_idempotencia_automatica(lote) != chave


def test_processar_sem_oracle_continua_funcionando_e_avisa():
    lote = {"origem_comunidade": "Teste", "periodo_referencia": "Semana_teste_web_oracle",
            "interacoes": [{"autor": "Ana", "canal": "#geral", "texto": "Como configuro o Maven?"}]}
    r = cliente.post("/processar", json=lote)
    assert r.status_code == 200
    assert r.json()["persistencia"] == "desativada"
    assert r.json()["lote_id"] is None
