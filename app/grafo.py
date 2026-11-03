"""Orquestração do pipeline com LangGraph."""
from collections import Counter
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from . import ia
from .schemas import Alerta, Analise, LoteEntrada
from .storage import salvar_pacote


def mesclar(a: dict, b: dict) -> dict:
    return {**a, **b}


class Estado(TypedDict, total=False):
    lote: LoteEntrada
    analises: list[Analise]
    ativos: Annotated[dict, mesclar]
    armazenamento: dict
    persistir_pacote: bool
    processamento_id: str | None
    interaction_ids: list[str]
    fontes_ativos: Annotated[dict, mesclar]


def no_classificar(e: Estado) -> Estado:
    return {
        "analises": [
            ia.classificar(interacao)
            for interacao in e["lote"].interacoes
        ]
    }


def roteador(e: Estado) -> list[str]:
    rotas = {analise.rota for analise in e["analises"]}

    ramos = [
        nome
        for rota, nome in [
            ("case_sucesso", "gerar_case"),
            ("faq", "gerar_faq"),
            ("alerta", "gerar_alerta"),
        ]
        if rota in rotas
    ]

    return ramos or ["gerar_newsletter"]


def no_case(e: Estado) -> Estado:
    candidatos = [
        (index, analysis)
        for index, analysis in enumerate(e["analises"])
        if analysis.rota == "case_sucesso"
    ]

    indice, melhor = max(
        candidatos,
        key=lambda item: item[1].relevancia,
    )

    ids = e.get("interaction_ids", [])
    fontes = [ids[indice]] if indice < len(ids) else []

    return {
        "ativos": {
            "post_linkedin": ia.gerar_linkedin(
                melhor
            ).model_dump()
        },
        "fontes_ativos": {
            "post": fontes,
        },
    }


def no_faq(e: Estado) -> Estado:
    indices = [
        index
        for index, analysis in enumerate(e["analises"])
        if analysis.rota == "faq"
    ]

    faqs = [
        ia.gerar_faq(e["analises"][index]).model_dump()
        for index in indices
    ]

    ids = e.get("interaction_ids", [])

    fontes = {
        f"faq_{numero}": (
            [ids[indice]]
            if indice < len(ids)
            else []
        )
        for numero, indice in enumerate(indices)
    }

    return {
        "ativos": {
            "sugestao_conteudo_faq": faqs,
        },
        "fontes_ativos": fontes,
    }


def no_alerta(e: Estado) -> Estado:
    indices = [
        index
        for index, analysis in enumerate(e["analises"])
        if analysis.rota == "alerta"
    ]

    alertas = [
        Alerta(
            autor=e["analises"][index].autor,
            motivo=(
                f"{e['analises'][index].sentimento} em "
                f"{e['analises'][index].canal}: "
                f"{e['analises'][index].texto[:100]}"
            ),
        ).model_dump()
        for index in indices
    ]

    ids = e.get("interaction_ids", [])

    fontes = {
        f"alerta_{numero}": (
            [ids[indice]]
            if indice < len(ids)
            else []
        )
        for numero, indice in enumerate(indices)
    }

    return {
        "ativos": {
            "alertas_comunidade": alertas,
        },
        "fontes_ativos": fontes,
    }


def no_newsletter(e: Estado) -> Estado:
    ids = list(e.get("interaction_ids", []))

    return {
        "ativos": {
            "destaque_newsletter_semanal": (
                ia.gerar_newsletter(
                    e["analises"]
                ).model_dump()
            )
        },
        "fontes_ativos": {
            "newsletter": ids,
        },
    }


def montar_resposta(
    e: Estado,
    armazenamento: dict,
) -> dict:
    analises = e["analises"]

    sentimento = Counter(
        a.sentimento for a in analises
    ).most_common(1)[0][0]

    topicos = [
        topico
        for topico, _ in Counter(
            a.topico for a in analises
        ).most_common(5)
    ]

    return {
        "status": "sucesso",
        "resumo_comunidade": {
            "total_interacoes_processadas": len(analises),
            "sentimento_predominante": sentimento,
            "topicos_principais": topicos,
        },
        "analises": [
            analysis.model_dump()
            for analysis in analises
        ],
        "ativos_distribuicao_gerados": e.get(
            "ativos", {}
        ),
        "fontes_ativos": e.get(
            "fontes_ativos", {}
        ),
        "armazenamento_oci": armazenamento,
    }


def no_salvar(e: Estado) -> Estado:
    # O backend coordena Oracle e OCI separadamente.
    if not e.get("persistir_pacote", True):
        return {
            "armazenamento": {
                "bucket": "",
                "caminho_objeto": "",
                "status": "pendente",
            }
        }

    pacote = montar_resposta(e, armazenamento={})

    return {
        "armazenamento": salvar_pacote(
            pacote,
            e["lote"].periodo_referencia,
            processamento_id=e.get("processamento_id"),
        )
    }


def construir_grafo():
    grafo = StateGraph(Estado)

    grafo.add_node("classificar", no_classificar)
    grafo.add_node("gerar_case", no_case)
    grafo.add_node("gerar_faq", no_faq)
    grafo.add_node("gerar_alerta", no_alerta)
    grafo.add_node("gerar_newsletter", no_newsletter)
    grafo.add_node("salvar_oci", no_salvar)

    grafo.add_edge(START, "classificar")

    grafo.add_conditional_edges(
        "classificar",
        roteador,
        [
            "gerar_case",
            "gerar_faq",
            "gerar_alerta",
            "gerar_newsletter",
        ],
    )

    for ramo in (
        "gerar_case",
        "gerar_faq",
        "gerar_alerta",
    ):
        grafo.add_edge(ramo, "gerar_newsletter")

    grafo.add_edge("gerar_newsletter", "salvar_oci")
    grafo.add_edge("salvar_oci", END)

    return grafo.compile()


GRAFO = construir_grafo()


def processar(
    lote: LoteEntrada,
    *,
    persistir_pacote: bool = True,
    processamento_id: str | None = None,
    interaction_ids: list[str] | None = None,
) -> dict:
    """Executa o pipeline e retorna os resultados estruturados."""
    estado = GRAFO.invoke(
        {
            "lote": lote,
            "ativos": {},
            "persistir_pacote": persistir_pacote,
            "processamento_id": processamento_id,
            "interaction_ids": list(
                interaction_ids or []
            ),
            "fontes_ativos": {},
        }
    )

    return montar_resposta(
        estado,
        estado["armazenamento"],
    )