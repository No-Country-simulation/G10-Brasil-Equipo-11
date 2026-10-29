"""Orquestração com LangGraph. Dono: pessoa 2.

    classificar ──┬─> gerar_case ──┐
                  ├─> gerar_faq ───┼─> gerar_newsletter ─> salvar_oci ─> FIM
                  └─> gerar_alerta ┘

O roteador só abre os ramos que têm interações daquela rota no lote.
Os ramos rodam em paralelo e se juntam na newsletter.
"""
from collections import Counter
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from . import ia, repositorio
from .schemas import Alerta, Analise, LoteEntrada
from .storage import salvar_pacote


def mesclar(a: dict, b: dict) -> dict:
    return {**a, **b}


class Estado(TypedDict, total=False):
    lote: LoteEntrada
    analises: list[Analise]
    ativos: Annotated[dict, mesclar]
    armazenamento: dict


def no_classificar(e: Estado) -> Estado:
    return {"analises": [ia.classificar(i) for i in e["lote"].interacoes]}


def roteador(e: Estado) -> list[str]:
    rotas = {a.rota for a in e["analises"]}
    ramos = [nome for rota, nome in [("case_sucesso", "gerar_case"), ("faq", "gerar_faq"), ("alerta", "gerar_alerta")] if rota in rotas]
    return ramos or ["gerar_newsletter"]


def no_case(e: Estado) -> Estado:
    melhor = max((a for a in e["analises"] if a.rota == "case_sucesso"), key=lambda a: a.relevancia)
    return {"ativos": {"post_linkedin": ia.gerar_linkedin(melhor).model_dump()}}


def no_faq(e: Estado) -> Estado:
    faqs = [ia.gerar_faq(a).model_dump() for a in e["analises"] if a.rota == "faq"]
    return {"ativos": {"sugestao_conteudo_faq": faqs}}


def no_alerta(e: Estado) -> Estado:
    alertas = [Alerta(autor=a.autor, motivo=f"{a.sentimento} em {a.canal}: {a.texto[:100]}").model_dump()
               for a in e["analises"] if a.rota == "alerta"]
    return {"ativos": {"alertas_comunidade": alertas}}


def no_newsletter(e: Estado) -> Estado:
    return {"ativos": {"destaque_newsletter_semanal": ia.gerar_newsletter(e["analises"]).model_dump()}}


def montar_resposta(e: Estado, armazenamento: dict) -> dict:
    analises = e["analises"]
    sentimento = Counter(a.sentimento for a in analises).most_common(1)[0][0]
    topicos = [t for t, _ in Counter(a.topico for a in analises).most_common(5)]
    return {
        "status": "sucesso",
        "resumo_comunidade": {
            "total_interacoes_processadas": len(analises),
            "sentimento_predominante": sentimento,
            "topicos_principais": topicos,
        },
        "analises": [a.model_dump() for a in analises],
        "ativos_distribuicao_gerados": e.get("ativos", {}),
        "armazenamento_oci": armazenamento,
    }


def no_salvar(e: Estado) -> Estado:
    pacote = montar_resposta(e, armazenamento={})
    return {"armazenamento": salvar_pacote(pacote, e["lote"].periodo_referencia)}


def construir_grafo():
    g = StateGraph(Estado)
    g.add_node("classificar", no_classificar)
    g.add_node("gerar_case", no_case)
    g.add_node("gerar_faq", no_faq)
    g.add_node("gerar_alerta", no_alerta)
    g.add_node("gerar_newsletter", no_newsletter)
    g.add_node("salvar_oci", no_salvar)

    g.add_edge(START, "classificar")
    g.add_conditional_edges("classificar", roteador,
                            ["gerar_case", "gerar_faq", "gerar_alerta", "gerar_newsletter"])
    for ramo in ("gerar_case", "gerar_faq", "gerar_alerta"):
        g.add_edge(ramo, "gerar_newsletter")
    g.add_edge("gerar_newsletter", "salvar_oci")
    g.add_edge("salvar_oci", END)
    return g.compile()


GRAFO = construir_grafo()


def processar_com_registro(lote: LoteEntrada) -> tuple[dict, dict]:
    """Processa o lote e, se houver banco configurado, grava o resultado.

    Falha ao gravar não derruba o processamento: o erro volta no registro."""
    estado = GRAFO.invoke({"lote": lote, "ativos": {}})
    resposta = montar_resposta(estado, estado["armazenamento"])
    registro = {"lote_id": None, "erro": None}
    if repositorio.banco_configurado():
        try:
            registro["lote_id"] = repositorio.gravar_lote(lote, resposta, repositorio.modo_atual())
        except Exception as e:
            print(f"[Supabase] falha ao gravar: {e}")
            registro["erro"] = str(e)
    return resposta, registro


def processar(lote: LoteEntrada) -> dict:
    return processar_com_registro(lote)[0]
