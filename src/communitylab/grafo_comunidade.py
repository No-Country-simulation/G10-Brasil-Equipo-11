"""Grafo de Conhecimento da Comunidade (inspirado em Graphify).

Responsável: Marcelo Sales (devmarcelosales).

Mapeia as interações da comunidade em uma estrutura de grafo auditável,
distinguindo explicitamente entre:
  - EXTRACTED (confiança 1.0): fatos extraídos diretamente das mensagens
    (autor publicou no canal, mencionou tópico, tipo de interação).
  - INFERRED (confiança < 1.0): conexões semânticas deduzidas pela topologia
    (afinidade temática entre membros distintos ou pontes entre canais).
"""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import re
from typing import Any

from app.schemas import Interacao, LoteEntrada


TERMOS_TECNICOS_CONHECIDOS = {
    "oci": "OCI Cloud",
    "bucket": "OCI Object Storage",
    "python": "Python",
    "langgraph": "LangGraph",
    "langchain": "LangChain",
    "gemini": "Google Gemini",
    "rag": "RAG",
    "sql": "SQL / Banco de Dados",
    "supabase": "Supabase",
    "streamlit": "Streamlit",
    "fastapi": "FastAPI",
    "api": "API REST",
    "docker": "Docker",
    "git": "Git / GitHub",
    "github": "Git / GitHub",
    "vaga": "Empregabilidade",
    "contratad": "Empregabilidade",
    "estágio": "Empregabilidade",
    "estagio": "Empregabilidade",
    "júnior": "Empregabilidade",
    "junior": "Empregabilidade",
    "prompt": "Engenharia de Prompts",
    "llm": "Modelos de Linguagem (LLMs)",
}


@dataclass(frozen=True)
class NoGrafo:
    id: str
    rotulo: str
    tipo: str  # "membro" | "canal" | "topico" | "categoria"
    peso: int = 1


@dataclass(frozen=True)
class ArestaGrafo:
    origem: str
    destino: str
    relacao: str
    natureza: str  # "EXTRACTED" | "INFERRED"
    confianca: float = 1.0
    evidencia: str = ""


@dataclass
class GrafoComunidade:
    nos: dict[str, NoGrafo] = field(default_factory=dict)
    arestas: list[ArestaGrafo] = field(default_factory=list)

    def adicionar_no(self, id_no: str, rotulo: str, tipo: str) -> None:
        if id_no in self.nos:
            atual = self.nos[id_no]
            self.nos[id_no] = NoGrafo(
                id=atual.id,
                rotulo=atual.rotulo,
                tipo=atual.tipo,
                peso=atual.peso + 1,
            )
        else:
            self.nos[id_no] = NoGrafo(id=id_no, rotulo=rotulo, tipo=tipo, peso=1)

    def adicionar_aresta(
        self,
        origem: str,
        destino: str,
        relacao: str,
        natureza: str = "EXTRACTED",
        confianca: float = 1.0,
        evidencia: str = "",
    ) -> None:
        if origem == destino:
            return
        for existente in self.arestas:
            if (
                existente.origem == origem
                and existente.destino == destino
                and existente.relacao == relacao
                and existente.natureza == natureza
            ):
                return
        self.arestas.append(
            ArestaGrafo(
                origem=origem,
                destino=destino,
                relacao=relacao,
                natureza=natureza,
                confianca=round(confianca, 2),
                evidencia=evidencia,
            )
        )

    def graus(self) -> dict[str, int]:
        contagem: Counter[str] = Counter()
        for aresta in self.arestas:
            contagem[aresta.origem] += 1
            contagem[aresta.destino] += 1
        return dict(contagem)

    def hubs(self, limite: int = 5) -> list[dict[str, Any]]:
        """Retorna os nós mais conectados ('God Nodes') do grafo comunitário."""
        graus_nos = self.graus()
        ordenados = sorted(
            self.nos.values(),
            key=lambda no: (graus_nos.get(no.id, 0), no.peso),
            reverse=True,
        )
        return [
            {
                "id": no.id,
                "rotulo": no.rotulo,
                "tipo": no.tipo,
                "grau": graus_nos.get(no.id, 0),
                "ocorrencias": no.peso,
            }
            for no in ordenados[:limite]
        ]

    def resumo(self) -> dict[str, Any]:
        extraidas = sum(1 for a in self.arestas if a.natureza == "EXTRACTED")
        inferidas = sum(1 for a in self.arestas if a.natureza == "INFERRED")
        return {
            "total_nos": len(self.nos),
            "total_arestas": len(self.arestas),
            "arestas_extraidas": extraidas,
            "arestas_inferidas": inferidas,
            "hubs_principais": self.hubs(limite=5),
        }

    def para_dict(self) -> dict[str, Any]:
        return {
            "resumo": self.resumo(),
            "nos": [asdict(n) for n in self.nos.values()],
            "arestas": [asdict(a) for a in self.arestas],
        }

    def exportar_mermaid(self) -> str:
        """Gera representação Mermaid (flowchart LR) para relatórios e documentação."""
        linhas = ["flowchart LR"]
        ids_seguros = {
            id_no: re.sub(r"[^a-zA-Z0-9_]", "_", id_no)
            for id_no in self.nos
        }
        for id_no, no in self.nos.items():
            seguro = ids_seguros[id_no]
            rotulo_limpo = no.rotulo.replace('"', "'")
            linhas.append(f'    {seguro}["{rotulo_limpo} ({no.tipo})"]')

        for aresta in self.arestas:
            orig = ids_seguros.get(aresta.origem, aresta.origem)
            dest = ids_seguros.get(aresta.destino, aresta.destino)
            seta = "-->" if aresta.natureza == "EXTRACTED" else "-.->"
            linhas.append(f'    {orig} {seta}|"{aresta.relacao}"| {dest}')

        return "\n".join(linhas)


def extrair_topicos_texto(texto: str, canal: str = "") -> list[str]:
    """Identifica tópicos técnicos explícitos na mensagem ou no canal."""
    texto_baixo = texto.lower()
    encontrados: list[str] = []
    for radical, topico_canonico in TERMOS_TECNICOS_CONHECIDOS.items():
        if radical in texto_baixo and topico_canonico not in encontrados:
            encontrados.append(topico_canonico)

    if not encontrados and canal.strip():
        topico_canal = canal.strip().lstrip("#").replace("-", " ").title()
        if topico_canal:
            encontrados.append(topico_canal)

    return encontrados


def construir_grafo_comunidade(lote: LoteEntrada | list[Interacao]) -> GrafoComunidade:
    """Constrói o grafo de conhecimento a partir de um LoteEntrada ou lista de interações."""
    interacoes = lote.interacoes if isinstance(lote, LoteEntrada) else lote
    grafo = GrafoComunidade()

    membros_por_topico: dict[str, list[str]] = defaultdict(list)
    canais_por_topico: dict[str, list[str]] = defaultdict(list)

    for interacao in interacoes:
        id_autor = f"membro:{interacao.autor.strip()}"
        id_canal = f"canal:{interacao.canal.strip()}"
        id_tipo = f"categoria:{interacao.tipo.strip()}"

        grafo.adicionar_no(id_autor, interacao.autor.strip(), "membro")
        grafo.adicionar_no(id_canal, interacao.canal.strip(), "canal")
        grafo.adicionar_no(id_tipo, interacao.tipo.strip(), "categoria")

        # Arestas EXTRACTED (fatos diretos da interação)
        grafo.adicionar_aresta(
            origem=id_autor,
            destino=id_canal,
            relacao="PUBLICOU_EM",
            natureza="EXTRACTED",
            confianca=1.0,
            evidencia=interacao.texto[:80],
        )
        grafo.adicionar_aresta(
            origem=id_autor,
            destino=id_tipo,
            relacao="INTERAGIU_COMO",
            natureza="EXTRACTED",
            confianca=1.0,
            evidencia=interacao.tipo,
        )

        topicos = extrair_topicos_texto(interacao.texto, interacao.canal)
        for topico in topicos:
            id_topico = f"topico:{topico}"
            grafo.adicionar_no(id_topico, topico, "topico")
            grafo.adicionar_aresta(
                origem=id_autor,
                destino=id_topico,
                relacao="MENCIONOU_TOPICO",
                natureza="EXTRACTED",
                confianca=1.0,
                evidencia=interacao.texto[:80],
            )
            grafo.adicionar_aresta(
                origem=id_canal,
                destino=id_topico,
                relacao="DEBATE_TOPICO",
                natureza="EXTRACTED",
                confianca=1.0,
                evidencia=f"{interacao.canal} -> {topico}",
            )
            if id_autor not in membros_por_topico[id_topico]:
                membros_por_topico[id_topico].append(id_autor)
            if id_canal not in canais_por_topico[id_topico]:
                canais_por_topico[id_topico].append(id_canal)

    # Arestas INFERRED (afinidades semânticas e pontes entre canais)
    for id_topico, membros in membros_por_topico.items():
        rotulo_topico = grafo.nos[id_topico].rotulo
        for i in range(len(membros)):
            for j in range(i + 1, len(membros)):
                grafo.adicionar_aresta(
                    origem=membros[i],
                    destino=membros[j],
                    relacao="AFINIDADE_TEMATICA",
                    natureza="INFERRED",
                    confianca=0.85,
                    evidencia=f"Interesse compartilhado em {rotulo_topico}",
                )

    for id_topico, canais in canais_por_topico.items():
        rotulo_topico = grafo.nos[id_topico].rotulo
        for i in range(len(canais)):
            for j in range(i + 1, len(canais)):
                grafo.adicionar_aresta(
                    origem=canais[i],
                    destino=canais[j],
                    relacao="PONTE_ENTRE_CANAIS",
                    natureza="INFERRED",
                    confianca=0.80,
                    evidencia=f"Tópico transversal: {rotulo_topico}",
                )

    return grafo
