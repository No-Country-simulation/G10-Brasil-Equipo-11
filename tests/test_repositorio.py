import json
import os
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import psycopg
import pytest

import ui.curadoria as cur
from app import grafo, repositorio
from app.grafo import processar
from app.schemas import LoteEntrada

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_MODO", "mock")
    monkeypatch.delenv("OCI_NAMESPACE", raising=False)


@pytest.fixture
def lote_exemplo():
    dados = json.loads((RAIZ / "data" / "interacoes_exemplo.json").read_text(encoding="utf-8"))
    return LoteEntrada(**dados)


@pytest.fixture
def resposta(lote_exemplo):
    return processar(lote_exemplo)


def test_testes_simulados_nunca_veem_o_banco():
    assert os.environ.get("DATABASE_URL") == ""


def test_banco_configurado_ignora_vazio(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  ")
    assert repositorio.banco_configurado() is False
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:s@h:5432/postgres")
    assert repositorio.banco_configurado() is True


def test_hash_ignora_ordem_espacos_e_forma_unicode(lote_exemplo):
    base = repositorio.hash_conteudo(lote_exemplo)
    invertido = lote_exemplo.model_copy(update={"interacoes": list(reversed(lote_exemplo.interacoes))})
    sujo = lote_exemplo.model_copy(update={"interacoes": [
        i.model_copy(update={"texto": "  " + unicodedata.normalize("NFD", i.texto) + "\n"})
        for i in lote_exemplo.interacoes]})
    assert len(base) == 64
    assert repositorio.hash_conteudo(invertido) == base
    assert repositorio.hash_conteudo(sujo) == base


def test_hash_ignora_periodo_mas_nao_comunidade(lote_exemplo):
    base = repositorio.hash_conteudo(lote_exemplo)
    assert repositorio.hash_conteudo(lote_exemplo.model_copy(update={"periodo_referencia": "Semana_99"})) == base
    assert repositorio.hash_conteudo(lote_exemplo.model_copy(update={"origem_comunidade": "Outra"})) != base


def test_hash_muda_quando_um_texto_muda(lote_exemplo):
    interacoes = list(lote_exemplo.interacoes)
    interacoes[0] = interacoes[0].model_copy(update={"texto": "outro texto"})
    assert repositorio.hash_conteudo(lote_exemplo.model_copy(update={"interacoes": interacoes})) != repositorio.hash_conteudo(lote_exemplo)


def test_linhas_do_lote(lote_exemplo, resposta):
    linhas = repositorio.linhas_do_lote(lote_exemplo, resposta)
    assert [l["ordem"] for l in linhas["interacoes"]] == list(range(12))
    assert linhas["interacoes"][0]["texto"] == lote_exemplo.interacoes[0].texto
    assert linhas["interacoes"][6]["rota"] == "alerta"
    ativos = {a["chave"]: a for a in linhas["ativos"]}
    assert list(ativos)[:2] == ["post", "newsletter"]
    assert ativos["post"]["tipo"] == "post_linkedin"
    assert ativos["post"]["conteudo_gerado"] == resposta["ativos_distribuicao_gerados"]["post_linkedin"]
    assert resposta["analises"][ativos["post"]["ordem_origem"]] == cur.membro_do_post(resposta)
    assert ativos["newsletter"]["ordem_origem"] is None
    assert resposta["analises"][ativos["faq_1"]["ordem_origem"]] == cur.duvida_da_faq(resposta, 1)
    assert [(a["ordem"], a["autor"]) for a in linhas["alertas"]] == [(6, "Juliana Prado"), (10, "Fernanda Castro")]


def test_linhas_sem_case_nao_tem_post(lote_exemplo):
    so_duvida = lote_exemplo.model_copy(update={"interacoes": [lote_exemplo.interacoes[1]]})
    linhas = repositorio.linhas_do_lote(so_duvida, processar(so_duvida))
    assert [a["chave"] for a in linhas["ativos"]] == ["newsletter", "faq_0"]
    assert linhas["alertas"] == []


@pytest.fixture
def lote_real(lote_exemplo, banco_real):
    return lote_exemplo.model_copy(update={"origem_comunidade": banco_real})


@pytest.fixture
def resposta_real(lote_real):
    return processar(lote_real)


def _linhas_na_view(comunidade):
    with repositorio.conectar() as conn:
        return conn.execute("select count(*) from vw_interacoes_analisadas where comunidade = %s",
                            (comunidade,)).fetchone()[0]


@pytest.mark.real
def test_gravar_e_carregar_lote(banco_real, lote_real, resposta_real):
    lote_id = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    achado = repositorio.buscar_lote(repositorio.hash_conteudo(lote_real), "mock")
    assert achado["id"] == lote_id and achado["total_interacoes"] == 12
    carregado = repositorio.carregar_lote(lote_id)
    assert carregado["resposta"] == resposta_real
    assert carregado["decisoes"] == {c: "p" for c in cur.ids_dos_ativos(resposta_real)}
    assert carregado["alertas"] == {} and carregado["autorizado"] is False
    assert carregado["origem"] == banco_real and carregado["periodo"] == lote_real.periodo_referencia


@pytest.mark.real
def test_reprocessar_no_mesmo_modo_substitui(banco_real, lote_real, resposta_real):
    primeiro = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    segundo = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    assert segundo != primeiro
    assert repositorio.buscar_lote(repositorio.hash_conteudo(lote_real), "mock")["id"] == segundo
    assert _linhas_na_view(banco_real) == 12


@pytest.mark.real
def test_mock_e_gemini_nao_se_substituem(banco_real, lote_real, resposta_real):
    h = repositorio.hash_conteudo(lote_real)
    a = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    b = repositorio.gravar_lote(lote_real, resposta_real, "gemini")
    assert repositorio.buscar_lote(h, "mock")["id"] == a
    assert repositorio.buscar_lote(h, "gemini")["id"] == b


@pytest.mark.real
def test_decisoes_e_alertas_sao_restaurados(banco_real, lote_real, resposta_real):
    lote_id = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    repositorio.salvar_decisao(lote_id, "post", "a", {"post_copy": "Revisado"}, autorizacao=True)
    repositorio.salvar_decisao(lote_id, "faq_0", "d", {}, autorizacao=True)
    repositorio.atualizar_alerta(lote_id, 6, "resolvido")
    c = repositorio.carregar_lote(lote_id)
    assert c["decisoes"]["post"] == "a" and c["decisoes"]["faq_0"] == "d"
    assert c["textos"]["post_copy"] == "Revisado" and c["autorizado"] is True
    assert c["alertas"] == {6: "resolvido"}


@pytest.mark.real
def test_voltar_para_pendente_limpa_revisao(banco_real, lote_real, resposta_real):
    lote_id = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    repositorio.salvar_decisao(lote_id, "faq_0", "a", {}, autorizacao=False)
    repositorio.salvar_decisao(lote_id, "faq_0", "p", {}, autorizacao=False)
    with repositorio.conectar() as conn:
        rev = conn.execute("select revisado_em from ativos where lote_id = %s and chave = 'faq_0'",
                           (lote_id,)).fetchone()[0]
    assert rev is None


@pytest.mark.real
def test_post_aprovado_sem_autorizacao_e_recusado_pelo_banco(banco_real, lote_real, resposta_real):
    lote_id = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    with pytest.raises(psycopg.errors.CheckViolation):
        repositorio.salvar_decisao(lote_id, "post", "a", {}, autorizacao=False)


def test_sem_banco_nao_tenta_gravar(lote_exemplo, monkeypatch):
    monkeypatch.setattr(repositorio, "gravar_lote", lambda *a: pytest.fail("não devia gravar"))
    resposta, registro = grafo.processar_com_registro(lote_exemplo)
    assert registro == {"lote_id": None, "erro": None}
    assert resposta["status"] == "sucesso"


def test_falha_do_banco_nao_derruba_o_processamento(lote_exemplo, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    def explode(*a):
        raise RuntimeError("senha errada")

    monkeypatch.setattr(repositorio, "gravar_lote", explode)
    resposta, registro = grafo.processar_com_registro(lote_exemplo)
    assert registro == {"lote_id": None, "erro": "senha errada"}
    assert resposta["resumo_comunidade"]["total_interacoes_processadas"] == 12
    assert "[Supabase]" in capsys.readouterr().out


def test_processar_grava_com_o_modo_atual(lote_exemplo, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    chamadas = []
    monkeypatch.setattr(repositorio, "gravar_lote", lambda l, r, m: chamadas.append(m) or 42)
    assert grafo.processar_com_registro(lote_exemplo)[1] == {"lote_id": 42, "erro": None}
    assert grafo.processar(lote_exemplo)["status"] == "sucesso"
    assert chamadas == ["mock", "mock"]


@pytest.mark.real
def test_consultar_interacoes_filtra_modo_canal_e_periodo(banco_real, lote_real, resposta_real):
    comunidade = banco_real
    repositorio.gravar_lote(lote_real, resposta_real, "mock")
    hoje = date.today()
    df = repositorio.consultar_interacoes(hoje, hoje, "mock", comunidades=[comunidade])
    assert len(df) == 12 and set(df["comunidade"]) == {comunidade}
    assert repositorio.consultar_interacoes(hoje, hoje, "gemini", comunidades=[comunidade]).empty
    so_geral = repositorio.consultar_interacoes(hoje, hoje, "mock", [comunidade], ["#geral"])
    assert set(so_geral["canal"]) == {"#geral"} and len(so_geral) == 2
    assert repositorio.consultar_interacoes(
        hoje - timedelta(days=30), hoje - timedelta(days=1), "mock", [comunidade]).empty


@pytest.mark.real
def test_consultar_ativos_com_canal_tira_a_newsletter(banco_real, lote_real, resposta_real):
    comunidade = banco_real
    lote_id = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    repositorio.salvar_decisao(lote_id, "newsletter", "a", {}, autorizacao=False)
    hoje = date.today()
    todos = repositorio.consultar_ativos(hoje, hoje, "mock", [comunidade])
    assert len(todos) == 7 and todos.set_index("chave").loc["newsletter", "status"] == "aprovado"
    duvidas = repositorio.consultar_ativos(hoje, hoje, "mock", [comunidade], ["#duvidas-oci"])
    assert "newsletter" not in set(duvidas["chave"]) and set(duvidas["canal"]) == {"#duvidas-oci"}


@pytest.mark.real
def test_opcoes_filtros(banco_real, lote_real, resposta_real):
    repositorio.gravar_lote(lote_real, resposta_real, "mock")
    opcoes = repositorio.opcoes_filtros("mock")
    assert banco_real in opcoes["comunidades"] and "#geral" in opcoes["canais"]


@pytest.mark.real
def test_atualizar_lote_substituido_avisa(banco_real, lote_real, resposta_real):
    antigo = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    repositorio.gravar_lote(lote_real, resposta_real, "mock")  # substitui: o id antigo some
    with pytest.raises(LookupError, match="substituído"):
        repositorio.salvar_decisao(antigo, "faq_0", "a", {}, autorizacao=False)
    with pytest.raises(LookupError, match="substituído"):
        repositorio.atualizar_alerta(antigo, 6, "resolvido")


@pytest.mark.real
def test_carregar_lote_inexistente_avisa(banco_real, lote_real, resposta_real):
    lote_id = repositorio.gravar_lote(lote_real, resposta_real, "mock")
    repositorio.gravar_lote(lote_real, resposta_real, "mock")
    with pytest.raises(LookupError, match="não encontrado"):
        repositorio.carregar_lote(lote_id)


def test_erro_sem_mensagem_ainda_avisa(lote_exemplo, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")

    def explode(*a):
        raise TimeoutError()

    monkeypatch.setattr(repositorio, "gravar_lote", explode)
    assert grafo.processar_com_registro(lote_exemplo)[1]["erro"] == "TimeoutError"
