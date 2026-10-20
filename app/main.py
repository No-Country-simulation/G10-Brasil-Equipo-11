"""API do CommunityLab. Rode com: uvicorn app.main:app --reload"""
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402

from .grafo import processar  # noqa: E402
from .llm import modo_mock  # noqa: E402
from .schemas import LoteEntrada, RespostaProcessamento  # noqa: E402

app = FastAPI(title="CommunityLab", version="0.1.0")


@app.get("/saude")
def saude():
    return {"status": "ok", "modo_llm": "mock" if modo_mock() else "gemini"}


@app.post("/processar", response_model=RespostaProcessamento)
def processar_lote(lote: LoteEntrada):
    if not lote.interacoes:
        raise HTTPException(400, "O lote não tem interações.")
    return processar(lote)
