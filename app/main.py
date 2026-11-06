"""API do CommunityLab. Rode com: uvicorn app.main:app --reload"""
import json
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from communitylab.adapter import carregar_lote_bytes  # noqa: E402
from .grafo import processar  # noqa: E402
from .llm import modo_mock  # noqa: E402
from .schemas import LoteEntrada, RespostaProcessamento  # noqa: E402

app = FastAPI(title="CommunityLab", version="0.1.0")


@app.get("/saude")
def saude():
    return {"status": "ok", "modo_llm": "mock" if modo_mock() else "gemini"}


@app.post("/processar", response_model=RespostaProcessamento)
async def processar_lote(request: Request):
    """Processa um lote de interações enviado como JSON (LoteEntrada) ou upload multipart (campo 'arquivo')."""
    content_type = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("arquivo") or form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(422, "Arquivo ausente. Envie o campo 'arquivo' via multipart/form-data.")

        conteudo = await upload.read()
        nome_arquivo = getattr(upload, "filename", None) or "lote.csv"
        origem = form.get("origem_comunidade")
        periodo = form.get("periodo_referencia")

        try:
            lote = carregar_lote_bytes(
                conteudo=conteudo,
                nome_arquivo=str(nome_arquivo),
                origem_comunidade=str(origem) if isinstance(origem, str) and origem.strip() else None,
                periodo_referencia=str(periodo) if isinstance(periodo, str) and periodo.strip() else None,
            )
        except (ValueError, ValidationError) as exc:
            raise HTTPException(422, str(exc)) from exc
    else:
        try:
            dados = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(422, "O corpo da requisição não é um JSON válido.") from exc

        try:
            lote = LoteEntrada.model_validate(dados)
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json())) from exc

    if not lote.interacoes:
        raise HTTPException(400, "O lote não tem interações.")

    return processar(lote)
