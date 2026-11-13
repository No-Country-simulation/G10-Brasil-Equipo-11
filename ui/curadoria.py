"""Regras da curadoria, sem Streamlit, para poderem ser testadas sozinhas.

Cada ativo gerado pelo pipeline vira um item com id estável ("post", "newsletter", "faq_0"...).
A pessoa decide: "p" pendente, "a" aprovado, "d" descartado.
O pacote de aprovados leva os textos COMO FORAM EDITADOS no painel.
"""
import json
import re
from datetime import datetime
from pathlib import Path

from app.storage import caminho_objeto

PENDENTE, APROVADO, DESCARTADO = "p", "a", "d"
STATUS_ALERTA = {"encaminhado": "Encaminhado", "mentoria_oferecida": "Mentoria oferecida", "resolvido": "Resolvido"}


def membro_do_post(resultado: dict) -> dict | None:
    """A interação que originou o post: a de maior relevância na rota case_sucesso (mesma regra do grafo)."""
    cases = [a for a in resultado["analises"] if a["rota"] == "case_sucesso"]
    return max(cases, key=lambda a: a["relevancia"]) if cases else None


def outros_cases(resultado: dict) -> list[dict]:
    escolhido = membro_do_post(resultado)
    return [a for a in resultado["analises"] if a["rota"] == "case_sucesso" and a is not escolhido]


def duvida_da_faq(resultado: dict, indice: int) -> dict | None:
    faqs = [a for a in resultado["analises"] if a["rota"] == "faq"]
    return faqs[indice] if indice < len(faqs) else None


def ids_dos_ativos(resultado: dict) -> list[str]:
    ativos = resultado["ativos_distribuicao_gerados"]
    ids = []
    if ativos.get("post_linkedin"):
        ids.append("post")
    if ativos.get("destaque_newsletter_semanal"):
        ids.append("newsletter")
    ids += [f"faq_{i}" for i in range(len(ativos.get("sugestao_conteudo_faq") or []))]
    return ids


def proximo_pendente(ids: list[str], decisoes: dict[str, str], atual: str | None = None) -> str | None:
    """O primeiro pendente depois de `atual`, dando a volta na fila. None quando não sobrou nenhum."""
    inicio = ids.index(atual) + 1 if atual in ids else 0
    return next((i for i in ids[inicio:] + ids[:inicio] if decisoes.get(i, PENDENTE) == PENDENTE), None)


def titulo_na_fila(resultado: dict, id_ativo: str) -> str:
    ativos = resultado["ativos_distribuicao_gerados"]
    if id_ativo == "post":
        return f'Post: {ativos["post_linkedin"]["titulo"]}'
    if id_ativo == "newsletter":
        return f'Newsletter: {ativos["destaque_newsletter_semanal"]["secao"]}'
    faq = ativos["sugestao_conteudo_faq"][int(id_ativo.removeprefix("faq_"))]
    return faq["tema"].removeprefix("Dica Rápida:").strip()


def campos_do_ativo(id_ativo: str | None) -> tuple[str, ...]:
    """Chaves de estado dos campos que o item mostra na tela."""
    if id_ativo == "post":
        return ("txt_post_copy", "autorizado")
    if id_ativo == "newsletter":
        return ("txt_news_chamada", "txt_news_resumo")
    return (f"txt_{id_ativo}_conteudo",) if id_ativo else ()


def textos_do_ativo(id_ativo: str, textos: dict[str, str]) -> dict[str, str]:
    """Os textos editados (sem o "txt_") que pertencem a um ativo, para gravar junto com a decisão."""
    prefixo = {"post": "post_", "newsletter": "news_"}.get(id_ativo, f"{id_ativo}_")
    return {k: v for k, v in textos.items() if k.startswith(prefixo)}


def resumo(decisoes: dict[str, str]) -> dict[str, int]:
    valores = list(decisoes.values())
    aprovados = valores.count(APROVADO)
    descartados = valores.count(DESCARTADO)
    return {
        "total": len(valores),
        "aprovados": aprovados,
        "descartados": descartados,
        "revisados": aprovados + descartados,
        "pendentes": len(valores) - aprovados - descartados,
    }


def montar_aprovados(resultado: dict, decisoes: dict[str, str], textos: dict[str, str],
                     origem: str, periodo: str, autorizado: bool) -> dict:
    """Pacote final com o que foi aprovado, usando os textos editados (textos[id_campo])."""
    ativos = resultado["ativos_distribuicao_gerados"]
    pacote = {
        "origem_comunidade": origem,
        "periodo_referencia": periodo,
        "aprovado_em": datetime.now().isoformat(timespec="seconds"),
        "post_linkedin": None,
        "destaque_newsletter_semanal": None,
        "sugestao_conteudo_faq": [],
        "descartados": sorted(k for k, v in decisoes.items() if v == DESCARTADO),
    }

    if decisoes.get("post") == APROVADO and ativos.get("post_linkedin"):
        if not autorizado:
            raise ValueError("O post só pode ser exportado com a autorização do membro.")
        post = dict(ativos["post_linkedin"])
        post["copy"] = textos.get("post_copy", post["copy"])
        membro = membro_do_post(resultado)
        post["membro"] = membro["autor"] if membro else None
        post["autorizacao_membro"] = True
        pacote["post_linkedin"] = post

    if decisoes.get("newsletter") == APROVADO and ativos.get("destaque_newsletter_semanal"):
        news = dict(ativos["destaque_newsletter_semanal"])
        news["chamada"] = textos.get("news_chamada", news["chamada"])
        news["resumo"] = textos.get("news_resumo", news["resumo"])
        pacote["destaque_newsletter_semanal"] = news

    for i, faq in enumerate(ativos.get("sugestao_conteudo_faq") or []):
        if decisoes.get(f"faq_{i}") == APROVADO:
            item = dict(faq)
            item["conteudo"] = textos.get(f"faq_{i}_conteudo", item["conteudo"])
            pacote["sugestao_conteudo_faq"].append(item)

    return pacote


def salvar_aprovados(pacote: dict, raiz: Path = Path(".")) -> Path:
    """Salva ao lado do pacote de distribuição: saida_local/ativos/<ano>-semana-XX/aprovados.json."""
    periodo = str(pacote.get("periodo_referencia") or "").strip()
    if not re.fullmatch(r"^[a-zA-Z0-9_\-]+$", periodo):
        raise ValueError(f"Período de referência inválido: {periodo}")
    pasta_base = (raiz / "saida_local").resolve()
    relativo = Path(caminho_objeto(periodo)).parent
    pasta = (pasta_base / relativo).resolve()
    if not pasta.is_relative_to(pasta_base):
        raise ValueError("Tentativa de gravação fora do diretório permitido.")
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / "aprovados.json"
    destino.write_text(json.dumps(pacote, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino
