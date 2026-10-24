"""Cliente de LLM com retry e modo simulado.

Sem GEMINI_API_KEY (ou com LLM_MODO=mock), tudo roda com respostas simuladas.
Isso deixa a equipe desenvolver interface e orquestração sem gastar cota da API.
"""
import json
import os
import time

MODELO = os.getenv("GEMINI_MODELO", "gemini-2.5-flash")


def modo_mock() -> bool:
    return os.getenv("LLM_MODO", "").lower() == "mock" or not os.getenv("GEMINI_API_KEY")


def chamar_llm(sistema: str, usuario: str, json_saida: bool = False, tentativas: int = 3) -> str:
    """Chama o Gemini com backoff exponencial. Levanta a última exceção se todas falharem."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(
        system_instruction=sistema,
        temperature=0.4 if json_saida else 0.8,
        response_mime_type="application/json" if json_saida else "text/plain",
    )
    erro = None
    for tentativa in range(tentativas):
        try:
            resposta = cliente.models.generate_content(model=MODELO, contents=usuario, config=config)
            return resposta.text
        except Exception as e:  # rate limit, timeout, 5xx
            erro = e
            time.sleep(2 ** tentativa)
    raise erro


def chamar_llm_json(sistema: str, usuario: str) -> dict:
    texto = chamar_llm(sistema, usuario, json_saida=True)
    texto = texto.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(texto)
