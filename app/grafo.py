"""Orquestração com LangGraph. Dono: pessoa 2.

    classificar ──┬─> gerar_case ───────┐
    (+ FAQs)      ├─> gerar_faq ────────┤
                  ├─> gerar_alerta ─────┼─> salvar_oci ─> FIM
                  └─> gerar_newsletter ─┘

O roteador só abre os ramos que têm interações daquela rota no lote; a newsletter sempre roda.
Os ramos rodam em paralelo e se juntam antes de salvar.

O que encurta o lote: a FAQ de cada dúvida começa assim que aquela mensagem é classificada
(`mapear_em_cadeia`), sem esperar a classificação das outras, e a newsletter, que só depende
das análises, roda junto com os outros ramos em vez de depois deles.

Com Oracle ligado, quem coordena banco e Object Storage é `app.main`:
o grafo recebe `persistir_pacote=False` e os IDs das interações para registrar
de qual mensagem cada ativo saiu (`fontes_ativos`).
"""
from collections import Counter
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from . import ia
from .llm import mapear, mapear_em_cadeia
from .schemas import Alerta, Analise, LoteEntrada, SugestaoFaq
from .storage import bucket_name, caminho_objeto, salvar_pacote


def mesclar(a: dict, b: dict) -> dict:
    return {**a, **b}


class Estado(TypedDict, total=False):
    lote: LoteEntrada
    analises: list[Analise]
    # FAQs já geradas durante a classificação, pela posição da mensagem no lote.
    faqs_geradas: dict[int, SugestaoFaq]
    ativos: Annotated[dict, mesclar]
    armazenamento: dict
    persistir_pacote: bool
    processamento_id: str | None
    interaction_ids: list[str]
    fontes_ativos: Annotated[dict, mesclar]


def _faq_se_for_duvida(analise: Analise) -> SugestaoFaq | None:
    return ia.gerar_faq(analise) if analise.rota == "faq" else None


def no_classificar(e: Estado) -> Estado:
    # As mensagens são independentes: classifica em paralelo (ordem preservada).
    # A FAQ de uma dúvida só depende da análise dela, então começa logo em seguida.
    pares = mapear_em_cadeia(ia.classificar, _faq_se_for_duvida, e["lote"].interacoes)
    return {
        "analises": [analise for analise, _ in pares],
        "faqs_geradas": {
            indice: faq
            for indice, (_, faq) in enumerate(pares)
            if faq is not None
        },
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

    # A newsletter só depende das análises: roda junto com os outros ramos.
    return [*ramos, "gerar_newsletter"]


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

    # Normalmente todas já vieram da classificação; gera aqui só as que faltarem.
    prontas = dict(e.get("faqs_geradas") or {})
    faltantes = [index for index in indices if index not in prontas]
    prontas.update(zip(
        faltantes,
        mapear(ia.gerar_faq, [e["analises"][index] for index in faltantes], aquecer_cache=False),
    ))

    faqs = [prontas[index].model_dump() for index in indices]

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

    periodo = e["lote"].periodo_referencia
    processamento_id = e.get("processamento_id")

    try:
        armazenamento = salvar_pacote(
            pacote,
            periodo,
            processamento_id=processamento_id,
        )
    except Exception as exc:
        # Falha de armazenamento não derruba o processamento: volta como "erro".
        print(f"[OCI] falha ao salvar o pacote: {type(exc).__name__}")
        armazenamento = {
            "bucket": bucket_name(),
            "caminho_objeto": caminho_objeto(periodo, processamento_id),
            "status": "erro",
        }

    return {"armazenamento": armazenamento}


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
        "gerar_newsletter",
    ):
        grafo.add_edge(ramo, "salvar_oci")

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


def processar_com_registro(lote: LoteEntrada) -> tuple[dict, dict]:
    """Caminho do painel Streamlit (plano B): processa e grava no histórico antigo (Supabase).

    Só grava se DATABASE_URL estiver configurada. Falha ao gravar não derruba o
    processamento: o erro volta no registro. O painel web grava no Oracle por `app.main`.
    """
    from . import repositorio

    resposta = processar(lote)
    registro = {"lote_id": None, "erro": None}
    if repositorio.banco_configurado():
        try:
            registro["lote_id"] = repositorio.gravar_lote(lote, resposta, repositorio.modo_atual())
        except Exception as e:
            registro["erro"] = str(e) or type(e).__name__
            print(f"[Supabase] falha ao gravar: {registro['erro']}")
    return resposta, registro
