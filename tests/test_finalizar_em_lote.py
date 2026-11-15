"""`finalizar_processamento` grava o resultado do lote com um envio por tabela.

Um Oracle de mentira registra os comandos. Os testes conferem que nada deixou de ser
gravado, que a ordem dos ativos é mantida e que as travas de segurança continuam valendo.
"""
import json
from contextlib import contextmanager

import pytest

pytest.importorskip("oracledb")

from app import database, repository  # noqa: E402

PROCESSO = "proc-1"
TOKEN = "tentativa-1"
IDS = ["i0", "i1", "i2", "i3"]


class CursorFalso:
    def __init__(self, banco):
        self.banco = banco
        self.rowcount = 0
        self.arraysize = 100
        self.outputtypehandler = None
        self._linhas = []
        self._contagens = []

    def __enter__(self):
        return self

    def __exit__(self, *erro):
        return False

    def setinputsizes(self, **tipos):
        pass

    def execute(self, sql, parametros=None):
        self.banco.comandos.append(("execute", " ".join(sql.split()), parametros))
        if "SELECT STATUS, ATTEMPT_TOKEN" in sql:
            self._linhas = [("PROCESSANDO", TOKEN)]
        elif "FROM CL_INTERACOES" in sql:
            self._linhas = list(self.banco.interacoes)
        elif "SELECT COUNT(*)" in sql:
            self._linhas = [(self.banco.ativos_existentes,)]
        elif "UPDATE CL_PROCESSAMENTOS" in sql:
            self.rowcount = 1

    def executemany(self, sql, linhas, **opcoes):
        sql = " ".join(sql.split())
        self.banco.comandos.append(("executemany", sql, list(linhas)))
        if "UPDATE CL_INTERACOES" in sql:
            assert opcoes.get("arraydmlrowcounts") is True
            self._contagens = [0 if linha["id"] in self.banco.ids_sumidos else 1 for linha in linhas]

    def getarraydmlrowcounts(self):
        return self._contagens

    def fetchone(self):
        return self._linhas[0] if self._linhas else None

    def fetchall(self):
        return self._linhas


class BancoFalso:
    def __init__(self, interacoes):
        self.interacoes = interacoes
        self.comandos = []
        self.commits = 0
        self.ativos_existentes = 0
        self.ids_sumidos = set()

    def cursor(self):
        return CursorFalso(self)

    def commit(self):
        self.commits += 1

    def lotes(self, tabela):
        return [linhas for tipo, sql, linhas in self.comandos if tipo == "executemany" and tabela in sql]


def resposta_do_pipeline():
    analises = [
        {"autor": "Ana", "canal": "#vagas", "texto": "Fui contratada!", "tipo": "depoimento",
         "sentimento": "Altamente Positivo", "topico": "Vagas", "relevancia": 9, "rota": "case_sucesso"},
        {"autor": "Beto", "canal": "#duvidas", "texto": "Como leio um CSV?", "tipo": "pergunta_tecnica",
         "sentimento": "Neutro", "topico": "CSV", "relevancia": 6, "rota": "faq"},
        {"autor": "Caio", "canal": "#geral", "texto": "Estou frustrado com o suporte.", "tipo": "reclamacao",
         "sentimento": "Negativo", "topico": "Suporte", "relevancia": 4, "rota": "alerta"},
        {"autor": "Dani", "canal": "#duvidas", "texto": "E um JSON, como leio?", "tipo": "pergunta_tecnica",
         "sentimento": "Neutro", "topico": "JSON", "relevancia": 6, "rota": "faq"},
    ]
    return {
        "status": "sucesso",
        "analises": analises,
        "ativos_distribuicao_gerados": {
            "post_linkedin": {"titulo": "Conquista da Ana", "copy": "Texto", "potencial_engajamento": "Alto"},
            "sugestao_conteudo_faq": [
                {"tema": "Dica Rápida: CSV", "conteudo": "Use pandas.", "origem": "Beto"},
                {"tema": "Dica Rápida: JSON", "conteudo": "Use json.", "origem": "Dani"},
            ],
            "alertas_comunidade": [{"autor": "Caio", "motivo": "Negativo em #geral"}],
            "destaque_newsletter_semanal": {"secao": "S", "chamada": "C", "resumo": "R"},
        },
        "fontes_ativos": {"post": ["i0"], "faq_0": ["i1"], "faq_1": ["i3"], "alerta_0": ["i2"],
                          "newsletter": list(IDS)},
    }


@pytest.fixture
def banco(monkeypatch):
    resposta = resposta_do_pipeline()
    falso = BancoFalso([(IDS[n], a["autor"], a["canal"], a["texto"]) for n, a in enumerate(resposta["analises"])])

    @contextmanager
    def conexao():
        yield falso

    monkeypatch.setattr(database, "connection", conexao)
    monkeypatch.setenv("OCI_STORAGE_MODE", "local")
    return falso


def finalizar():
    return repository.finalizar_processamento(PROCESSO, resposta_do_pipeline(), IDS, TOKEN, "ativos/x/pacote.json")


def test_grava_tudo_com_um_envio_por_tabela(banco):
    resultado = finalizar()

    assert banco.commits == 1
    assert resultado["processamento_id"] == PROCESSO and resultado["persistencia"] == "oracle"

    (analises,) = banco.lotes("UPDATE CL_INTERACOES")
    assert [linha["id"] for linha in analises] == IDS
    assert [json.loads(linha["analysis_json"])["interacao_id"] for linha in analises] == IDS
    assert json.loads(analises[1]["analysis_json"])["texto"] == "Como leio um CSV?"

    (ativos,) = banco.lotes("INSERT INTO CL_ATIVOS")
    assert [linha["asset_key"] for linha in ativos] == ["post", "newsletter", "faq_0", "faq_1"]
    assert [linha["kind"] for linha in ativos] == ["POST_LINKEDIN", "NEWSLETTER", "FAQ", "FAQ"]
    assert [linha["title"] for linha in ativos] == ["Conquista da Ana", "C", "Dica Rápida: CSV", "Dica Rápida: JSON"]
    assert {linha["id"] for linha in ativos} == set(resultado["ids_ativos"].values())

    (fontes,) = banco.lotes("INSERT INTO CL_ATIVO_INTERACOES")
    por_ativo = {}
    for linha in fontes:
        por_ativo.setdefault(linha["asset_id"], []).append((linha["interaction_id"], linha["method"]))
    ids_ativos = resultado["ids_ativos"]
    assert por_ativo[ids_ativos["post"]] == [("i0", "FONTES_DO_GRAFO")]
    assert por_ativo[ids_ativos["faq_1"]] == [("i3", "FONTES_DO_GRAFO")]
    assert por_ativo[ids_ativos["newsletter"]] == [(i, "LOTE_COMPLETO") for i in IDS]

    (historico,) = banco.lotes("INSERT INTO CL_HISTORICO_CURADORIA")
    assert [linha["asset_id"] for linha in historico] == [linha["id"] for linha in ativos]
    assert [linha["new_payload"] for linha in historico] == [linha["payload_json"] for linha in ativos]

    (alertas,) = banco.lotes("INSERT INTO CL_ALERTAS")
    assert [(a["interaction_id"], a["motivo"]) for a in alertas] == [
        ("i2", "Negativo em #geral: Estou frustrado com o suporte.")]
    (historico_alertas,) = banco.lotes("INSERT INTO CL_HISTORICO_ALERTAS")
    assert [(h["alert_id"], h["justification"]) for h in historico_alertas] == [
        (alertas[0]["id"], alertas[0]["motivo"])]


def test_ativos_mantem_a_ordem_de_criacao(banco):
    """As telas listam os ativos por CRIADO_EM: cada linha do lote leva um horário crescente."""
    finalizar()
    (ativos,) = banco.lotes("INSERT INTO CL_ATIVOS")
    assert [linha["ordem"] for linha in ativos] == [0, 1, 2, 3]
    sql = next(sql for tipo, sql, _ in banco.comandos if tipo == "executemany" and "INSERT INTO CL_ATIVOS" in sql)
    assert sql.count("SYSTIMESTAMP + NUMTODSINTERVAL(:ordem / 1000000, 'SECOND')") == 2


def test_resultado_e_confirmado_antes_dos_ativos_e_uma_vez_so(banco):
    finalizar()
    tabelas = [sql.split(" (")[0].split(" SET")[0] for tipo, sql, _ in banco.comandos
               if sql.startswith(("UPDATE", "INSERT"))]
    assert tabelas == ["UPDATE CL_INTERACOES", "UPDATE CL_PROCESSAMENTOS", "INSERT INTO CL_ATIVOS",
                       "INSERT INTO CL_ATIVO_INTERACOES", "INSERT INTO CL_HISTORICO_CURADORIA",
                       "INSERT INTO CL_ALERTAS", "INSERT INTO CL_HISTORICO_ALERTAS"]


def test_interacao_que_nao_foi_atualizada_recusa_a_gravacao(banco):
    banco.ids_sumidos = {"i2"}
    with pytest.raises(RuntimeError, match="Interação de origem não localizada"):
        finalizar()
    assert banco.commits == 0
    assert banco.lotes("INSERT INTO CL_ATIVOS") == []


def test_ativos_ja_gravados_recusam_gravacao_duplicada(banco):
    banco.ativos_existentes = 3
    with pytest.raises(RuntimeError, match="gravação duplicada"):
        finalizar()
    assert banco.commits == 0 and banco.lotes("UPDATE CL_INTERACOES") == []


def test_interacoes_alteradas_recusam_a_gravacao(banco):
    banco.interacoes[1] = ("i1", "Beto", "#duvidas", "texto trocado no banco")
    with pytest.raises(ValueError, match="não corresponde exatamente"):
        finalizar()
    assert banco.commits == 0


def test_lote_sem_alertas_nao_envia_nada_para_as_tabelas_de_alerta(banco, monkeypatch):
    resposta = resposta_do_pipeline()
    resposta["analises"][2]["rota"] = "nenhuma"
    repository.finalizar_processamento(PROCESSO, resposta, IDS, TOKEN, "ativos/x/pacote.json")
    assert banco.commits == 1
    assert banco.lotes("INSERT INTO CL_ALERTAS") == [] and banco.lotes("INSERT INTO CL_HISTORICO_ALERTAS") == []
