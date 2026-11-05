"""Testes do Grafo de Conhecimento Comunitário e Guardrails Anti-Slop.

Responsável: Marcelo Sales (devmarcelosales).
"""
from app.ia import higienizar_texto_editorial, validar_ancoragem_factual
from app.prompts import DIRETRIZES_ANTI_SLOP, FAQ_SISTEMA, LINKEDIN_SISTEMA, NEWSLETTER_SISTEMA
from app.schemas import Interacao, LoteEntrada
from communitylab.adapter import carregar_lote, carregar_lote_bytes
from communitylab.grafo_comunidade import construir_grafo_comunidade


def test_grafo_extrai_nos_e_arestas_diretas_e_inferidas():
    lote = LoteEntrada(
        origem_comunidade="Discord_Teste",
        periodo_referencia="Semana_04",
        interacoes=[
            Interacao(
                autor="Ana Silva",
                canal="#duvidas",
                tipo="pergunta_tecnica",
                texto="Como configuro o bucket na OCI usando Python?",
            ),
            Interacao(
                autor="Carlos Mendes",
                canal="#projetos",
                tipo="projeto",
                texto="Subi minha API com Python e conectei no bucket da OCI!",
            ),
        ],
    )

    grafo = construir_grafo_comunidade(lote)
    resumo = grafo.resumo()

    assert resumo["total_nos"] >= 6
    assert resumo["arestas_extraidas"] >= 6
    assert resumo["arestas_inferidas"] >= 2

    naturezas = {a.natureza for a in grafo.arestas}
    assert "EXTRACTED" in naturezas
    assert "INFERRED" in naturezas

    relacoes_inferidas = {a.relacao for a in grafo.arestas if a.natureza == "INFERRED"}
    assert "AFINIDADE_TEMATICA" in relacoes_inferidas
    assert "PONTE_ENTRE_CANAIS" in relacoes_inferidas


def test_grafo_lote_exemplo_oficial_identifica_hubs_e_exporta_mermaid():
    lote = carregar_lote("data/interacoes_exemplo.json")
    grafo = construir_grafo_comunidade(lote)
    dados = grafo.para_dict()

    assert dados["resumo"]["total_nos"] > 10
    assert dados["resumo"]["arestas_extraidas"] > 10
    assert len(dados["resumo"]["hubs_principais"]) == 5

    mermaid = grafo.exportar_mermaid()
    assert mermaid.startswith("flowchart LR")
    assert "PUBLICOU_EM" in mermaid


def test_guardrail_anti_slop_remove_aberturas_cliches():
    texto_sujo = "No cenário tecnológico atual, a aluna Mariana conquistou sua vaga de estágio."
    limpo = higienizar_texto_editorial(texto_sujo)
    assert limpo == "A aluna Mariana conquistou sua vaga de estágio."

    texto_mundo = "Em um mundo cada vez mais conectado, aprender Python abre portas."
    assert higienizar_texto_editorial(texto_mundo) == "Aprender Python abre portas."


def test_prompts_incluem_diretrizes_anti_slop():
    assert DIRETRIZES_ANTI_SLOP in LINKEDIN_SISTEMA
    assert DIRETRIZES_ANTI_SLOP in NEWSLETTER_SISTEMA
    assert DIRETRIZES_ANTI_SLOP in FAQ_SISTEMA


def test_validacao_ancoragem_factual():
    origem = "Fui contratada como desenvolvedora júnior após apresentar meu projeto com LangGraph!"
    autor = "Mariana Souza"

    assert validar_ancoragem_factual(
        "Parabéns Mariana Souza pela contratação com seu projeto em LangGraph!",
        origem,
        autor,
    )
    assert not validar_ancoragem_factual(
        "Texto genérico sem relação alguma.",
        origem,
        "Outro Nome",
    )


def test_carregar_lote_bytes_csv_ponto_e_virgula_cp1252():
    csv_cp1252 = (
        "autor;canal;tipo;texto\n"
        "João Sales;#vagas;depoimento;Consegui minha transição para programação e IA!\n"
    ).encode("cp1252")

    lote = carregar_lote_bytes(
        csv_cp1252,
        nome_arquivo="transicao.csv",
        origem_comunidade="Discord_G10",
        periodo_referencia="Semana_04",
    )
    assert len(lote.interacoes) == 1
    assert lote.interacoes[0].autor == "João Sales"
    assert "transição para programação" in lote.interacoes[0].texto
