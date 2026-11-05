"""Análise e geração de ativos. Cada função tem versão real (LLM) e simulada (mock).

A versão mock usa regras simples por palavra-chave. Ela não precisa ser boa,
só precisa devolver o formato certo para o resto do sistema funcionar.
Inclui guardrails Anti-Slop (Humanizer) e verificação de ancoragem factual (Harness²).
"""
import json
import re

from . import prompts
from .llm import chamar_llm_json, modo_mock
from .schemas import Analise, DestaqueNewsletter, Interacao, PostLinkedin, SugestaoFaq

POSITIVOS = ("passei", "contratad", "consegui", "aprovad", "grat", "obrigad", "incrível", "adorei", "vaga")
NEGATIVOS = ("difícil", "dificil", "frustrad", "não consigo", "nao consigo", "desistir", "péssim", "ruim", "travad")

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
        r = chamar_llm_json(prompts.CLASSIFICADOR_SISTEMA, f'Canal: {i.canal}\nMensagem: "{i.texto}"')
    rota = decidir_rota(r["tipo"], r["sentimento"], int(r["relevancia"]))
    return Analise(autor=i.autor, canal=i.canal, texto=i.texto, rota=rota, **r)


# ---------- Geração ----------
def gerar_linkedin(a: Analise) -> PostLinkedin:
    if modo_mock():
        r = {
            "titulo": f"Da Comunidade para o Mercado: a conquista de {a.autor}",
            "copy": f"Nada nos dá mais orgulho do que ver nossos talentos crescendo! 🚀\n\n"
                    f"{a.autor} compartilhou com a comunidade: \"{a.texto[:180]}\"\n\n"
                    f"Parabéns, {a.autor.split()[0]}! 👏\n\n#TalentosTech #ComunidadeONE #CarreiraDev",
        }
    else:
        r = chamar_llm_json(prompts.LINKEDIN_SISTEMA, f"Autor: {a.autor}\nMensagem: \"{a.texto}\"")
    r["titulo"] = higienizar_texto_editorial(r.get("titulo", ""))
    r["copy"] = higienizar_texto_editorial(r.get("copy", ""))
    engajamento = "Alto" if a.relevancia >= 8 else "Médio"
    return PostLinkedin(potencial_engajamento=engajamento, **r)


def gerar_faq(a: Analise) -> SugestaoFaq:
    if modo_mock():
        r = {"tema": f"Dica Rápida: {a.topico}", "conteudo": f"[rascunho simulado] Resposta para: {a.texto}"}
    else:
        r = chamar_llm_json(prompts.FAQ_SISTEMA, f"Dúvida: \"{a.texto}\"")
    r["tema"] = higienizar_texto_editorial(r.get("tema", ""))
    r["conteudo"] = higienizar_texto_editorial(r.get("conteudo", ""))
    return SugestaoFaq(origem=f"Dúvida levantada por {a.autor} em {a.canal}", **r)


def gerar_newsletter(analises: list[Analise]) -> DestaqueNewsletter:
    destaque = max(analises, key=lambda a: a.relevancia)
    if modo_mock():
        return DestaqueNewsletter(
            secao="Vitória da Semana" if destaque.rota == "case_sucesso" else "Tema da Semana",
            chamada=f"{destaque.autor} em destaque: {destaque.topico}",
            resumo=f"Foram {len(analises)} interações nesta semana. O destaque foi de {destaque.autor} em {destaque.canal}.",
        )
    entrada = json.dumps([a.model_dump() for a in analises], ensure_ascii=False)
    r = chamar_llm_json(prompts.NEWSLETTER_SISTEMA, entrada)
    r["chamada"] = higienizar_texto_editorial(r.get("chamada", ""))
    r["resumo"] = higienizar_texto_editorial(r.get("resumo", ""))
    return DestaqueNewsletter(**r)
