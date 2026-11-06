"""Avaliação auditável da classificação, sem geração de ativos ou persistência OCI."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Callable, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ia import decidir_rota
from app.schemas import Analise, Interacao, Sentimento, TipoInteracao

TIPOS = get_args(TipoInteracao)
SENTIMENTOS = get_args(Sentimento)
ROTAS = get_args(Analise.model_fields["rota"].annotation)
CENARIOS = ("tipo_oculto", "tipo_informado")


def hash_casos(casos: list[dict]) -> str:
    """Identifica o conteúdo revisado, independentemente da formatação do JSON."""
    conteudo = json.dumps(casos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


class RevisaoAnotacao(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    revisor: str = Field(min_length=1)
    data: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    metodo: Literal["conferencia_individual_de_propostas"]
    decisao: Literal["aprovado_sem_alteracoes"]
    escopo: Literal["rotulos_justificativas_e_criterios"]
    versao_criterios: str = Field(min_length=1)
    versao_origem: str = Field(min_length=1)
    dataset_origem_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    casos_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    casos_revisados: list[str] = Field(min_length=1)

    @field_validator("revisor", "versao_criterios", "versao_origem")
    @classmethod
    def conferir_texto(cls, valor):
        if not valor.strip():
            raise ValueError("Revisor e versões devem ser preenchidos.")
        return valor

    @field_validator("data")
    @classmethod
    def conferir_data(cls, valor):
        date.fromisoformat(valor)
        return valor


class Referencia(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    tipo: TipoInteracao
    sentimento: Sentimento
    relevancia_min: int = Field(ge=0, le=10)
    relevancia_max: int = Field(ge=0, le=10)
    rota: Literal["case_sucesso", "faq", "alerta", "nenhuma"]

    @model_validator(mode="after")
    def conferir_intervalo_e_rota(self):
        if not 0 <= self.relevancia_max - self.relevancia_min <= 3:
            raise ValueError("Intervalo de relevância invertido ou maior que três pontos.")
        for valor in (self.relevancia_min, self.relevancia_max):
            if decidir_rota(self.tipo, self.sentimento, valor) != self.rota:
                raise ValueError("Rota de referência incompatível com o intervalo e a regra oficial.")
        return self


class CasoAvaliacao(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^AV[0-9]{3,}$")
    grupo: Literal["referencia", "desafio"]
    entrada: Interacao
    referencia: Referencia
    justificativa: str = Field(min_length=10)
    evidencia: str = Field(min_length=3)
    marcadores: list[str]
    revisao_humana: bool
    motivo_revisao: str | None

    @model_validator(mode="after")
    def conferir_evidencia(self):
        if any(not getattr(self.entrada, campo).strip() for campo in ("autor", "canal", "texto")):
            raise ValueError("Autor, canal e texto devem ser preenchidos.")
        if self.evidencia not in self.entrada.texto:
            raise ValueError("Evidência precisa ser um trecho literal da mensagem.")
        if self.entrada.tipo != self.referencia.tipo:
            raise ValueError("O cenário com tipo informado exige a anotação de tipo na entrada.")
        if self.revisao_humana and not (self.motivo_revisao or "").strip():
            raise ValueError("Caso que exige revisão precisa de motivo.")
        if self.grupo == "desafio" and not self.revisao_humana:
            raise ValueError("Casos de desafio precisam de revisão humana.")
        if not self.marcadores or any(not m.strip() for m in self.marcadores):
            raise ValueError("Informe marcadores descritivos para cada caso.")
        return self


class BaseAvaliacao(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    versao: str = Field(min_length=1)
    natureza: Literal["sintetica"]
    status_anotacao: Literal["proposta_pendente_revisao_humana", "revisada_individualmente"]
    revisao_anotacao: RevisaoAnotacao | None = None
    descricao: str = Field(min_length=10)
    casos: list[CasoAvaliacao] = Field(min_length=1)

    @model_validator(mode="after")
    def conferir_unicidade(self):
        ids = [c.id for c in self.casos]
        textos = [" ".join(unicodedata.normalize("NFC", c.entrada.texto).casefold().split()) for c in self.casos]
        if len(set(ids)) != len(ids) or len(set(textos)) != len(textos):
            raise ValueError("A base contém IDs ou mensagens duplicados.")
        if self.status_anotacao == "proposta_pendente_revisao_humana":
            if self.revisao_anotacao is not None:
                raise ValueError("Base pendente não pode conter registro de aprovação.")
        else:
            revisao = self.revisao_anotacao
            if revisao is None:
                raise ValueError("Base revisada exige registro de revisão individual.")
            if (len(set(revisao.casos_revisados)) != len(revisao.casos_revisados)
                    or set(revisao.casos_revisados) != set(ids)):
                raise ValueError("A revisão deve identificar todos os casos, sem IDs duplicados ou desconhecidos.")
            if revisao.casos_sha256 != hash_casos([caso.model_dump() for caso in self.casos]):
                raise ValueError("O conteúdo dos casos mudou: a revisão registrada não corresponde a esta base.")
        return self


def _json_sem_duplicatas(pares):
    dados = {}
    for chave, valor in pares:
        if chave in dados:
            raise ValueError(f"Chave JSON duplicada: {chave}")
        dados[chave] = valor
    return dados


def ler_json(caminho: Path):
    return json.loads(Path(caminho).read_text(encoding="utf-8-sig"), object_pairs_hook=_json_sem_duplicatas)


def _validar_base(base: dict) -> dict:
    if not isinstance(base, dict):
        raise ValueError("A base deve ser um objeto JSON.")
    dados = {k: v for k, v in base.items() if k != "_sha256"}
    if not isinstance(dados.get("casos"), list):
        raise ValueError("A base deve conter uma lista de casos.")
    # Interacao é um contrato compartilhado permissivo; a base de avaliação é estrita.
    for caso in dados.get("casos", []):
        entrada = caso.get("entrada", {}) if isinstance(caso, dict) else {}
        if not isinstance(entrada, dict) or set(entrada) != set(Interacao.model_fields):
            raise ValueError("A entrada de avaliação deve conter exatamente autor, canal, tipo e texto.")
        Interacao.model_validate(entrada, strict=True)
    return BaseAvaliacao.model_validate(dados).model_dump()


def carregar_base(caminho: Path) -> dict:
    dados = _validar_base(ler_json(caminho))
    dados["_sha256"] = hashlib.sha256(Path(caminho).read_bytes()).hexdigest()
    return dados


def metricas_classificacao(referencias: list[str], previsoes: list[str | None], rotulos) -> dict:
    """Falhas contam no denominador; macro-F1 usa apenas classes com suporte real.

    Precisão sem predições e recall sem referência são indefinidos (None).
    F1 é zero quando só um dos dois suportes é positivo, None se ambos são zero.
    """
    rotulos = list(rotulos)
    if len(referencias) != len(previsoes) or not rotulos or len(set(rotulos)) != len(rotulos):
        raise ValueError("Comprimentos incompatíveis ou vocabulário inválido.")
    if any(r not in rotulos for r in referencias) or any(p is not None and p not in rotulos for p in previsoes):
        raise ValueError("Rótulo fora do contrato.")
    matriz = [[0] * (len(rotulos) + 1) for _ in rotulos]
    for referencia, previsto in zip(referencias, previsoes):
        matriz[rotulos.index(referencia)][rotulos.index(previsto) if previsto is not None else len(rotulos)] += 1
    por_classe = []
    for i, rotulo in enumerate(rotulos):
        suporte = sum(matriz[i])
        preditos = sum(linha[i] for linha in matriz)
        tp = matriz[i][i]
        por_classe.append({
            "rotulo": rotulo, "suporte": suporte, "preditos": preditos,
            "verdadeiros_positivos": tp,
            "precisao": tp / preditos if preditos else None,
            "recall": tp / suporte if suporte else None,
            "f1": 2 * tp / (suporte + preditos) if suporte + preditos else None,
        })
    presentes = [c for c in por_classe if c["suporte"]]
    total = len(referencias)
    return {
        "total": total, "validos": sum(p is not None for p in previsoes),
        "acuracia": sum(r == p for r, p in zip(referencias, previsoes)) / total if total else None,
        "macro_f1": sum(c["f1"] for c in presentes) / len(presentes) if presentes else None,
        "ponderado_f1": sum(c["f1"] * c["suporte"] for c in presentes) / total if total else None,
        "por_classe": por_classe, "rotulos": rotulos, "matriz_confusao": matriz,
        "classes_com_suporte": len(presentes),
    }


def _validar_analise(valor, entrada: Interacao) -> dict:
    dados = valor.model_dump() if isinstance(valor, Analise) else valor
    if not isinstance(dados, dict) or set(dados) != set(Analise.model_fields):
        raise ValueError("A previsão deve seguir exatamente o contrato Analise.")
    previsto = Analise.model_validate(dados, strict=True).model_dump()
    for campo in ("autor", "canal", "texto"):
        if previsto[campo] != getattr(entrada, campo):
            raise ValueError("A previsão não corresponde à interação de origem.")
    if not previsto["topico"].strip():
        raise ValueError("Tópico vazio.")
    return previsto


def _resumir(casos: list[dict]) -> dict:
    total = len(casos)
    validos = [c for c in casos if c["previsto"] is not None]
    distancias = []
    for caso in validos:
        ref, prev = caso["referencia"], caso["previsto"]
        distancias.append(max(ref["relevancia_min"] - prev["relevancia"], 0, prev["relevancia"] - ref["relevancia_max"]))
    dentro = sum(d == 0 for d in distancias)
    return {
        "cobertura": {"total": total, "validos": len(validos), "falhas": total - len(validos), "taxa": len(validos) / total if total else None},
        "metricas": {campo: metricas_classificacao(
            [c["referencia"][campo] for c in casos],
            [c["previsto"][campo] if c["previsto"] is not None else None for c in casos], rotulos,
        ) for campo, rotulos in (("tipo", TIPOS), ("sentimento", SENTIMENTOS), ("rota", ROTAS))},
        "relevancia": {"total": total, "avaliados": len(validos), "dentro_faixa": dentro,
                       "proporcao_dentro_faixa": dentro / total if total else None,
                       "distancia_media_faixa": sum(distancias) / len(distancias) if distancias else None},
    }


def avaliar(base: dict, classificador: Callable, *, cenario="tipo_oculto", metadados=None) -> dict:
    """Avalia cada mensagem isoladamente. Não modifica a base nem chama o grafo."""
    if cenario not in CENARIOS:
        raise ValueError("Cenário desconhecido.")
    dados = _validar_base(base)
    casos = []
    for caso in dados["casos"]:
        entrada = Interacao.model_validate(caso["entrada"], strict=True)
        if cenario == "tipo_oculto":
            entrada = entrada.model_copy(update={"tipo": "outro"})
        previsto, erro = None, None
        try:
            previsto = _validar_analise(classificador(entrada), entrada)
        except Exception as exc:
            # Não propagar mensagens de provedores: podem conter payloads ou credenciais.
            erro = f"{type(exc).__name__}: classificação ausente, inválida ou indisponível."
        ref = caso["referencia"]
        divergencias = []
        if previsto is None:
            divergencias.append("falha_classificacao")
        else:
            divergencias.extend(c for c in ("tipo", "sentimento", "rota") if previsto[c] != ref[c])
            if not ref["relevancia_min"] <= previsto["relevancia"] <= ref["relevancia_max"]:
                divergencias.append("relevancia")
            if decidir_rota(previsto["tipo"], previsto["sentimento"], previsto["relevancia"]) != previsto["rota"]:
                divergencias.append("consistencia_rota")
        perdeu_alerta = ref["rota"] == "alerta" and (previsto is None or previsto["rota"] != "alerta")
        prioridade = "alta" if perdeu_alerta or erro else ("media" if divergencias or caso["revisao_humana"] else "baixa")
        casos.append({**caso, "status_anotacao": dados["status_anotacao"],
                      "entrada": entrada.model_dump(), "previsto": previsto, "erro": erro,
                      "divergencias": divergencias, "prioridade": prioridade})
    resumo = _resumir(casos)
    recortes = {grupo: _resumir([c for c in casos if c["grupo"] == grupo]) for grupo in ("referencia", "desafio")}
    # Metas usam o recorte principal; os desafios são reportados separadamente.
    principal = recortes["referencia"]
    recall_alerta = next(c["recall"] for c in principal["metricas"]["rota"]["por_classe"] if c["rotulo"] == "alerta")
    metas = [
        ("macro_f1_tipo", "Macro-F1 de tipo no recorte referência", principal["metricas"]["tipo"]["macro_f1"], .80),
        ("macro_f1_sentimento", "Macro-F1 de sentimento no recorte referência", principal["metricas"]["sentimento"]["macro_f1"], .75),
        ("macro_f1_rota", "Macro-F1 de rota no recorte referência", principal["metricas"]["rota"]["macro_f1"], .85),
        ("recall_alerta", "Recall de alerta no recorte referência", recall_alerta, .90),
        ("relevancia_faixa", "Relevância dentro da faixa no recorte referência", principal["relevancia"]["proporcao_dentro_faixa"], .80),
        ("cobertura", "Cobertura de saídas válidas em toda a base", resumo["cobertura"]["taxa"], 1.0),
        ("cobertura_classes", "Cobertura do vocabulário no recorte referência", sum(m["classes_com_suporte"] for m in principal["metricas"].values()) / (len(TIPOS) + len(SENTIMENTOS) + len(ROTAS)), 1.0),
        ("consistencia_rota", "Saídas válidas com rota coerente com a regra oficial", sum(c["previsto"] is not None and "consistencia_rota" not in c["divergencias"] for c in casos) / len(casos), 1.0),
    ]
    validos = [c["previsto"] for c in casos if c["previsto"] is not None]
    informados = dict(metadados or {})
    informados.update({"versao_base": dados["versao"], "natureza": dados["natureza"],
                       "status_anotacao": dados["status_anotacao"], "cenario": cenario,
                       "revisao_anotacao": dados["revisao_anotacao"],
                       "dataset_sha256": base.get("_sha256") or hashlib.sha256(json.dumps(dados, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                       "python": platform.python_version()})
    informados.setdefault("modo", "avaliacao_local")
    informados.setdefault("modelo", "classificador_fornecido")
    informados.setdefault("commit_base", "nao_informado")
    return {
        "metadados": informados, **resumo, "recortes": recortes,
        "criterios": [{"id": i, "descricao": d, "valor": v, "limiar": l, "atendido": v >= l if v is not None else None} for i, d, v, l in metas],
        "indicadores": {
            "tipos_referencia": dict(Counter(c["referencia"]["tipo"] for c in casos)),
            "tipos_previstos": dict(Counter(p["tipo"] for p in validos)),
            "sentimentos_previstos": dict(Counter(p["sentimento"] for p in validos)),
            "rotas_previstas": dict(Counter(p["rota"] for p in validos)),
            "topicos": [{"topico": t, "quantidade": n} for t, n in sorted(Counter(p["topico"] for p in validos).items(), key=lambda x: (-x[1], x[0]))],
            "alertas_nao_detectados": sum(c["referencia"]["rota"] == "alerta" and (c["previsto"] is None or c["previsto"]["rota"] != "alerta") for c in casos),
            "casos_revisao": len(casos),
            "inconsistencias_rota": sum("consistencia_rota" in c["divergencias"] for c in casos),
        },
        "casos": sorted(casos, key=lambda c: ({"alta": 0, "media": 1, "baixa": 2}[c["prioridade"]], c["id"])),
        "limitacoes": [
            "Base sintética e intencionalmente balanceada por tipo; não estima prevalência, engajamento ou impacto em comunidade real.",
            ("Referências, justificativas e critérios conferidos e aprovados individualmente pelo responsável registrado; "
             "não representa validação conjunta da equipe, aprovação de previsões ou autorização de produção."
             if dados["revisao_anotacao"] else
             "Referências e metas são propostas pendentes de revisão humana; nenhuma pontuação autoriza publicação ou uso em produção."),
            "Macro-F1 considera classes com suporte de referência. Classes ausentes não demonstram qualidade; consulte os suportes.",
            "Falhas contam como erro na acurácia, no recall e na proporção de relevância dentro da faixa; a distância média usa somente previsões válidas.",
            "Metas numéricas usam o recorte referência; desafios permanecem visíveis no resultado total e no recorte próprio.",
            "Tipo informado é avaliação assistida: o mock reutiliza essa anotação. Não comparar esse resultado como inferência autônoma.",
            "Tópicos são contagens de texto exato, sem agrupamento semântico. No mock, derivam do canal; tópicos precisam de avaliação qualitativa.",
            "Roteamento é uma regra determinística; acerto de rota não valida sentimento, geração de conteúdo, Gemini ou armazenamento OCI.",
            "A fila prioriza a conferência deste conjunto de avaliação; não implementa aprovação de conteúdo nem triagem operacional da comunidade.",
        ],
    }


def validar_previsoes(caminho: Path, base: dict, cenario: str) -> dict:
    """Importa previsões por ID; ausências ficam como falhas na avaliação completa."""
    envelope = ler_json(caminho)
    if not isinstance(envelope, dict) or set(envelope) != {"dataset_sha256", "cenario", "modelo", "previsoes"}:
        raise ValueError("Envelope de previsões inválido.")
    hash_base = base.get("_sha256")
    if not isinstance(hash_base, str) or re.fullmatch(r"[0-9a-f]{64}", hash_base) is None:
        raise ValueError("Carregue a base de um arquivo para verificar seu SHA256.")
    if cenario not in CENARIOS or envelope["dataset_sha256"] != hash_base or envelope["cenario"] != cenario:
        raise ValueError("Previsões pertencem a outra base ou cenário.")
    if not isinstance(envelope["modelo"], str) or not envelope["modelo"].strip():
        raise ValueError("Informe o modelo declarado na origem das previsões.")
    if not isinstance(envelope["previsoes"], list):
        raise ValueError("Previsões devem ser uma lista.")
    conhecidos = {c["id"]: c for c in base["casos"]}
    previsoes = {}
    for item in envelope["previsoes"]:
        if not isinstance(item, dict) or set(item) != {"id", "analise"} or not isinstance(item["id"], str):
            raise ValueError("Cada previsão deve conter id e analise.")
        identificador = item["id"]
        if identificador not in conhecidos or identificador in previsoes:
            raise ValueError("ID de previsão desconhecido ou duplicado.")
        # A estrutura da análise é conferida por caso; inválidos contam como falha.
        previsoes[identificador] = item["analise"]
    return previsoes


def _celula_segura(valor):
    if valor is None:
        return ""
    if isinstance(valor, str) and (valor.lstrip().startswith(("=", "+", "-", "@")) or valor.startswith(("\t", "\r", "\n"))):
        return "'" + valor
    return valor


def _escrever_csv(caminho, colunas, linhas):
    with Path(caminho).open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(colunas)
        escritor.writerows([_celula_segura(v) for v in linha] for linha in linhas)


def salvar_resultados(resultado: dict, diretorio: Path) -> list[Path]:
    from communitylab.relatorio_avaliacao import renderizar_html

    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for nome, conteudo in (
        ("resultado.json", json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + "\n"),
        ("relatorio.html", renderizar_html(resultado)),
    ):
        destino = diretorio / nome
        destino.write_text(conteudo, encoding="utf-8")
        arquivos.append(destino)
    colunas = ["id", "grupo", "prioridade", "texto", "tipo_referencia", "tipo_previsto", "sentimento_referencia", "sentimento_previsto", "rota_referencia", "rota_prevista", "relevancia_min", "relevancia_max", "relevancia_prevista", "divergencias", "erro", "evidencia", "justificativa", "motivo_revisao", "status_revisao", "tipo_revisado", "sentimento_revisado", "relevancia_min_revisada", "relevancia_max_revisada", "rota_revisada", "revisor", "data_revisao", "observacao"]
    linhas = []
    revisao = resultado["metadados"].get("revisao_anotacao")
    for caso in resultado["casos"]:
        ref, previsto = caso["referencia"], caso["previsto"] or {}
        campos_revisao = (
            ["confirmado", ref["tipo"], ref["sentimento"], ref["relevancia_min"],
             ref["relevancia_max"], ref["rota"], revisao["revisor"], revisao["data"],
             "Referência, justificativa e critérios confirmados em conferência individual de propostas; "
             "não aprova a previsão do classificador nem a publicação de conteúdo."]
            if revisao else ["pendente", "", "", "", "", "", "", "", ""]
        )
        linhas.append([caso["id"], caso["grupo"], caso["prioridade"], caso["entrada"]["texto"],
                       ref["tipo"], previsto.get("tipo"), ref["sentimento"], previsto.get("sentimento"),
                       ref["rota"], previsto.get("rota"), ref["relevancia_min"], ref["relevancia_max"], previsto.get("relevancia"),
                       ", ".join(caso["divergencias"]), caso["erro"], caso["evidencia"], caso["justificativa"],
                       caso["motivo_revisao"], *campos_revisao])
    destino = diretorio / "revisao_classificacoes.csv"
    _escrever_csv(destino, colunas, linhas)
    arquivos.append(destino)
    destino = diretorio / "metricas_por_categoria.csv"
    campos = ["rotulo", "suporte", "preditos", "verdadeiros_positivos", "precisao", "recall", "f1"]
    _escrever_csv(destino, ["dimensao", *campos], ([dimensao, *(c[k] for k in campos)] for dimensao, metrica in resultado["metricas"].items() for c in metrica["por_classe"]))
    arquivos.append(destino)
    for dimensao, metrica in resultado["metricas"].items():
        destino = diretorio / f"matriz_confusao_{dimensao}.csv"
        _escrever_csv(destino, ["referencia / previsto", *metrica["rotulos"], "falha"], ([rotulo, *linha] for rotulo, linha in zip(metrica["rotulos"], metrica["matriz_confusao"])))
        arquivos.append(destino)
    return arquivos
