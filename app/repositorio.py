"""Persistência do histórico no Supabase (Postgres). Dono: pessoa 4.

Este módulo reúne as regras puras: se o banco está configurado, a impressão digital (hash) do
conteúdo de um lote e a montagem das linhas que serão gravadas. Sem DATABASE_URL não grava nada.
"""
import hashlib
import json
import os
import unicodedata

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
