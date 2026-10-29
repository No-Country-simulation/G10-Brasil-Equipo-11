"""Persistência do histórico no Supabase (Postgres). Dono: pessoa 4.

Este módulo reúne as regras puras: se o banco está configurado, a impressão digital (hash) do
conteúdo de um lote e a montagem das linhas que serão gravadas. Sem DATABASE_URL não grava nada.
"""
import hashlib
import json
import os
import unicodedata
from datetime import date

import pandas as pd
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
    # Sem limite, uma conexão recusada no Windows espera 130 s e trava o painel.
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)


def gravar_lote(lote: LoteEntrada, resposta: dict, modo: str) -> int:
    """Grava o lote inteiro numa transação, substituindo o lote de mesmo (hash, modo). Devolve lotes.id."""
    linhas = linhas_do_lote(lote, resposta)
    resumo = resposta["resumo_comunidade"]
    oci = resposta.get("armazenamento_oci") or {}
    with conectar() as conn:
        comunidade_id = conn.execute(
            "insert into comunidades (nome) values (%s) "
            "on conflict (nome) do update set nome = excluded.nome returning id",
            (_norm(lote.origem_comunidade),)).fetchone()[0]
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
        if lote is None:
            raise LookupError("Lote não encontrado no histórico.")
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


_LOTE_SUBSTITUIDO = "Este lote foi substituído no histórico; reabra-o pelo Importar."


def salvar_decisao(lote_id: int, chave: str, decisao: str, conteudo_editado: dict, autorizacao: bool) -> None:
    status = _DECISAO_PARA_STATUS[decisao]
    with conectar() as conn:
        cur = conn.execute(
            "update ativos set status = %s, conteudo_editado = %s, autorizacao_membro = %s, "
            "revisado_em = case when %s = 'pendente' then null else now() end "
            "where lote_id = %s and chave = %s",
            (status, Jsonb(conteudo_editado) if conteudo_editado else None, autorizacao,
             status, lote_id, chave))
        if cur.rowcount == 0:
            raise LookupError(_LOTE_SUBSTITUIDO)


def atualizar_alerta(lote_id: int, ordem: int, status: str) -> None:
    with conectar() as conn:
        cur = conn.execute(
            "update alertas set status = %s, atualizado_em = now() "
            "where lote_id = %s and interacao_id = "
            "(select id from interacoes where lote_id = %s and ordem = %s)",
            (status, lote_id, lote_id, ordem))
        if cur.rowcount == 0:
            raise LookupError(_LOTE_SUBSTITUIDO)


FUSO = "America/Sao_Paulo"

_COLUNAS_INTERACOES = ["lote_id", "processado_em", "periodo_referencia", "comunidade", "canal",
                       "sentimento", "topico", "rota"]
_COLUNAS_ATIVOS = ["lote_id", "chave", "tipo", "status", "canal"]


def _filtros(inicio: date, fim: date, modo: str, comunidades, canais, col_lote: str, col_modo: str,
             col_comunidade: str, col_canal: str) -> tuple[str, list]:
    """Monta o where (período inclusivo no fuso de São Paulo, modo e filtros opcionais) e seus parâmetros."""
    condicoes = [f"({col_lote} at time zone '{FUSO}')::date between %s and %s", f"{col_modo} = %s"]
    params: list = [inicio, fim, modo]
    if comunidades:
        condicoes.append(f"{col_comunidade} = any(%s)")
        params.append(list(comunidades))
    if canais:
        condicoes.append(f"{col_canal} = any(%s)")
        params.append(list(canais))
    return " and ".join(condicoes), params


def consultar_interacoes(inicio: date, fim: date, modo: str, comunidades: list[str] | None = None,
                         canais: list[str] | None = None) -> pd.DataFrame:
    where, params = _filtros(inicio, fim, modo, comunidades, canais, "processado_em", "modo_llm", "comunidade", "canal")
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("select lote_id, processado_em, periodo_referencia, comunidade, canal, sentimento, topico, rota "
                    f"from vw_interacoes_analisadas where {where} "
                    "order by processado_em, lote_id, ordem", params)
        return pd.DataFrame(cur.fetchall(), columns=_COLUNAS_INTERACOES)


def consultar_ativos(inicio: date, fim: date, modo: str, comunidades: list[str] | None = None,
                     canais: list[str] | None = None) -> pd.DataFrame:
    where, params = _filtros(inicio, fim, modo, comunidades, canais, "l.processado_em", "l.modo_llm", "c.nome", "i.canal")
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("select a.lote_id, a.chave, a.tipo, a.status, i.canal "
                    "from ativos a join lotes l on l.id = a.lote_id "
                    "join comunidades c on c.id = l.comunidade_id "
                    "left join interacoes i on i.id = a.interacao_origem_id "
                    f"where {where} "
                    "order by a.lote_id, a.id", params)
        return pd.DataFrame(cur.fetchall(), columns=_COLUNAS_ATIVOS)


def opcoes_filtros(modo: str) -> dict:
    with conectar() as conn:
        comunidades = conn.execute(
            "select distinct c.nome from comunidades c join lotes l on l.comunidade_id = c.id "
            "where l.modo_llm = %s order by 1", (modo,)).fetchall()
        canais = conn.execute(
            "select distinct i.canal from interacoes i join lotes l on l.id = i.lote_id "
            "where l.modo_llm = %s order by 1", (modo,)).fetchall()
    return {"comunidades": [r[0] for r in comunidades], "canais": [r[0] for r in canais]}
