"""Análise e geração de ativos. Cada função tem versão real (LLM) e simulada (mock).

A versão mock usa regras simples por palavra-chave. Ela não precisa ser boa,
só precisa devolver o formato certo para o resto do sistema funcionar.
"""
import json

from . import prompts
from .llm import chamar_llm_json, modo_mock
from .schemas import Analise, DestaqueNewsletter, Interacao, PostLinkedin, SugestaoFaq

POSITIVOS = ("passei", "contratad", "consegui", "aprovad", "grat", "obrigad", "incrível", "adorei", "vaga")
NEGATIVOS = ("difícil", "dificil", "frustrad", "não consigo", "nao consigo", "não consegui", "nao consegui", "não fui aprovado", "nao fui aprovado", "não passei", "nao passei", "sem conseguir", "desistir", "péssim", "ruim", "travad")


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
    engajamento = "Alto" if a.relevancia >= 8 else "Médio"
    return PostLinkedin(potencial_engajamento=engajamento, **r)


def gerar_faq(a: Analise) -> SugestaoFaq:
    if modo_mock():
        r = {"tema": f"Dica Rápida: {a.topico}", "conteudo": f"[rascunho simulado] Resposta para: {a.texto}"}
    else:
        r = chamar_llm_json(prompts.FAQ_SISTEMA, f"Dúvida: \"{a.texto}\"")
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
    return DestaqueNewsletter(**chamar_llm_json(prompts.NEWSLETTER_SISTEMA, entrada))
