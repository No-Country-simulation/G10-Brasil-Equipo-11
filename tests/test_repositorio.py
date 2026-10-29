import json
import os
import unicodedata
from pathlib import Path

import pytest

import ui.curadoria as cur
from app import repositorio
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
