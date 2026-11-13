"""Análise e geração de ativos. Cada função tem versão real (LLM) e simulada (mock).

A versão mock usa regras simples por palavra-chave. Ela não precisa ser boa,
só precisa devolver o formato certo para o resto do sistema funcionar.
Inclui guardrails Anti-Slop (Humanizer) e verificação de ancoragem factual (Harness²).
"""
import json
import logging
import re
import unicodedata

from . import prompts
from .llm import ErroLLM, chamar_llm_json, esforco_classificacao, esforco_geracao, modo_mock
from .schemas import Analise, DestaqueNewsletter, Interacao, PostLinkedin, SugestaoFaq

log = logging.getLogger("communitylab.ia")

# Mensagens/ativos em que o Claude falhou e o modo simulado foi usado no lugar.
# O teste controlado (scripts/teste_llm.py) lê esta lista para o relatório.
FALHAS: list[dict] = []

POSITIVOS = ("passei", "contratad", "consegui", "aprovad", "grat", "obrigad", "incrível", "adorei", "vaga")
NEGATIVOS = ("difícil", "dificil", "frustrad", "não consigo", "nao consigo", "não consegui", "nao consegui", "não fui aprovado", "nao fui aprovado", "não passei", "nao passei", "sem conseguir", "desistir", "péssim", "ruim", "travad")


# ---------- Guardrails anti-clichê e ancoragem factual (Marcelo) ----------
PADROES_SLOP_INICIO = (
    r"^no cenário (?:tecnológico )?atual[,:\s]+",
    r"^em um mundo cada vez mais [a-záéíóúâêôãõç]+[,:\s]+",
    r"^é importante destacar que\s+",
    r"^vale ressaltar que\s+",
)


def higienizar_texto_editorial(texto: str) -> str:
    """Remove aberturas clichês de IA (anti-slop) e normaliza espaçamento."""
    if not isinstance(texto, str):
        return ""
    limpo = texto.strip()
    for padrao in PADROES_SLOP_INICIO:
        limpo = re.sub(padrao, "", limpo, flags=re.IGNORECASE).strip()
    if limpo and limpo[0].islower():
        limpo = limpo[0].upper() + limpo[1:]
    return limpo


def validar_ancoragem_factual(texto_gerado: str, interacao_origem: str, autor: str) -> bool:
    """Verifica se o conteúdo gerado mantém ancoragem factual mínima no autor ou no relato original."""
    if not texto_gerado or not texto_gerado.strip():
        return False
    gerado_lower = texto_gerado.lower()
    primeiro_nome = autor.split()[0].lower() if autor.strip() else ""
    if primeiro_nome and primeiro_nome in gerado_lower:
        return True
    palavras_origem = {
        p.strip(".,!?:;\"'()[]{}").lower()
        for p in interacao_origem.split()
        if len(p.strip(".,!?:;\"'()[]{}")) >= 4
    }
    return any(palavra in gerado_lower for palavra in palavras_origem)


# ---------- Validação das respostas do modelo ----------
TIPOS = ("depoimento", "pergunta_tecnica", "feedback", "reclamacao", "projeto", "outro")
SENTIMENTOS = ("Altamente Positivo", "Positivo", "Neutro", "Negativo", "Altamente Negativo")

# Schemas da saída estruturada: a API garante JSON neste formato (sem JSON quebrado nem rótulo fora da lista).
SCHEMA_CLASSIFICACAO = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": list(TIPOS)},
        "sentimento": {"type": "string", "enum": list(SENTIMENTOS)},
        "topico": {"type": "string"},
        "relevancia": {"type": "integer"},
    },
    "required": ["tipo", "sentimento", "topico", "relevancia"],
    "additionalProperties": False,
}


def schema_textos(*campos: str) -> dict:
    """Schema de um objeto só com campos de texto obrigatórios."""
    return {
        "type": "object",
        "properties": {c: {"type": "string"} for c in campos},
        "required": list(campos),
        "additionalProperties": False,
    }


def _chave(texto) -> str:
    """Minúsculas, sem acento e sem espaços/hífens extras: 'Pergunta Técnica' -> 'pergunta_tecnica'."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return "_".join(sem_acento.lower().replace("-", " ").split())


_TIPOS = {_chave(t): t for t in TIPOS} | {
    "pergunta": "pergunta_tecnica", "duvida": "pergunta_tecnica", "duvida_tecnica": "pergunta_tecnica",
    "reclamacao_ou_critica": "reclamacao", "critica": "reclamacao",
}
_SENTIMENTOS = {_chave(s): s for s in SENTIMENTOS} | {
    "positiva": "Positivo", "neutra": "Neutro", "negativa": "Negativo",
    "altamente_positiva": "Altamente Positivo", "altamente_negativa": "Altamente Negativo",
    "muito_positivo": "Altamente Positivo", "muito_negativo": "Altamente Negativo",
}


def validar_classificacao(dados: dict) -> dict:
    """Normaliza a classificação do modelo para o contrato. Valor desconhecido -> ValueError."""
    tipo = _TIPOS.get(_chave(dados.get("tipo", "")))
    sentimento = _SENTIMENTOS.get(_chave(dados.get("sentimento", "")))
    if not tipo:
        raise ValueError(f"tipo inválido: {dados.get('tipo')!r}")
    if not sentimento:
        raise ValueError(f"sentimento inválido: {dados.get('sentimento')!r}")
    try:
        relevancia = round(float(dados.get("relevancia")))
    except (TypeError, ValueError):
        raise ValueError(f"relevancia inválida: {dados.get('relevancia')!r}")
    topico = str(dados.get("topico") or "").strip()
    if not topico:
        raise ValueError("topico vazio")
    return {"tipo": tipo, "sentimento": sentimento, "topico": topico[:60], "relevancia": max(0, min(10, relevancia))}


def exigir_textos(*campos: str):
    """Validador que exige os campos como texto não vazio."""
    def validar(dados: dict) -> dict:
        faltando = [c for c in campos if not isinstance(dados.get(c), str) or not dados[c].strip()]
        if faltando:
            raise ValueError("campos ausentes ou vazios: " + ", ".join(faltando))
        return {c: dados[c].strip() for c in campos}
    return validar


def _mensagem(texto: str) -> str:
    """Delimita o texto do membro para o modelo tratá-lo como dado, não como instrução."""
    return "<mensagem>\n" + texto.replace("</mensagem>", "</ mensagem>") + "\n</mensagem>"


def _registrar_falha(etapa: str, autor: str, erro: Exception):
    FALHAS.append({"etapa": etapa, "autor": autor, "erro": str(erro)})
    log.warning("Claude falhou em %s (%s): %s. Usando o modo simulado para este item.", etapa, autor, erro)


# ---------- Roteamento (regra de negócio, não depende do LLM) ----------
def decidir_rota(tipo: str, sentimento: str, relevancia: int) -> str:
    if sentimento in ("Negativo", "Altamente Negativo") or tipo == "reclamacao":
        return "alerta"
    if tipo in ("depoimento", "projeto") and sentimento in ("Altamente Positivo", "Positivo") and relevancia >= 7:
        return "case_sucesso"
    if tipo == "pergunta_tecnica":
        return "faq"
    return "nenhuma"


# ---------- Classificação ----------
def _classificar_mock(i: Interacao) -> dict:
    t = i.texto.lower()
    if any(p in t for p in NEGATIVOS):
        sentimento, relevancia = "Negativo", 6
    elif any(p in t for p in POSITIVOS):
        sentimento, relevancia = "Altamente Positivo", 9
    else:
        sentimento, relevancia = "Neutro", 5
    tipo = i.tipo if i.tipo != "outro" else ("pergunta_tecnica" if "?" in t else "outro")
    topico = i.canal.strip("#").replace("-", " ").title()
    return {"tipo": tipo, "sentimento": sentimento, "topico": topico, "relevancia": relevancia}


def classificar(i: Interacao) -> Analise:
    if modo_mock():
        r = _classificar_mock(i)
    else:
        try:
            r = chamar_llm_json(prompts.CLASSIFICADOR_SISTEMA, f"Canal: {i.canal}\n{_mensagem(i.texto)}",
                                validar=validar_classificacao, schema=SCHEMA_CLASSIFICACAO,
                                esforco=esforco_classificacao(), max_tokens=4000)
        except ErroLLM as erro:
            _registrar_falha("classificação", i.autor, erro)
            r = _classificar_mock(i)
    rota = decidir_rota(r["tipo"], r["sentimento"], int(r["relevancia"]))
    return Analise(autor=i.autor, canal=i.canal, texto=i.texto, rota=rota, **r)


# ---------- Geração ----------
def _linkedin_mock(a: Analise) -> dict:
    return {
        "titulo": f"Da Comunidade para o Mercado: a conquista de {a.autor}",
        "copy": f"Nada nos dá mais orgulho do que ver nossos talentos crescendo! 🚀\n\n"
                f"{a.autor} compartilhou com a comunidade: \"{a.texto[:180]}\"\n\n"
                f"Parabéns, {a.autor.split()[0]}! 👏\n\n#TalentosTech #ComunidadeONE #CarreiraDev",
    }


def gerar_linkedin(a: Analise) -> PostLinkedin:
    if modo_mock():
        r = _linkedin_mock(a)
    else:
        try:
            r = chamar_llm_json(prompts.LINKEDIN_SISTEMA, f"Autor: {a.autor}\n{_mensagem(a.texto)}",
                                validar=exigir_textos("titulo", "copy"), schema=schema_textos("titulo", "copy"),
                                esforco=esforco_geracao())
        except ErroLLM as erro:
            _registrar_falha("post LinkedIn", a.autor, erro)
            r = _linkedin_mock(a)
    r["titulo"] = higienizar_texto_editorial(r.get("titulo", ""))
    r["copy"] = higienizar_texto_editorial(r.get("copy", ""))
    engajamento = "Alto" if a.relevancia >= 8 else "Médio"
    return PostLinkedin(potencial_engajamento=engajamento, **r)


def gerar_faq(a: Analise) -> SugestaoFaq:
    simulado = {"tema": f"Dica Rápida: {a.topico}", "conteudo": f"[rascunho simulado] Resposta para: {a.texto}"}
    if modo_mock():
        r = simulado
    else:
        try:
            r = chamar_llm_json(prompts.FAQ_SISTEMA, f"Dúvida:\n{_mensagem(a.texto)}",
                                validar=exigir_textos("tema", "conteudo"), schema=schema_textos("tema", "conteudo"),
                                esforco=esforco_geracao())
        except ErroLLM as erro:
            _registrar_falha("FAQ", a.autor, erro)
            r = simulado
    r["tema"] = higienizar_texto_editorial(r.get("tema", ""))
    r["conteudo"] = higienizar_texto_editorial(r.get("conteudo", ""))
    return SugestaoFaq(origem=f"Dúvida levantada por {a.autor} em {a.canal}", **r)


def gerar_newsletter(analises: list[Analise]) -> DestaqueNewsletter:
    destaque = max(analises, key=lambda a: a.relevancia)
    simulado = DestaqueNewsletter(
        secao="Vitória da Semana" if destaque.rota == "case_sucesso" else "Tema da Semana",
        chamada=f"{destaque.autor} em destaque: {destaque.topico}",
        resumo=f"Foram {len(analises)} interações nesta semana. O destaque foi de {destaque.autor} em {destaque.canal}.",
    )
    if modo_mock():
        return simulado
    entrada = json.dumps([a.model_dump() for a in analises], ensure_ascii=False)
    try:
        r = chamar_llm_json(prompts.NEWSLETTER_SISTEMA, _mensagem(entrada),
                            validar=exigir_textos("secao", "chamada", "resumo"),
                            schema=schema_textos("secao", "chamada", "resumo"), esforco=esforco_geracao())
    except ErroLLM as erro:
        _registrar_falha("newsletter", "lote", erro)
        return simulado
    r["chamada"] = higienizar_texto_editorial(r.get("chamada", ""))
    r["resumo"] = higienizar_texto_editorial(r.get("resumo", ""))
    return DestaqueNewsletter(**r)
