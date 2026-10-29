"""Persistência do histórico no Supabase (Postgres). Dono: pessoa 4.

Este módulo reúne as regras puras: se o banco está configurado, a impressão digital (hash) do
conteúdo de um lote e a montagem das linhas que serão gravadas. Sem DATABASE_URL não grava nada.
"""
import hashlib
import json
import os
import unicodedata

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .llm import modo_mock
from .schemas import LoteEntrada


def banco_configurado() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())


def modo_atual() -> str:
    return "mock" if modo_mock() else "gemini"


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def hash_conteudo(lote: LoteEntrada) -> str:
    """SHA-256 do conteúdo: ignora ordem das interações, espaços nas pontas, forma Unicode e período."""
    itens = sorted([_norm(i.autor), _norm(i.canal), i.tipo, _norm(i.texto)] for i in lote.interacoes)
    bruto = json.dumps({"comunidade": _norm(lote.origem_comunidade), "interacoes": itens},
                       ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def linhas_do_lote(lote: LoteEntrada, resposta: dict) -> dict:
    """Monta as linhas de interações, ativos e alertas a partir do lote e da resposta de processar()."""
    analises = resposta["analises"]
    interacoes = []
    for ordem, (entrada, a) in enumerate(zip(lote.interacoes, analises)):
        interacoes.append({
            "ordem": ordem,
            "autor": entrada.autor,
            "canal": entrada.canal,
            "tipo": entrada.tipo,
            "texto": entrada.texto,
            "sentimento": a["sentimento"],
            "topico": a["topico"],
            "relevancia": a["relevancia"],
            "rota": a["rota"],
        })

    ativos_gerados = resposta["ativos_distribuicao_gerados"]
    ativos = []

    if ativos_gerados.get("post_linkedin"):
        cases = [i for i, a in enumerate(analises) if a["rota"] == "case_sucesso"]
        origem = max(cases, key=lambda i: analises[i]["relevancia"]) if cases else None
        ativos.append({"chave": "post", "tipo": "post_linkedin", "ordem_origem": origem,
                       "conteudo_gerado": ativos_gerados["post_linkedin"]})

    if ativos_gerados.get("destaque_newsletter_semanal"):
        ativos.append({"chave": "newsletter", "tipo": "newsletter", "ordem_origem": None,
                       "conteudo_gerado": ativos_gerados["destaque_newsletter_semanal"]})

    ordens_faq = [i for i, a in enumerate(analises) if a["rota"] == "faq"]
    for n, faq in enumerate(ativos_gerados.get("sugestao_conteudo_faq") or []):
        ativos.append({"chave": f"faq_{n}", "tipo": "faq",
                       "ordem_origem": ordens_faq[n] if n < len(ordens_faq) else None,
                       "conteudo_gerado": faq})

    ordens_alerta = [i for i, a in enumerate(analises) if a["rota"] == "alerta"]
    alertas = [{"ordem": ordem, "autor": al["autor"], "motivo": al["motivo"]}
               for ordem, al in zip(ordens_alerta, ativos_gerados.get("alertas_comunidade") or [])]

    return {"interacoes": interacoes, "ativos": ativos, "alertas": alertas}


_DECISAO_PARA_STATUS = {"p": "pendente", "a": "aprovado", "d": "descartado"}
_STATUS_PARA_DECISAO = {v: k for k, v in _DECISAO_PARA_STATUS.items()}


def conectar() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def gravar_lote(lote: LoteEntrada, resposta: dict, modo: str) -> int:
    """Grava o lote inteiro numa transação, substituindo o lote de mesmo (hash, modo). Devolve lotes.id."""
    linhas = linhas_do_lote(lote, resposta)
    resumo = resposta["resumo_comunidade"]
    oci = resposta.get("armazenamento_oci") or {}
    with conectar() as conn:
        comunidade_id = conn.execute(
            "insert into comunidades (nome) values (%s) "
            "on conflict (nome) do update set nome = excluded.nome returning id",
            (lote.origem_comunidade,)).fetchone()[0]
        conn.execute("delete from lotes where hash_conteudo = %s and modo_llm = %s",
                     (hash_conteudo(lote), modo))
        lote_id = conn.execute(
            "insert into lotes (comunidade_id, periodo_referencia, hash_conteudo, modo_llm, total_interacoes, "
            "sentimento_predominante, topicos_principais, oci_bucket, oci_caminho_objeto, oci_status, resposta) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
            (comunidade_id, lote.periodo_referencia, hash_conteudo(lote), modo,
             resumo["total_interacoes_processadas"], resumo["sentimento_predominante"],
             resumo["topicos_principais"], oci.get("bucket"), oci.get("caminho_objeto"), oci.get("status"),
             Jsonb(resposta))).fetchone()[0]

        id_por_ordem = {}
        for i in linhas["interacoes"]:
            interacao_id = conn.execute(
                "insert into interacoes (lote_id, ordem, autor, canal, tipo, texto) "
                "values (%s,%s,%s,%s,%s,%s) returning id",
                (lote_id, i["ordem"], i["autor"], i["canal"], i["tipo"], i["texto"])).fetchone()[0]
            id_por_ordem[i["ordem"]] = interacao_id
            conn.execute(
                "insert into analises (interacao_id, sentimento, topico, relevancia, rota) "
                "values (%s,%s,%s,%s,%s)",
                (interacao_id, i["sentimento"], i["topico"], i["relevancia"], i["rota"]))
        for a in linhas["ativos"]:
            conn.execute(
                "insert into ativos (lote_id, chave, tipo, interacao_origem_id, conteudo_gerado) "
                "values (%s,%s,%s,%s,%s)",
                (lote_id, a["chave"], a["tipo"], id_por_ordem.get(a["ordem_origem"]),
                 Jsonb(a["conteudo_gerado"])))
        for al in linhas["alertas"]:
            conn.execute(
                "insert into alertas (lote_id, interacao_id, autor, motivo) values (%s,%s,%s,%s)",
                (lote_id, id_por_ordem[al["ordem"]], al["autor"], al["motivo"]))
    return lote_id


def buscar_lote(hash_conteudo: str, modo: str) -> dict | None:
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select id, processado_em, total_interacoes from lotes "
                    "where hash_conteudo = %s and modo_llm = %s", (hash_conteudo, modo))
        return cur.fetchone()


def carregar_lote(lote_id: int) -> dict:
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select l.resposta, l.processado_em, l.periodo_referencia, c.nome "
                    "from lotes l join comunidades c on c.id = l.comunidade_id where l.id = %s", (lote_id,))
        lote = cur.fetchone()
        cur.execute("select chave, tipo, status, conteudo_editado, autorizacao_membro "
                    "from ativos where lote_id = %s order by id", (lote_id,))
        ativos = cur.fetchall()
        cur.execute("select i.ordem, a.status from alertas a join interacoes i on i.id = a.interacao_id "
                    "where a.lote_id = %s and a.status <> 'aberto'", (lote_id,))
        alertas = cur.fetchall()
    textos = {}
    for a in ativos:
        textos.update(a["conteudo_editado"] or {})
    return {
        "resposta": lote["resposta"],
        "processado_em": lote["processado_em"],
        "origem": lote["nome"],
        "periodo": lote["periodo_referencia"],
        "decisoes": {a["chave"]: _STATUS_PARA_DECISAO[a["status"]] for a in ativos},
        "textos": textos,
        "autorizado": any(a["autorizacao_membro"] for a in ativos if a["tipo"] == "post_linkedin"),
        "alertas": {a["ordem"]: a["status"] for a in alertas},
    }


def salvar_decisao(lote_id: int, chave: str, decisao: str, conteudo_editado: dict, autorizacao: bool) -> None:
    status = _DECISAO_PARA_STATUS[decisao]
    with conectar() as conn:
        conn.execute(
            "update ativos set status = %s, conteudo_editado = %s, autorizacao_membro = %s, "
            "revisado_em = case when %s = 'pendente' then null else now() end "
            "where lote_id = %s and chave = %s",
            (status, Jsonb(conteudo_editado) if conteudo_editado else None, autorizacao,
             status, lote_id, chave))


def atualizar_alerta(lote_id: int, ordem: int, status: str) -> None:
    with conectar() as conn:
        conn.execute(
            "update alertas set status = %s, atualizado_em = now() "
            "where lote_id = %s and interacao_id = "
            "(select id from interacoes where lote_id = %s and ordem = %s)",
            (status, lote_id, lote_id, ordem))
