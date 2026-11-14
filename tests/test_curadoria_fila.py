"""Fila única da Curadoria: lotes pendentes em lote (Oracle com dublês) e download de vários lotes.

Rode com:  python -m pytest tests/test_curadoria_fila.py -v
"""
import csv
import io
import json
import sys
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import exportacao_arquivos as arquivos  # noqa: E402
from app import main, repository, rotas_web  # noqa: E402

cliente = TestClient(main.app)


# ---------------------------------------------------------------------------
# Repositório: estados de vários lotes em três consultas
# ---------------------------------------------------------------------------
class CursorSequencia:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.sqls, self.params_lista, self.rows = [], [], []
        self.outputtypehandler = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        self.params_lista.append(params or {})
        self.rows = self.respostas.pop(0)

    def fetchall(self):
        return self.rows


def conectar_sequencia(monkeypatch, respostas):
    cursor = CursorSequencia(respostas)

    class Conexao:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return cursor

    @contextmanager
    def fake_connection():
        yield Conexao()

    monkeypatch.setattr(repository.database, "connection", fake_connection)
    return cursor


def test_estados_dos_lotes_em_tres_consultas(monkeypatch):
    cursor = conectar_sequencia(monkeypatch, [
        [("L1", "Discord · ONE", "2026-11", "SUCESSO", "gemini", 3, '{"analises": []}',
          datetime(2026, 11, 12, 18, 0), datetime(2026, 11, 12, 18, 1))],
        [("L1", "a-1", "post", "POST_LINKEDIN", "Título", '{"copy": "Oi"}', "PENDENTE", 1, "PENDENTE", None, None, None)],
        [("L1", "al-1", "int-1", "Bia", "#suporte", "Ruim", "Reclamação", "PENDENTE", 2, None, None, None)],
    ])
    lotes = repository.carregar_estados_dos_lotes(["L1"])
    assert len(cursor.sqls) == 3
    assert all(":id0" in sql for sql in cursor.sqls)
    assert cursor.outputtypehandler is not None
    item = lotes["L1"]
    assert (item["origem_comunidade"], item["periodo_referencia"], item["status"]) == ("Discord · ONE", "2026-11", "SUCESSO")
    assert item["resultado"] == {"analises": []}
    assert item["finalizado_em"] == "2026-11-12T18:01:00"
    assert item["ativos"] == [{
        "id": "a-1", "chave": "post", "tipo": "POST_LINKEDIN", "titulo": "Título", "payload": {"copy": "Oi"},
        "status_curadoria": "PENDENTE", "versao": 1, "consentimento_status": "PENDENTE",
        "consentimento_autor": None, "consentimento_em": None, "consentimento_referencia": None,
    }]
    assert item["alertas"] == [{
        "id": "al-1", "interacao_id": "int-1", "autor": "Bia", "canal": "#suporte", "texto": "Ruim",
        "motivo": "Reclamação", "status": "PENDENTE", "versao": 2, "acao": None, "responsavel": None,
        "justificativa": None,
    }]


def test_estados_dos_lotes_sem_ids_nao_consulta(monkeypatch):
    cursor = conectar_sequencia(monkeypatch, [])
    assert repository.carregar_estados_dos_lotes([]) == {}
    assert cursor.sqls == []


# ---------------------------------------------------------------------------
# Rota /api/curadoria/fila
# ---------------------------------------------------------------------------
def lote_resumo(lid, ativos, alertas=0):
    return {"id": lid, "origem_comunidade": f"Origem {lid}", "periodo_referencia": "2026-11",
            "criado_em": "2026-11-12T18:00:00", "finalizado_em": "2026-11-12T18:01:00",
            "ativos_pendentes": {"post": ativos, "newsletter": 0, "faq": 0}, "alertas_pendentes": alertas}


def estado_item(lid):
    return {"id": lid, "origem_comunidade": f"Origem {lid}", "periodo_referencia": "2026-11", "status": "SUCESSO",
            "criado_em": "2026-11-12T18:00:00", "finalizado_em": "2026-11-12T18:01:00",
            "resultado": {"analises": [], "ativos_distribuicao_gerados": {"post_linkedin": {"copy": "x"}}},
            "ativos": [{"id": f"{lid}-post", "chave": "post", "payload": {"copy": "x"}, "status_curadoria": "PENDENTE",
                        "consentimento_status": "PENDENTE"}],
            "alertas": []}


@pytest.fixture
def oracle(monkeypatch):
    chamadas = []
    monkeypatch.setattr(rotas_web, "oracle_ativo", lambda: True)
    monkeypatch.setattr(rotas_web, "_modo_atual", lambda: "mock")
    monkeypatch.setattr(repository, "listar_lotes_com_pendencias",
                        lambda modo: [lote_resumo("L1", 1), lote_resumo("L2", 0, 2), lote_resumo("L3", 1)])

    def estados(ids):
        chamadas.append(list(ids))
        return {i: estado_item(i) for i in ids}

    def proibido(pid):
        raise AssertionError("a fila não busca lote a lote")

    monkeypatch.setattr(repository, "carregar_estados_dos_lotes", estados)
    monkeypatch.setattr(repository, "obter_processamento", proibido)
    return chamadas


def test_fila_so_traz_lotes_com_ativos_na_ordem(oracle):
    r = cliente.get("/api/curadoria/fila").json()
    assert r["oracle_configurado"] is True
    assert [l["lote_id"] for l in r["lotes"]] == ["L1", "L3"]
    assert oracle == [["L1", "L3"]]
    primeiro = r["lotes"][0]
    assert primeiro["decisoes"] == {"post": "p"}
    assert (primeiro["origem"], primeiro["periodo"]) == ("Origem L1", "2026-11")
    assert primeiro["processado_em"] == "2026-11-12T18:01:00+00:00"


def test_fila_sem_oracle_avisa(monkeypatch):
    monkeypatch.setattr(rotas_web, "oracle_ativo", lambda: False)
    r = cliente.get("/api/curadoria/fila")
    assert r.status_code == 200 and r.json()["oracle_configurado"] is False


def test_fila_banco_fora_da_503_sem_ora(oracle, monkeypatch):
    def falha(*a, **k):
        raise RuntimeError("ORA-12541 host interno")
    monkeypatch.setattr(repository, "carregar_estados_dos_lotes", falha)
    r = cliente.get("/api/curadoria/fila")
    assert r.status_code == 503 and "ORA-" not in r.text


def test_fila_exige_login(monkeypatch):
    monkeypatch.setenv("ADMIN_USUARIO", "admin")
    monkeypatch.setenv("ADMIN_SENHA", "segredo")
    assert cliente.get("/api/curadoria/fila").status_code == 401


# ---------------------------------------------------------------------------
# Download de vários lotes num arquivo
# ---------------------------------------------------------------------------
def _resultado():
    lote = json.loads(cliente.get("/api/exemplo").text)
    return cliente.post("/processar", json=lote).json()


@pytest.fixture(scope="module")
def resultado():
    return _resultado()


def pedido(resultado, origem, decisoes):
    # o painel sempre manda uma decisão por ativo; o que não foi decidido vai como pendente
    faqs = len(resultado["ativos_distribuicao_gerados"]["sugestao_conteudo_faq"])
    todas = {"post": "p", "newsletter": "p", **{f"faq_{i}": "p" for i in range(faqs)}, **decisoes}
    return {"resultado": resultado, "origem_comunidade": origem, "periodo_referencia": "2026-11",
            "decisoes": todas, "autorizado": True, "textos": {}}


def test_csv_varios_tem_coluna_lote():
    pacotes = [{"origem_comunidade": "A", "periodo_referencia": "2026-10",
                "destaque_newsletter_semanal": {"chamada": "C", "resumo": "R", "secao": "S"}},
               {"origem_comunidade": "B", "periodo_referencia": "2026-11",
                "sugestao_conteudo_faq": [{"tema": "T", "conteudo": "X", "origem": "O"}]}]
    linhas = list(csv.DictReader(io.StringIO(arquivos.gerar_varios(pacotes, "csv").decode("utf-8-sig")), delimiter=";"))
    assert list(linhas[0].keys())[0] == "lote"
    assert [(l["lote"], l["tipo"]) for l in linhas] == [("A · 2026-10", "Newsletter"), ("B · 2026-11", "FAQ")]


def test_json_varios_e_lista():
    pacotes = [{"origem_comunidade": "A", "periodo_referencia": "2026-10"}]
    assert json.loads(arquivos.gerar_varios(pacotes, "json")) == pacotes


def test_pdf_varios_comeca_com_assinatura_pdf():
    pacotes = [{"origem_comunidade": "A", "periodo_referencia": "2026-10",
                "destaque_newsletter_semanal": {"chamada": "C", "resumo": "R", "secao": "S"}}] * 2
    assert arquivos.gerar_varios(pacotes, "pdf").startswith(b"%PDF")


def test_nome_do_arquivo_varios_tem_a_data():
    assert arquivos.nome_do_arquivo_varios("csv", date(2026, 11, 14)) == "aprovados_2026-11-14.csv"


def test_baixar_varios_ignora_lote_sem_aprovados(resultado):
    corpo = {"pacotes": [pedido(resultado, "Lote_A", {"newsletter": "a"}),
                         pedido(resultado, "Lote_B", {"newsletter": "d"})]}
    r = cliente.post("/api/curadoria/baixar-varios?formato=csv", json=corpo)
    assert r.status_code == 200, r.text
    assert 'filename="aprovados_' in r.headers["content-disposition"]
    linhas = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    assert [l["lote"] for l in linhas] == ["Lote_A · 2026-11"]


def test_baixar_varios_sem_aprovados_da_422(resultado):
    corpo = {"pacotes": [pedido(resultado, "Lote_A", {"newsletter": "d"})]}
    assert cliente.post("/api/curadoria/baixar-varios?formato=csv", json=corpo).status_code == 422


def test_baixar_varios_formato_invalido_da_400(resultado):
    corpo = {"pacotes": [pedido(resultado, "Lote_A", {"newsletter": "a"})]}
    assert cliente.post("/api/curadoria/baixar-varios?formato=xls", json=corpo).status_code == 400
