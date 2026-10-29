"""Cliente de LLM com retry, validação de resposta e modo simulado.

Sem GEMINI_API_KEY (ou com LLM_MODO=mock), tudo roda com respostas simuladas.
Isso deixa a equipe desenvolver interface e orquestração sem gastar cota da API.

A chave fica SOMENTE no .env local (ignorado pelo git). Nada aqui imprime a chave.
"""
import json
import logging
import os
import time
from typing import Any, Callable

log = logging.getLogger("communitylab.llm")

# Erros que valem nova tentativa: limite de requisições e falhas temporárias do servidor
CODIGOS_TEMPORARIOS = {408, 429, 500, 502, 503, 504}
ESPERA_LIMITE_S = (10, 20, 40)   # 429: o plano gratuito libera a cota por minuto
ESPERA_FALHA_S = (4, 10, 20)  # 503 (servidor sobrecarregado) costuma passar em segundos

# Contadores para o relatório do teste controlado (scripts/teste_gemini.py)
ESTATISTICAS = {"chamadas": 0, "novas_tentativas": 0, "respostas_invalidas": 0}


class ErroLLM(RuntimeError):
    """Falha definitiva ao obter uma resposta válida do modelo."""


# Gemini 3.5 Flash Lite: no plano gratuito, 15 chamadas/min e 500/dia (o 3.6 Flash permite 5/min e 20/dia).
# No teste controlado de 26/10/2026 acertou 7 de 7 rotas, em 11 s.
MODELO_PADRAO = "gemini-3.5-flash-lite"
RPM_PADRAO = 15


def modelo() -> str:
    return os.getenv("GEMINI_MODELO") or MODELO_PADRAO


def chamadas_por_minuto() -> float:
    """Limite de chamadas por minuto do plano (GEMINI_RPM no .env). 0 desliga o ritmo."""
    try:
        return max(0.0, float(os.getenv("GEMINI_RPM") or RPM_PADRAO))
    except ValueError:
        return float(RPM_PADRAO)


_ultima_chamada = None


def _aguardar_vez():
    """Espaça as chamadas para nunca passar do limite por minuto (evita o HTTP 429 em vez de reagir a ele)."""
    global _ultima_chamada
    rpm = chamadas_por_minuto()
    if rpm and _ultima_chamada is not None:
        falta = 60.0 / rpm - (time.monotonic() - _ultima_chamada)
        if falta > 0:
            time.sleep(falta)
    _ultima_chamada = time.monotonic()


def modo_mock() -> bool:
    return os.getenv("LLM_MODO", "").lower() == "mock" or not os.getenv("GEMINI_API_KEY")


_cliente = None
_chave_do_cliente = None


def _obter_cliente():
    """Reaproveita o cliente entre chamadas; recria se a chave mudar."""
    global _cliente, _chave_do_cliente
    chave = os.environ["GEMINI_API_KEY"]
    if _cliente is None or chave != _chave_do_cliente:
        from google import genai
        _cliente, _chave_do_cliente = genai.Client(api_key=chave), chave
    return _cliente


def _codigo_http(erro: Exception) -> int | None:
    return getattr(erro, "code", None) if isinstance(getattr(erro, "code", None), int) else None


def chamar_llm(sistema: str, usuario: str, json_saida: bool = False, tentativas: int = 3) -> str:
    """Chama o Gemini. Tenta de novo só em erros temporários; erro de chave ou de pedido falha na hora."""
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=sistema,
        temperature=0.4 if json_saida else 0.8,
        response_mime_type="application/json" if json_saida else "text/plain",
    )
    for tentativa in range(tentativas):
        _aguardar_vez()
        ESTATISTICAS["chamadas"] += 1
        try:
            resposta = _obter_cliente().models.generate_content(model=modelo(), contents=usuario, config=config)
            if not resposta.text:
                raise ErroLLM("O modelo devolveu uma resposta vazia (possível bloqueio de segurança).")
            return resposta.text
        except ErroLLM:
            raise
        except Exception as erro:
            codigo = _codigo_http(erro)
            temporario = codigo is None or codigo in CODIGOS_TEMPORARIOS  # sem código = rede/timeout
            if not temporario:
                raise ErroLLM(f"Gemini recusou o pedido (HTTP {codigo}). Confira a chave e o nome do modelo "
                              f"({modelo()}).") from erro
            if tentativa == tentativas - 1:
                raise ErroLLM(f"Gemini indisponível após {tentativas} tentativas (último erro: HTTP {codigo}).") from erro
            espera = (ESPERA_LIMITE_S if codigo == 429 else ESPERA_FALHA_S)[tentativa]
            log.warning("Gemini: erro temporário (HTTP %s). Nova tentativa em %s s.", codigo, espera)
            ESTATISTICAS["novas_tentativas"] += 1
            time.sleep(espera)
    raise ErroLLM("Nenhuma tentativa realizada.")


def _extrair_json(texto: str) -> Any:
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(texto)


def chamar_llm_json(sistema: str, usuario: str, validar: Callable[[Any], dict] | None = None,
                    tentativas_formato: int = 2) -> dict:
    """Pede JSON ao modelo e valida. Resposta fora do formato gera um novo pedido; persistindo, ErroLLM.

    `validar` recebe o JSON e devolve o dicionário normalizado, ou levanta ValueError.
    """
    ultimo = None
    for _ in range(tentativas_formato):
        texto = chamar_llm(sistema, usuario, json_saida=True)
        try:
            dados = _extrair_json(texto)
            if not isinstance(dados, dict):
                raise ValueError("a resposta não é um objeto JSON")
            return validar(dados) if validar else dados
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as erro:
            ultimo = erro
            ESTATISTICAS["respostas_invalidas"] += 1
            log.warning("Gemini: resposta fora do formato (%s). Pedindo de novo.", erro)
    raise ErroLLM(f"Resposta fora do formato após {tentativas_formato} tentativas: {ultimo}")
