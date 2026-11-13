"""Testes do painel de curadoria (ui/). Rodam em modo simulado, sem abrir navegador.

    python -m pytest tests/test_painel.py -v
"""
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from ui import curadoria as cur  # noqa: E402
from ui.importacao import ler_arquivo  # noqa: E402

EXEMPLO = RAIZ / "data" / "interacoes_exemplo.json"
CSV = (
    "autor,canal,tipo,texto\n"
    "Ana Teste,#vagas,depoimento,Fui contratada como dev júnior! Muito grata\n"
    ",#duvidas,pergunta_tecnica,Como configuro o bucket?\n"
)


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_MODO", "mock")
    monkeypatch.delenv("OCI_NAMESPACE", raising=False)


# ---------------------------------------------------------------------------
# Importação
# ---------------------------------------------------------------------------
def test_json_do_exemplo_e_lido():
    leitura = ler_arquivo("interacoes_exemplo.json", EXEMPLO.read_bytes())
    assert leitura.ok and leitura.total == 12
    assert leitura.lote.periodo_referencia == "Semana_04"


def test_csv_utf8_e_lido_e_conta_anonimas():
    leitura = ler_arquivo("lote.csv", CSV.encode("utf-8"))
    assert leitura.ok, leitura.explicacao
    assert leitura.total == 2
    assert leitura.anonimas == 1
    assert leitura.lote.interacoes[0].texto.endswith("Muito grata")


def test_csv_utf8_com_bom_do_excel_e_lido():
    assert ler_arquivo("lote.csv", CSV.encode("utf-8-sig")).ok


def test_origem_e_periodo_informados_substituem_os_padroes():
    leitura = ler_arquivo("lote.csv", CSV.encode("utf-8"), origem="Forum", periodo="Semana_10")
    assert leitura.lote.origem_comunidade == "Forum"
    assert leitura.lote.periodo_referencia == "Semana_10"


def test_csv_com_ponto_e_virgula_explica_como_resolver():
    leitura = ler_arquivo("excel.csv", CSV.replace(",", ";").encode("utf-8"))
    assert not leitura.ok
    assert "ponto e vírgula" in leitura.titulo_erro
    assert any("CSV UTF-8" in p for p in leitura.passos)
    assert "autor;canal;tipo;texto" in leitura.evidencia


def test_csv_em_windows_1252_explica_como_resolver():
    leitura = ler_arquivo("antigo.csv", CSV.encode("cp1252"))
    assert not leitura.ok
    assert "UTF-8" in leitura.titulo_erro
    assert leitura.passos


def test_formato_nao_suportado():
    leitura = ler_arquivo("lote.xlsx", b"qualquer coisa")
    assert not leitura.ok and "não suportado" in leitura.titulo_erro


def test_csv_sem_coluna_obrigatoria_mostra_erro_do_adaptador():
    leitura = ler_arquivo("faltando.csv", "autor,texto\nAna,oi\n".encode("utf-8"))
    assert not leitura.ok
    assert leitura.explicacao


def test_json_quebrado_mostra_erro():
    leitura = ler_arquivo("lote.json", b'{"interacoes": [')
    assert not leitura.ok and "JSON" in leitura.explicacao


# ---------------------------------------------------------------------------
# Regras da curadoria
# ---------------------------------------------------------------------------
@pytest.fixture
def resultado():
    from app.grafo import processar
    return processar(ler_arquivo(EXEMPLO.name, EXEMPLO.read_bytes()).lote)


def test_ids_dos_ativos(resultado):
    ids = cur.ids_dos_ativos(resultado)
    assert ids[:2] == ["post", "newsletter"]
    assert ids[2:] == [f"faq_{i}" for i in range(len(resultado["ativos_distribuicao_gerados"]["sugestao_conteudo_faq"]))]


def test_membro_do_post_e_o_case_mais_relevante(resultado):
    membro = cur.membro_do_post(resultado)
    assert membro["rota"] == "case_sucesso"
    assert membro["autor"] in resultado["ativos_distribuicao_gerados"]["post_linkedin"]["copy"]
    assert membro not in cur.outros_cases(resultado)


def test_pacote_de_aprovados_usa_textos_editados(resultado):
    decisoes = {i: cur.PENDENTE for i in cur.ids_dos_ativos(resultado)}
    decisoes.update({"post": cur.APROVADO, "newsletter": cur.APROVADO, "faq_0": cur.APROVADO, "faq_1": cur.DESCARTADO})
    textos = {"post_copy": "Texto revisado", "news_chamada": "Chamada nova", "faq_0_conteudo": "Resposta revisada"}

    pacote = cur.montar_aprovados(resultado, decisoes, textos, "Discord", "Semana_04", autorizado=True)

    assert pacote["post_linkedin"]["copy"] == "Texto revisado"
    assert pacote["post_linkedin"]["autorizacao_membro"] is True
    assert pacote["destaque_newsletter_semanal"]["chamada"] == "Chamada nova"
    assert [f["conteudo"] for f in pacote["sugestao_conteudo_faq"]] == ["Resposta revisada"]
    assert pacote["descartados"] == ["faq_1"]


def test_post_sem_autorizacao_nao_e_exportado(resultado):
    with pytest.raises(ValueError):
        cur.montar_aprovados(resultado, {"post": cur.APROVADO}, {}, "D", "Semana_04", autorizado=False)


def test_aprovados_salvos_ao_lado_do_pacote(resultado):
    pacote = cur.montar_aprovados(resultado, {"newsletter": cur.APROVADO}, {}, "D", "Semana_04", autorizado=False)
    destino = cur.salvar_aprovados(pacote)
    assert destino.as_posix().endswith("ativos/" + destino.parent.name + "/aprovados.json")
    assert destino.parent.name.endswith("semana-04")
    assert json.loads(destino.read_text(encoding="utf-8"))["destaque_newsletter_semanal"]


# ---------------------------------------------------------------------------
# Painel completo, com cliques simulados
# ---------------------------------------------------------------------------
def _app(logado: bool = True):
    apptest = pytest.importorskip("streamlit.testing.v1")
    at = apptest.AppTest.from_file(str(RAIZ / "ui" / "painel.py"), default_timeout=60)
    if logado:
        at.session_state["logado"] = True
    return at


def _escolher_lote(at, fonte="Discord", canal="Grupo ONE G10"):
    at.selectbox(key="fonte").select(fonte).run()
    at.selectbox(key="canal").select(canal).run()
    return at


def _abrir(at, item):
    at.button(key=f"fila_{item}").click().run()


def _botao(at, rotulo):
    return next(b for b in at.button if b.label == rotulo)


def _processar_exemplo():
    at = _app().run()
    _botao(at, "Usar lote de exemplo").click().run()
    _escolher_lote(at)
    _botao(at, "Processar 12 interações").click().run()
    assert not at.exception
    return at


def test_painel_abre_na_importacao():
    at = _app().run()
    assert not at.exception
    assert at.radio(key="pagina").value == "Importar"
    assert _botao(at, "Envie um arquivo válido para processar").disabled


def test_exemplo_processado_vai_para_visao_geral():
    at = _processar_exemplo()
    assert at.radio(key="pagina").value == "Visão geral"
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Interações processadas"] == "12"
    assert metricas["Membros que precisam de apoio"] == "2"
    assert metricas["Ativos para aprovar"] == str(2 + 5)  # post + newsletter + 5 FAQ


def test_filtro_de_rota_na_tabela():
    at = _processar_exemplo()
    at.radio(key="filtro_rota").set_value("Alerta").run()
    tabela = at.dataframe[0].value
    assert set(tabela["Rota"]) == {"Alerta"} and len(tabela) == 2


def test_alerta_tratado_sai_da_contagem():
    at = _processar_exemplo()
    at.button(key="al_0_ok").click().run()
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Membros que precisam de apoio"] == "1"


def test_curadoria_exige_autorizacao_e_exporta_texto_editado(tmp_path):
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    assert at.radio(key="pagina").value == "Curadoria"
    assert not at.exception

    assert at.button(key="dec_post_a").disabled, "post não pode ser aprovado sem autorização"
    at.checkbox(key="autorizado").check().run()
    at.text_area(key="txt_post_copy").input("Post revisado pela equipe").run()
    at.button(key="dec_post_a").click().run()
    at.text_input(key="txt_news_chamada").input("Chamada revisada").run()
    at.button(key="dec_newsletter_a").click().run()
    at.button(key="dec_faq_0_d").click().run()

    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Aprovados"] == "2" and metricas["Descartados"] == "1"

    _botao(at, "Exportar aprovados").click().run()
    assert not at.exception
    salvo = json.loads(next(tmp_path.glob("saida_local/ativos/*/aprovados.json")).read_text(encoding="utf-8"))
    assert salvo["post_linkedin"]["copy"] == "Post revisado pela equipe"
    assert salvo["destaque_newsletter_semanal"]["chamada"] == "Chamada revisada"
    assert salvo["descartados"] == ["faq_0"]


def test_desmarcar_autorizacao_devolve_post_para_pendente():
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    assert at.radio(key="pagina").value == "Curadoria"
    at.checkbox(key="autorizado").check().run()
    at.button(key="dec_post_a").click().run()
    _abrir(at, "post")
    at.checkbox(key="autorizado").uncheck().run()
    assert at.button(key="dec_post_a").disabled


def test_textos_do_ativo():
    textos = {"post_copy": "P", "news_chamada": "C", "news_resumo": "R", "faq_0_conteudo": "F0", "faq_1_conteudo": "F1"}
    assert cur.textos_do_ativo("post", textos) == {"post_copy": "P"}
    assert cur.textos_do_ativo("newsletter", textos) == {"news_chamada": "C", "news_resumo": "R"}
    assert cur.textos_do_ativo("faq_1", textos) == {"faq_1_conteudo": "F1"}


def test_dois_alertas_da_mesma_pessoa_sao_independentes():
    lote = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    lote["interacoes"][10]["autor"] = "Juliana Prado"
    from app.grafo import processar
    from app.schemas import LoteEntrada
    at = _app()
    at.session_state["resultado"] = processar(LoteEntrada(**lote))
    at.session_state["decisoes"] = {}
    at.session_state["pagina"] = "Visão geral"
    at.run()
    at.button(key="al_0_ok").click().run()
    assert {m.label: m.value for m in at.metric}["Membros que precisam de apoio"] == "1"


def test_decisao_e_gravada_quando_ha_lote(monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.repositorio.salvar_decisao", lambda *a, **k: chamadas.append((a, k)))
    at = _processar_exemplo()
    at.session_state["lote_id"] = 7
    _botao(at, "Revisar 7 ativos").click().run()
    _abrir(at, "newsletter")
    at.text_input(key="txt_news_chamada").input("Chamada revisada").run()
    at.button(key="dec_newsletter_a").click().run()
    (args, kwargs), = chamadas
    assert args[:3] == (7, "newsletter", "a") and args[3]["news_chamada"] == "Chamada revisada"


def test_decisao_sem_lote_nao_chama_o_banco(monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.repositorio.salvar_decisao", lambda *a, **k: chamadas.append((a, k)))
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    _abrir(at, "newsletter")
    at.button(key="dec_newsletter_a").click().run()
    assert chamadas == [] and at.session_state["decisoes"]["newsletter"] == cur.APROVADO


def test_falha_ao_gravar_decisao_vira_aviso(monkeypatch):
    def falha(*a, **k):
        raise RuntimeError("conexão caiu")
    monkeypatch.setattr("app.repositorio.salvar_decisao", falha)
    at = _processar_exemplo()
    at.session_state["lote_id"] = 7
    _botao(at, "Revisar 7 ativos").click().run()
    _abrir(at, "newsletter")
    at.button(key="dec_newsletter_a").click().run()
    assert not at.exception
    assert at.session_state["decisoes"]["newsletter"] == cur.APROVADO
    assert any("conexão caiu" in w.value for w in at.warning)


def test_alertas_gravam_status_no_banco(monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.repositorio.atualizar_alerta", lambda *a, **k: chamadas.append(a))
    at = _processar_exemplo()
    at.session_state["lote_id"] = 7
    at.run()
    analises = at.session_state["resultado"]["analises"]
    ordens = [n for n, a in enumerate(analises) if a["rota"] == "alerta"]
    at.button(key="al_0_acao").click().run()
    at.button(key="al_1_ok").click().run()
    status_acao = "encaminhado" if analises[ordens[0]]["tipo"] == "reclamacao" else "mentoria_oferecida"
    assert chamadas == [(7, ordens[0], status_acao), (7, ordens[1], "resolvido")]
    assert at.session_state["alertas"] == {ordens[0]: status_acao, ordens[1]: "resolvido"}
    assert {m.label: m.value for m in at.metric}["Membros que precisam de apoio"] == "0"


def test_falha_ao_gravar_alerta_vira_aviso(monkeypatch):
    def falha(*a, **k):
        raise RuntimeError("conexão caiu")
    monkeypatch.setattr("app.repositorio.atualizar_alerta", falha)
    at = _processar_exemplo()
    at.session_state["lote_id"] = 7
    at.run()
    at.button(key="al_0_ok").click().run()
    assert not at.exception
    assert any("conexão caiu" in w.value for w in at.warning)


def test_texto_editado_continua_ao_voltar_para_curadoria():
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    _abrir(at, "newsletter")
    at.text_input(key="txt_news_chamada").input("Chamada revisada").run()
    at.radio(key="pagina").set_value("Visão geral").run()
    at.radio(key="pagina").set_value("Curadoria").run()
    assert not at.exception
    assert at.text_input(key="txt_news_chamada").value == "Chamada revisada"


def _na_tela(campo):
    """O que o navegador mostra: o valor enviado pelo servidor ou, sem ele, o valor padrão do campo."""
    return campo.proto.value if campo.proto.set_value else campo.proto.default


def test_textos_aparecem_na_tela_ao_voltar_para_curadoria():
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    post = at.text_area(key="txt_post_copy").value
    at.radio(key="pagina").set_value("Visão geral").run()
    at.radio(key="pagina").set_value("Curadoria").run()
    assert not at.exception
    assert not at.warning
    assert _na_tela(at.text_area(key="txt_post_copy")) == post
    _abrir(at, "newsletter")
    at.text_input(key="txt_news_chamada").input("Chamada revisada").run()
    at.radio(key="pagina").set_value("Visão geral").run()
    at.radio(key="pagina").set_value("Curadoria").run()
    assert not at.warning
    assert _na_tela(at.text_input(key="txt_news_chamada")) == "Chamada revisada"


def test_fila_mostra_um_item_por_vez():
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    assert [c.key for c in at.text_area] == ["txt_post_copy"]
    _abrir(at, "faq_1")
    assert [c.key for c in at.text_area] == ["txt_faq_1_conteudo"]
    assert not at.exception


def test_texto_editado_sobrevive_a_troca_de_item_e_chega_na_exportacao(tmp_path):
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    at.text_area(key="txt_post_copy").input("Post revisado").run()
    at.checkbox(key="autorizado").check().run()
    _abrir(at, "faq_0")
    at.text_area(key="txt_faq_0_conteudo").input("FAQ revisada").run()
    _abrir(at, "newsletter")
    at.text_input(key="txt_news_chamada").input("Chamada revisada").run()
    _abrir(at, "faq_2")  # sai de todos os itens editados antes de voltar
    assert not at.warning

    _abrir(at, "post")
    assert _na_tela(at.text_area(key="txt_post_copy")) == "Post revisado"
    assert at.checkbox(key="autorizado").value
    at.button(key="dec_post_a").click().run()
    _abrir(at, "faq_0")
    assert _na_tela(at.text_area(key="txt_faq_0_conteudo")) == "FAQ revisada"
    at.button(key="dec_faq_0_a").click().run()
    _abrir(at, "newsletter")
    assert _na_tela(at.text_input(key="txt_news_chamada")) == "Chamada revisada"
    at.button(key="dec_newsletter_a").click().run()

    _botao(at, "Exportar aprovados").click().run()
    assert not at.exception
    salvo = json.loads(next(tmp_path.glob("saida_local/ativos/*/aprovados.json")).read_text(encoding="utf-8"))
    assert salvo["post_linkedin"]["copy"] == "Post revisado"
    assert salvo["destaque_newsletter_semanal"]["chamada"] == "Chamada revisada"
    assert salvo["sugestao_conteudo_faq"][0]["conteudo"] == "FAQ revisada"


def test_decidir_avanca_para_o_proximo_pendente_e_desfazer_fica_no_item():
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    _abrir(at, "newsletter")
    at.button(key="dec_newsletter_a").click().run()
    assert at.session_state["item_ativo"] == "faq_0"
    at.button(key="dec_faq_0_d").click().run()
    assert at.session_state["item_ativo"] == "faq_1"
    _abrir(at, "faq_0")
    at.button(key="dec_faq_0_u").click().run()
    assert at.session_state["item_ativo"] == "faq_0"


def test_proximo_pendente_da_a_volta_na_fila():
    ids = ["post", "newsletter", "faq_0"]
    decisoes = {"post": cur.PENDENTE, "newsletter": cur.APROVADO, "faq_0": cur.DESCARTADO}
    assert cur.proximo_pendente(ids, decisoes, "faq_0") == "post"
    assert cur.proximo_pendente(ids, decisoes) == "post"
    assert cur.proximo_pendente(ids, {i: cur.APROVADO for i in ids}, "post") is None


def test_titulo_na_fila_tira_o_prefixo_repetido_da_faq():
    resultado = {"ativos_distribuicao_gerados": {
        "post_linkedin": {"titulo": "Conquista"},
        "destaque_newsletter_semanal": {"secao": "Destaques"},
        "sugestao_conteudo_faq": [{"tema": "Dica Rápida: OCID na OCI"}],
    }}
    assert cur.titulo_na_fila(resultado, "post") == "Post: Conquista"
    assert cur.titulo_na_fila(resultado, "newsletter") == "Newsletter: Destaques"
    assert cur.titulo_na_fila(resultado, "faq_0") == "OCID na OCI"


def _contraste(cor_a: str, cor_b: str) -> float:
    def luminancia(cor):
        canais = [int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    clara, escura = sorted((luminancia(cor_a), luminancia(cor_b)), reverse=True)
    return (clara + 0.05) / (escura + 0.05)


@pytest.mark.parametrize("indice,tema", [(0, "claro"), (1, "escuro")])
def test_textos_tem_contraste_legivel_nos_dois_temas(indice, tema):
    from ui import estilo
    for fundo in ("fundo", "superficie"):
        for nome in ("texto", "cinza", "lima", "ciano", "laranja", "rosa"):
            razao = _contraste(estilo.CORES[nome][indice], estilo.CORES[fundo][indice])
            assert razao >= 4.5, f"{nome} sobre {fundo} no tema {tema}: {razao:.1f}"


def test_html_troca_de_tema_sozinho():
    from ui import estilo
    claro, escuro = estilo.CORES["texto"]
    assert estilo.css("texto") == f"light-dark({claro}, {escuro})"


def test_cores_dos_dados_aparecem_nos_dois_fundos():
    from ui import estilo
    dados = [c for _, c in estilo.SENTIMENTOS] + [r["barra"] for r in estilo.ROTAS.values()] + [estilo.DADO_DESCARTADO]
    for cor in dados:
        for fundo in estilo.CORES["fundo"]:
            assert _contraste(cor, fundo) >= 2.5, f"{cor} sobre {fundo}"


def test_numeros_dentro_dos_graficos_sao_legiveis_nos_dois_fundos():
    from ui import estilo
    for fundo in estilo.CORES["fundo"]:
        assert _contraste(estilo.DADO_TEXTO, fundo) >= 3.5


def test_post_aprovado_continua_ao_voltar_para_curadoria():
    at = _processar_exemplo()
    _botao(at, "Revisar 7 ativos").click().run()
    at.checkbox(key="autorizado").check().run()
    at.button(key="dec_post_a").click().run()
    at.radio(key="pagina").set_value("Visão geral").run()
    at.radio(key="pagina").set_value("Curadoria").run()
    _abrir(at, "post")
    assert at.checkbox(key="autorizado").value
    assert at.session_state["decisoes"]["post"] == cur.APROVADO


def test_mensagem_com_html_nao_vira_codigo(tmp_path):
    lote = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    lote["interacoes"][6]["texto"] = "<script>alert(1)</script> estou pensando em desistir"
    arquivo = tmp_path / "malicioso.json"
    arquivo.write_text(json.dumps(lote, ensure_ascii=False), encoding="utf-8")

    from app.grafo import processar
    at = _app()
    at.session_state["resultado"] = processar(ler_arquivo(arquivo.name, arquivo.read_bytes()).lote)
    at.session_state["decisoes"] = {}
    at.session_state["pagina"] = "Visão geral"
    at.run()
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_fonte_canal_e_mes_continuam_ao_voltar_para_importar():
    at = _app().run()
    _botao(at, "Usar lote de exemplo").click().run()
    _escolher_lote(at, "Telegram", "Vagas Tech")
    at.selectbox(key="mes").select(3).run()
    _botao(at, "Processar 12 interações").click().run()
    at.radio(key="pagina").set_value("Importar").run()
    assert at.selectbox(key="fonte").value == "Telegram"
    assert at.selectbox(key="canal").value == "Vagas Tech"
    assert at.selectbox(key="mes").value == 3


def test_lote_comeca_sem_fonte_e_no_mes_atual():
    from datetime import date
    at = _app().run()
    assert at.selectbox(key="fonte").value is None
    assert at.selectbox(key="mes").value == date.today().month
    assert at.selectbox(key="ano").value == date.today().year
    assert not any(s.key == "canal" for s in at.selectbox), "canal só aparece depois da fonte"


def test_canal_mostra_so_os_da_fonte_escolhida():
    from ui.fontes import CANAIS
    at = _app().run()
    at.selectbox(key="fonte").select("WhatsApp").run()
    assert at.selectbox(key="canal").options == CANAIS["WhatsApp"]
    assert at.selectbox(key="canal").value is None


def test_trocar_a_fonte_limpa_o_canal():
    at = _escolher_lote(_app().run(), "Discord", "Dev Brasil")
    at.selectbox(key="fonte").select("Telegram").run()
    assert at.selectbox(key="canal").value is None


def test_processar_exige_fonte_e_canal():
    at = _app().run()
    _botao(at, "Usar lote de exemplo").click().run()
    assert _botao(at, "Escolha a fonte e o canal para processar").disabled
    at.selectbox(key="fonte").select("Discord").run()
    assert _botao(at, "Escolha a fonte e o canal para processar").disabled
    at.selectbox(key="canal").select("Dev Brasil").run()
    assert not _botao(at, "Processar 12 interações").disabled


def test_lote_salvo_com_a_comunidade_e_o_mes_escolhidos():
    from datetime import date
    at = _app().run()
    _botao(at, "Usar lote de exemplo").click().run()
    _escolher_lote(at, "Arquivo manual", "Pesquisa de satisfação")
    at.selectbox(key="mes").select(2).run()
    at.selectbox(key="ano").select(date.today().year - 1).run()
    _botao(at, "Processar 12 interações").click().run()
    assert at.session_state["lote_origem"] == "Arquivo manual · Pesquisa de satisfação"
    assert at.session_state["lote_periodo"] == f"{date.today().year - 1}-02"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "segredo")


def _entrar(at, usuario, senha):
    at.text_input(key="login_usuario").input(usuario)
    at.text_input(key="login_senha").input(senha)
    _botao(at, "Entrar").click().run()
    return at


def test_sem_login_mostra_so_a_tela_de_login(admin):
    at = _app(logado=False).run()
    assert not at.exception
    assert not any(r.key == "pagina" for r in at.radio)
    assert any(b.label == "Entrar" for b in at.button)


def test_login_certo_abre_a_importacao(admin):
    at = _entrar(_app(logado=False).run(), "admin", "segredo")
    assert not at.exception
    assert at.radio(key="pagina").value == "Importar"


def test_login_errado_avisa_e_continua_bloqueado(admin):
    at = _entrar(_app(logado=False).run(), "admin", "errada")
    assert any("Usuário ou senha inválidos" in e.value for e in at.error)
    assert not any(r.key == "pagina" for r in at.radio)


def test_sem_admin_no_env_avisa_e_nao_deixa_entrar(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "")
    monkeypatch.setenv("ADMIN_SENHA", "")
    at = _app(logado=False).run()
    assert any("ADMIN_USUARIO" in w.value for w in at.warning)
    assert _botao(at, "Entrar").disabled


def test_sair_volta_para_o_login(admin):
    at = _processar_exemplo()
    _botao(at, "Sair").click().run()
    assert not any(r.key == "pagina" for r in at.radio)
    assert any(b.label == "Entrar" for b in at.button)
    assert not at.session_state["logado"]


# ---------------------------------------------------------------------------
# Histórico no banco (duplicado, abrir resultado existente)
# ---------------------------------------------------------------------------
def test_sem_banco_processa_sem_aviso_de_duplicado():
    at = _processar_exemplo()
    assert not any(b.label == "Abrir resultado existente" for b in at.button)
    assert at.session_state["lote_id"] is None


def test_falha_do_banco_mostra_aviso_e_segue(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://usuario:errada@127.0.0.1:1/postgres")
    at = _processar_exemplo()
    assert at.radio(key="pagina").value == "Visão geral"
    assert any("não foi salvo no histórico" in w.value for w in at.warning)


def _com_duplicado():
    from datetime import datetime, timezone
    at = _app().run()
    _botao(at, "Usar lote de exemplo").click().run()
    _escolher_lote(at)
    at.session_state["duplicado"] = {"id": 999, "processado_em": datetime.now(timezone.utc), "total_interacoes": 12}
    return at.run()


def test_falha_ao_abrir_resultado_existente_avisa_e_fica_em_importar(monkeypatch):
    from app import repositorio

    def falha(lote_id):
        raise RuntimeError("conexão caiu")
    monkeypatch.setattr(repositorio, "carregar_lote", falha)
    at = _com_duplicado()
    assert any("já foi processado" in w.value for w in at.warning)
    _botao(at, "Abrir resultado existente").click().run()
    assert not at.exception
    assert at.radio(key="pagina").value == "Importar"
    assert any("Não foi possível abrir o resultado salvo" in w.value for w in at.warning)


def test_mudar_origem_descarta_aviso_de_duplicado():
    at = _com_duplicado()
    at.selectbox(key="fonte").select("Telegram").run()
    assert not any("já foi processado" in w.value for w in at.warning)
    assert at.session_state["duplicado"] is None


@pytest.mark.real
def test_duplicado_oferece_abrir_ou_substituir(banco_real_painel, monkeypatch):
    from ui import fontes
    monkeypatch.setitem(fontes.CANAIS, "Discord", [banco_real_painel])  # comunidade só de teste, apagada no fim
    at = _app().run()
    _botao(at, "Usar lote de exemplo").click().run()
    _escolher_lote(at, "Discord", banco_real_painel)
    _botao(at, "Processar 12 interações").click().run()
    at.radio(key="pagina").set_value("Importar").run()
    _botao(at, "Processar 12 interações").click().run()
    assert any("já foi processado" in w.value for w in at.warning)
    _botao(at, "Abrir resultado existente").click().run()
    assert at.radio(key="pagina").value == "Visão geral" and not at.exception


# ---------------------------------------------------------------------------
# Insights (histórico)
# ---------------------------------------------------------------------------
def _ativos_exemplo():
    import pandas as pd
    return pd.DataFrame({"lote_id": [1], "chave": ["post"], "tipo": ["post_linkedin"], "status": ["aprovado"], "canal": ["#a"]})


def _banco_com(monkeypatch, interacoes, chamadas=None):
    """Liga o "banco" com as consultas trocadas por dados fixos; `chamadas` recebe os argumentos usados."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    def consultar(*a, **k):
        if chamadas is not None:
            chamadas.append((a, k))
        return interacoes()
    monkeypatch.setattr("app.repositorio.opcoes_filtros", lambda modo: {"comunidades": ["C"], "canais": ["#a", "#b"]})
    monkeypatch.setattr("app.repositorio.consultar_interacoes", consultar)
    monkeypatch.setattr("app.repositorio.consultar_ativos", lambda *a, **k: _ativos_exemplo())


def _insights():
    at = _app().run()
    at.radio(key="pagina").set_value("Insights").run()
    assert not at.exception
    return at


def test_insights_sem_banco_explica_como_configurar(monkeypatch):
    def nao_chamar(*a, **k):
        raise AssertionError("sem banco a tela não consulta nada")
    monkeypatch.setattr("app.repositorio.consultar_interacoes", nao_chamar)
    monkeypatch.setattr("app.repositorio.opcoes_filtros", nao_chamar)
    at = _insights()
    assert any("DATABASE_URL" in i.value for i in at.info)


def test_insights_com_dados_mostra_numeros(monkeypatch):
    from tests.dados_insights import df_exemplo
    _banco_com(monkeypatch, df_exemplo)
    at = _insights()
    numeros = {m.label: m.value for m in at.metric}
    assert numeros["Interações"] == "6"
    assert numeros["Positivas"] == "50,0%"
    assert numeros["Negativas"] == "33,3%"
    assert numeros["Alertas"] == "1"
    assert len(at.get("vega_lite_chart")) == 6
    assert any("mensagens, não pessoas" in c.value for c in at.caption)
    assert not at.warning


def test_insights_comeca_no_modo_do_app_sem_filtros_e_muda_de_modo(monkeypatch):
    from tests.dados_insights import df_exemplo
    chamadas = []
    _banco_com(monkeypatch, df_exemplo, chamadas)
    at = _insights()
    (inicio, fim, modo), filtros = chamadas[-1]
    assert modo == "mock" and (fim - inicio).days == 56
    assert not filtros.get("comunidades") and not filtros.get("canais")
    at.radio(key="ins_modo").set_value("Claude").run()
    at.multiselect(key="ins_canais").select("#a").run()
    (_, _, modo), filtros = chamadas[-1]
    assert modo == "gemini" and filtros["canais"] == ["#a"]


def test_insights_comeca_no_gemini_quando_o_app_usa_gemini(monkeypatch):
    from tests.dados_insights import df_exemplo
    chamadas = []
    monkeypatch.setenv("LLM_MODO", "")  # vazio, e não apagado, para o load_dotenv não trazer o do .env
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-de-teste")
    _banco_com(monkeypatch, df_exemplo, chamadas)
    _insights()
    (_, _, modo), _ = chamadas[-1]
    assert modo == "gemini"


def test_insights_com_canal_filtrado_avisa_sobre_newsletter(monkeypatch):
    from tests.dados_insights import df_exemplo
    _banco_com(monkeypatch, df_exemplo)
    at = _insights()
    aviso = "A newsletter não tem canal de origem"
    assert not any(aviso in c.value for c in at.caption)
    at.multiselect(key="ins_canais").select("#a").run()
    assert not at.exception
    assert any(aviso in c.value for c in at.caption)


def test_insights_sem_mensagens_no_periodo(monkeypatch):
    from tests.dados_insights import vazio
    _banco_com(monkeypatch, vazio)
    at = _insights()
    assert any("Nenhuma mensagem nesse período" in i.value for i in at.info)
    assert not at.metric


def test_insights_falha_de_conexao_vira_aviso(monkeypatch):
    def falha(*a, **k):
        raise RuntimeError("conexão recusada")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setattr("app.repositorio.opcoes_filtros", falha)
    at = _insights()
    assert any("conexão recusada" in w.value for w in at.warning)


def test_lote_substituido_vira_aviso_e_para_de_tentar(monkeypatch):
    def substituido(*a, **k):
        raise LookupError("Este lote foi substituído no histórico; reabra-o pelo Importar.")
    monkeypatch.setattr("app.repositorio.salvar_decisao", substituido)
    at = _processar_exemplo()
    at.session_state["lote_id"] = 7
    _botao(at, "Revisar 7 ativos").click().run()
    _abrir(at, "newsletter")
    at.button(key="dec_newsletter_a").click().run()
    assert not at.exception
    assert at.session_state["lote_id"] is None
    assert any("substituído" in w.value for w in at.warning)


def test_aviso_some_quando_a_gravacao_volta(monkeypatch):
    chamadas = iter([RuntimeError("conexão caiu"), None])

    def salvar(*a, **k):
        r = next(chamadas)
        if r:
            raise r
    monkeypatch.setattr("app.repositorio.salvar_decisao", salvar)
    at = _processar_exemplo()
    at.session_state["lote_id"] = 7
    _botao(at, "Revisar 7 ativos").click().run()
    _abrir(at, "newsletter")
    at.button(key="dec_newsletter_a").click().run()
    assert at.session_state["aviso_banco"]
    _abrir(at, "newsletter")
    at.button(key="dec_newsletter_u").click().run()
    assert at.session_state["aviso_banco"] is None


# ---------------------------------------------------------------------------
# Desempenho
# ---------------------------------------------------------------------------
def test_abrir_o_painel_nao_carrega_o_pipeline():
    """O LangGraph leva segundos para importar; só deve carregar ao processar um lote."""
    import subprocess
    codigo = (
        "import sys\n"
        "from streamlit.testing.v1 import AppTest\n"
        f"at = AppTest.from_file({str(RAIZ / 'ui' / 'painel.py')!r}, default_timeout=60)\n"
        "at.session_state['logado'] = True\n"
        "at.run()\n"
        "assert not at.exception, at.exception\n"
        "print('langgraph' in sys.modules)\n"
    )
    saida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, cwd=RAIZ, timeout=120)
    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip().splitlines()[-1] == "False"
