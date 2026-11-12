"""API do Sender AI (CommunityLab). Rode com: uvicorn app.main:app --reload

Serve o painel web (pasta web/) e a API REST com persistência no Oracle.

Desenvolvimento: COMMUNITYLAB_DB_MODE=disabled e OCI_STORAGE_MODE=local.
Demonstração final: Oracle Database + OCI Object Storage + API key.
"""
from __future__ import annotations
from datetime import date
import hmac
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from communitylab.adapter import carregar_lote_bytes

from . import database, repository, storage
from .middleware import RequestContextAndBodyLimitMiddleware
from .grafo import processar, processar_com_registro
from .llm import modo_mock
from .rotas_web import exigir_admin, router as rotas_web_router
from .schemas import LoteEntrada, RespostaProcessamento

logger = logging.getLogger("communitylab.api")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper()
)


class CuradoriaAtualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["PENDENTE", "APROVADO", "DESCARTADO"]
    versao_esperada: int = Field(ge=1)
    patch: dict[str, str] = Field(default_factory=dict)
    consentimento: bool | None = None
    referencia_consentimento: str | None = Field(
        default=None,
        max_length=500,
    )
    justificativa: str | None = Field(
        default=None,
        max_length=2000,
    )


class AlertaAtualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["PENDENTE", "ENCAMINHADO", "RESOLVIDO"]
    versao_esperada: int = Field(ge=1)
    acao: str | None = Field(
        default=None,
        max_length=300,
    )
    justificativa: str | None = Field(
        default=None,
        max_length=2000,
    )


def _production_config_check() -> None:
    errors = []

    if (
        os.getenv("COMMUNITYLAB_DB_MODE", "disabled").lower()
        != "oracle"
        or not database.oracle_configured()
    ):
        errors.append(
            "Oracle Database deve estar configurado "
            "(COMMUNITYLAB_DB_MODE=oracle e credenciais/DSN)."
        )

    if os.getenv("OCI_STORAGE_MODE", "local").lower() != "required":
        errors.append(
            "OCI_STORAGE_MODE deve ser required em produção."
        )

    api_key = os.getenv("COMMUNITYLAB_API_KEY", "")
    if len(api_key) < 32 or not api_key.isascii():
        errors.append(
            "COMMUNITYLAB_API_KEY deve ter ao menos "
            "32 caracteres ASCII aleatórios em produção."
        )

    if (
        not os.getenv("OCI_NAMESPACE")
        or not os.getenv("OCI_BUCKET")
    ):
        errors.append(
            "OCI_NAMESPACE e OCI_BUCKET são obrigatórios."
        )

    auth_mode = os.getenv(
        "OCI_AUTH_MODE", "config_file"
    ).lower()

    if (
        auth_mode == "config_file"
        and not storage.oci_configurado()
    ):
        errors.append(
            "Credenciais OCI não configuradas para "
            "OCI_AUTH_MODE=config_file."
        )
    elif auth_mode not in {
        "config_file",
        "resource_principal",
    }:
        errors.append(
            "OCI_AUTH_MODE deve ser config_file "
            "ou resource_principal."
        )

    if modo_mock() or not os.getenv("GEMINI_API_KEY"):
        errors.append(
            "O modo real do Gemini deve estar ativo e "
            "GEMINI_API_KEY configurada em produção."
        )

    if errors:
        raise RuntimeError(
            "Configuração de produção incompleta: "
            + " ".join(errors)
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        env = os.getenv(
            "APP_ENV", "development"
        ).strip().lower()

        if env == "production":
            _production_config_check()

        if database.database_mode() == "oracle":
            database.initialize_pool()
            database.validate_schema()
            logger.info(
                "Oracle Database conectado e schema validado."
            )

        yield
    finally:
        database.close_pool()


RAIZ = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="Sender AI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    RequestContextAndBodyLimitMiddleware,
    max_bytes=int(
        os.getenv(
            "COMMUNITYLAB_MAX_REQUEST_BYTES",
            str(10 * 1024 * 1024),
        )
    ),
)


@app.middleware("http")
async def desativar_cache_estatico(request: Request, call_next):
    resposta = await call_next(request)
    if request.url.path == "/" or request.url.path.endswith((".html", ".css", ".js")):
        resposta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resposta


def require_api_access(
    request: Request,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
    authorization: str | None = Header(
        default=None,
        alias="Authorization",
    ),
    x_actor: str | None = Header(
        default=None,
        alias="X-Actor",
    ),
) -> str:
    env = os.getenv(
        "APP_ENV", "development"
    ).strip().lower()

    # Em produção, autenticação não pode ser desabilitada.
    required = (
        env == "production"
        or os.getenv(
            "COMMUNITYLAB_API_AUTH_REQUIRED", "false"
        ).lower() in {"1", "true", "yes"}
    )

    expected = os.getenv("COMMUNITYLAB_API_KEY", "")
    supplied = x_api_key

    if (
        not supplied
        and authorization
        and authorization.lower().startswith("bearer ")
    ):
        supplied = authorization[7:].strip()

    if required:
        if (
            not expected
            or not supplied
            or not expected.isascii()
            or not supplied.isascii()
            or not hmac.compare_digest(supplied, expected)
        ):
            raise HTTPException(
                status_code=401,
                detail="Credencial da API ausente ou inválida.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Sem chave de API válida, vale a sessão do painel web (login de admin),
    # quando ADMIN_USUARIO/ADMIN_SENHA estão configurados.
    chave_valida = bool(
        expected
        and supplied
        and expected.isascii()
        and supplied.isascii()
        and hmac.compare_digest(supplied, expected)
    )

    if not chave_valida:
        exigir_admin(request)

    actor = (x_actor or "").strip()

    if env == "production" and not actor:
        raise HTTPException(
            status_code=400,
            detail="Informe X-Actor para registrar a autoria.",
        )

    if len(actor) > 255:
        raise HTTPException(
            status_code=400,
            detail="X-Actor excede 255 caracteres.",
        )

    if any(ord(char) < 32 or ord(char) == 127 for char in actor):
        raise HTTPException(
            status_code=400,
            detail="X-Actor contém caracteres de controle inválidos.",
        )

    return actor or "usuario-local"


def _validar_chave_idempotencia(
    value: str | None,
) -> None:
    if value is None:
        return

    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value):
        raise HTTPException(
            status_code=400,
            detail=(
                "Idempotency-Key deve ter de 8 a 128 caracteres "
                "ASCII: letras, números, ponto, hífen, "
                "dois-pontos ou sublinhado."
            ),
        )


def _require_oracle() -> None:
    if database.database_mode() != "oracle":
        raise HTTPException(
            status_code=503,
            detail=(
                "Persistência Oracle indisponível. "
                "Configure COMMUNITYLAB_DB_MODE=oracle."
            ),
        )


def _safe_upload_error(
    exc: Exception,
    object_name: str,
    bucket: str,
) -> dict:
    # Evita expor detalhes internos de SDK, sistema operacional ou rede.
    return {
        "bucket": bucket,
        "caminho_objeto": object_name,
        "status": "erro",
        "sha256": None,
        "etag": None,
        "detalhe": (
            f"Falha no armazenamento ({type(exc).__name__})."
        ),
    }


def _bucket_destino_atual() -> str:
    mode = os.getenv(
        "OCI_STORAGE_MODE", "local"
    ).strip().lower()

    return (
        "local"
        if mode == "local"
        else (os.getenv("OCI_BUCKET") or storage.bucket_name())
    )


def _upload_process_package(process_id: str) -> dict:
    item = repository.obter_processamento(process_id)

    if not item or not item.get("resultado"):
        raise repository.RecordNotFound(
            "Lote não encontrado ou sem resultado persistido."
        )

    response = item["resultado"]

    object_name = (
        item.get("oci_object_name")
        or storage.caminho_objeto(
            item["periodo_referencia"],
            process_id,
        )
    )

    saved_bucket = item.get("oci_bucket")
    target_bucket = _bucket_destino_atual()

    if saved_bucket and saved_bucket != target_bucket:
        upload = _safe_upload_error(
            storage.StorageConfigurationError(
                "Destino persistido difere da configuração atual."
            ),
            object_name,
            saved_bucket,
        )
        upload["detalhe"] = (
            "O bucket configurado difere do destino persistido; "
            "nenhum upload foi realizado."
        )
        repository.atualizar_status_upload(
            process_id, upload
        )
        return upload

    package = dict(response)
    package.pop("armazenamento_oci", None)

    try:
        upload = storage.salvar_pacote(
            package,
            item["periodo_referencia"],
            processamento_id=process_id,
            object_name=object_name,
        )
    except Exception as exc:
        logger.warning(
            "Falha no upload OCI do processamento %s (%s)",
            process_id,
            type(exc).__name__,
        )
        upload = _safe_upload_error(
            exc,
            object_name,
            target_bucket,
        )

    repository.atualizar_status_upload(
        process_id, upload
    )
    return upload


@app.get("/saude")
def saude():
    """Liveness: verifica se o processo HTTP responde."""
    return {
        "status": "ok",
        "modo_llm": "mock" if modo_mock() else "gemini",
    }


@app.get("/", response_class=HTMLResponse)
def servir_index():
    caminho = RAIZ / "web" / "index.html"
    if caminho.exists():
        resposta = HTMLResponse(content=caminho.read_text(encoding="utf-8"))
        resposta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resposta.headers["Pragma"] = "no-cache"
        resposta.headers["Expires"] = "0"
        return resposta
    return HTMLResponse("<!DOCTYPE html><html><body><h1>Sender AI</h1></body></html>")


@app.get("/prontidao")
def prontidao():
    """Readiness: verifica Oracle, schema e acesso ao bucket."""
    env = os.getenv(
        "APP_ENV", "development"
    ).strip().lower()

    details = {
        "api": True,
        "database": "desativado",
        "object_storage": "não verificado",
    }
    failures = []

    if database.database_mode() == "oracle":
        try:
            database.ping()
            database.validate_schema()
            details["database"] = "ok"
        except Exception as exc:
            details["database"] = "indisponivel"
            failures.append(
                "Oracle Database: " + type(exc).__name__
            )
    elif env == "production":
        failures.append("Oracle Database desativado")

    if os.getenv(
        "OCI_STORAGE_MODE", "local"
    ).lower() in {"required", "oci"}:
        check = storage.verificar_bucket()
        details["object_storage"] = (
            "ok" if check["ok"] else "indisponivel"
        )

        if not check["ok"]:
            failures.append(
                "OCI Object Storage: "
                + check.get("motivo", "indisponivel")
            )
    else:
        details["object_storage"] = "modo_local"

    details["modo_llm"] = (
        "mock" if modo_mock() else "gemini"
    )
    details["pronto"] = not failures

    if failures and env == "production":
        return JSONResponse(
            status_code=503,
            content={
                "status": "indisponivel",
                "detalhes": details,
                "falhas": failures,
            },
        )

    return {
        "status": "ok" if not failures else "degradado",
        "detalhes": details,
        "falhas": failures,
    }


@app.post(
    "/processar",
    response_model=RespostaProcessamento,
)
async def processar_lote(
    request: Request,
    reprocessar: bool = Query(
        False,
        description=(
            "Processa de novo um conteúdo já processado, "
            "criando outro lote (só vale sem Idempotency-Key)."
        ),
    ),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
    _actor: str = Depends(require_api_access),
):
    """Processa um lote enviado como JSON (LoteEntrada) ou upload multipart (campo 'arquivo')."""
    lote = await _ler_lote(request)

    if not lote.interacoes:
        raise HTTPException(
            status_code=400,
            detail="O lote não tem interações.",
        )

    _validar_chave_idempotencia(idempotency_key)

    # O pipeline (IA + banco) é bloqueante: roda fora do laço de eventos.
    result = await run_in_threadpool(
        _processar_lote_validado,
        lote,
        request,
        idempotency_key,
        reprocessar,
    )

    # O painel web identifica o lote por lote_id; com Oracle é o processamento_id.
    if isinstance(result, dict) and result.get("processamento_id"):
        result["lote_id"] = result["processamento_id"]

    return result


async def _ler_lote(request: Request) -> LoteEntrada:
    content_type = (
        request.headers.get("content-type") or ""
    ).lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("arquivo") or form.get("file")

        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(
                422,
                "Arquivo ausente. Envie o campo 'arquivo' via multipart/form-data.",
            )

        conteudo = await upload.read()
        nome_arquivo = getattr(upload, "filename", None) or "lote.csv"
        origem = form.get("origem_comunidade")
        periodo = form.get("periodo_referencia")

        try:
            return carregar_lote_bytes(
                conteudo=conteudo,
                nome_arquivo=str(nome_arquivo),
                origem_comunidade=(
                    str(origem)
                    if isinstance(origem, str) and origem.strip()
                    else None
                ),
                periodo_referencia=(
                    str(periodo)
                    if isinstance(periodo, str) and periodo.strip()
                    else None
                ),
            )
        except (ValueError, ValidationError) as exc:
            raise HTTPException(422, str(exc)) from exc

    try:
        dados = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            422,
            "O corpo da requisição não é um JSON válido.",
        ) from exc

    try:
        return LoteEntrada.model_validate(dados)
    except ValidationError as exc:
        raise HTTPException(
            422,
            detail=json.loads(exc.json(include_url=False, include_context=False)),
        ) from exc


def _chave_idempotencia_automatica(input_dict: dict) -> str:
    """Chave estável para quem não envia Idempotency-Key (o painel web).

    Mesmo conteúdo no mesmo modo de IA reabre o processamento já gravado,
    em vez de duplicar o lote no histórico.
    """
    modo = "mock" if modo_mock() else "gemini"
    digest = repository.fingerprint_request(
        {"modo": modo, "lote": input_dict}
    )
    return f"auto:{modo}:{digest[:48]}"


def _processar_lote_validado(
    lote: LoteEntrada,
    request: Request,
    idempotency_key: str | None,
    reprocessar: bool = False,
):
    if database.database_mode() != "oracle":
        if os.getenv(
            "APP_ENV", "development"
        ).lower() == "production":
            raise HTTPException(
                status_code=503,
                detail="Persistência Oracle obrigatória em produção.",
            )

        # Sem Oracle: só processa (e grava no histórico antigo se
        # DATABASE_URL existir, para o painel Streamlit).
        result, registro = processar_com_registro(lote)
        result["lote_id"] = registro.get("lote_id")
        result["persistencia"] = "desativada"
        return result

    # O Oracle trata texto vazio como NULL: recusa antes de abrir o processamento.
    for posicao, interacao in enumerate(lote.interacoes, 1):
        if not (
            interacao.autor.strip()
            and interacao.canal.strip()
            and interacao.texto.strip()
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Interação {posicao}: autor, canal e texto "
                    "devem ser preenchidos."
                ),
            )

    if not (
        lote.origem_comunidade.strip()
        and lote.periodo_referencia.strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="Informe a comunidade de origem e o período de referência.",
        )

    input_dict = lote.model_dump(
        mode="json",
        exclude_none=True,
    )

    if not idempotency_key:
        idempotency_key = _chave_idempotencia_automatica(input_dict)

        if reprocessar:
            # Pedido explícito de novo processamento do mesmo conteúdo.
            idempotency_key += f":{uuid.uuid4().hex[:12]}"

    try:
        started = repository.iniciar_processamento(
            input_dict,
            idempotency_key,
        )

        if started.get("existing"):
            if started.get("oci_status") in {
                "PENDENTE", "ERRO"
            }:
                _upload_process_package(started["id"])
                current = repository.obter_processamento(
                    started["id"]
                )
                return (
                    current["resultado"]
                    if current
                    else started["response"]
                )

            return started["response"]

        process_id = started["id"]
        object_name = storage.caminho_objeto(
            lote.periodo_referencia,
            process_id,
        )

        try:
            result = processar(
                lote,
                persistir_pacote=False,
                processamento_id=process_id,
                interaction_ids=started["interaction_ids"],
            )

            result = repository.finalizar_processamento(
                process_id,
                result,
                started["interaction_ids"],
                started["attempt_token"],
                object_name,
            )

        except repository.AttemptSuperseded as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            logger.exception(
                "Falha no pipeline do processamento %s; request_id=%s",
                process_id,
                request.state.request_id,
            )

            try:
                repository.marcar_erro(
                    process_id,
                    started["attempt_token"],
                    type(exc).__name__,
                    "Falha interna no pipeline; consulte os logs "
                    "correlacionados pelo request_id.",
                )
            except Exception:
                logger.exception(
                    "Falha adicional ao registrar erro do processamento %s",
                    process_id,
                )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Falha ao processar o lote. Referência: "
                    f"{request.state.request_id}"
                ),
            ) from exc

        upload = _upload_process_package(process_id)
        current = repository.obter_processamento(process_id)

        return (
            current["resultado"]
            if current
            else {**result, "armazenamento_oci": upload}
        )

    except repository.IdempotencyConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except repository.ProcessingInProgress as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except repository.RecordNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Falha de persistência em /processar; request_id=%s",
            request.state.request_id,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Persistência indisponível. Referência: "
                f"{request.state.request_id}"
            ),
        ) from exc


@app.get("/processamentos")
def listar_processamentos(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        return {
            "items": repository.listar_processamentos(
                limit, offset
            ),
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        logger.exception("Falha ao listar processamentos")
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar os processamentos.",
        ) from exc


# ---------------------------------------------------------------------------
# Insights: consultas históricas
# ---------------------------------------------------------------------------

@app.get("/insights/opcoes")
def obter_opcoes_insights(
    modo: Literal["mock", "gemini"] = Query("mock"),
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        return repository.opcoes_filtros_insights(modo)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Falha ao consultar opções de Insights")

        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar os filtros de Insights.",
        ) from exc


@app.get("/insights/interacoes")
def obter_interacoes_insights(
    inicio: date,
    fim: date,
    modo: Literal["mock", "gemini"] = Query("mock"),
    comunidades: list[str] | None = Query(None),
    canais: list[str] | None = Query(None),
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        items = repository.consultar_interacoes_insights(
            inicio=inicio,
            fim=fim,
            modo=modo,
            comunidades=comunidades,
            canais=canais,
        )

        return {
            "items": items,
            "total": len(items),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Falha ao consultar interações de Insights")

        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar as interações de Insights.",
        ) from exc


@app.get("/insights/ativos")
def obter_ativos_insights(
    inicio: date,
    fim: date,
    modo: Literal["mock", "gemini"] = Query("mock"),
    comunidades: list[str] | None = Query(None),
    canais: list[str] | None = Query(None),
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        items = repository.consultar_ativos_insights(
            inicio=inicio,
            fim=fim,
            modo=modo,
            comunidades=comunidades,
            canais=canais,
        )

        return {
            "items": items,
            "total": len(items),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Falha ao consultar ativos de Insights")

        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar os ativos de Insights.",
        ) from exc

@app.get("/processamentos/{process_id}")
def obter_processamento(
    process_id: str,
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        item = repository.obter_processamento(process_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Processamento não encontrado.",
            )

        return item

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Falha ao consultar processamento %s",
            process_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar o processamento.",
        ) from exc


@app.patch("/ativos/{asset_id}/curadoria")
def atualizar_curadoria(
    asset_id: str,
    body: CuradoriaAtualizar,
    actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        return repository.atualizar_curadoria(
            asset_id,
            body.status,
            body.patch,
            actor,
            body.versao_esperada,
            body.consentimento,
            body.justificativa,
            body.referencia_consentimento,
        )

    except repository.RecordNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except repository.VersionConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except repository.InvalidCuration as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Falha ao salvar curadoria do ativo %s",
            asset_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível salvar a curadoria.",
        ) from exc


@app.get("/ativos/{asset_id}/historico")
def consultar_historico(
    asset_id: str,
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        history = repository.historico_ativo(asset_id)

        if history is None:
            raise HTTPException(
                status_code=404,
                detail="Ativo não encontrado.",
            )

        return {
            "ativo_id": asset_id,
            "historico": history,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Falha ao consultar histórico do ativo %s",
            asset_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar o histórico.",
        ) from exc


@app.patch("/alertas/{alert_id}")
def triagem_alerta(
    alert_id: str,
    body: AlertaAtualizar,
    actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        return repository.atualizar_alerta(
            alert_id,
            body.status,
            actor,
            body.versao_esperada,
            body.acao,
            body.justificativa,
        )

    except repository.RecordNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except repository.VersionConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except repository.InvalidCuration as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Falha na triagem do alerta %s",
            alert_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível salvar a triagem do alerta.",
        ) from exc


@app.get("/alertas/{alert_id}/historico")
def consultar_historico_alerta(
    alert_id: str,
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        history = repository.historico_alerta(alert_id)

        if history is None:
            raise HTTPException(
                status_code=404,
                detail="Alerta não encontrado.",
            )

        return {
            "alerta_id": alert_id,
            "historico": history,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Falha ao consultar histórico do alerta %s",
            alert_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar o histórico do alerta.",
        ) from exc


@app.post("/processamentos/{process_id}/repetir-upload")
def repetir_upload_processamento(
    process_id: str,
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        item = repository.obter_processamento(process_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Processamento não encontrado.",
            )

        if item["status"] != "SUCESSO":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Só é possível repetir o upload de um "
                    "processamento concluído."
                ),
            )

        upload = _upload_process_package(process_id)

        return {
            "processamento_id": process_id,
            "armazenamento_oci": upload,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Falha ao repetir upload do processamento %s",
            process_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível repetir o upload.",
        ) from exc


def _upload_export(export_id: str) -> dict:
    item = repository.obter_exportacao(export_id)

    if not item:
        raise repository.RecordNotFound(
            "Exportação não encontrada."
        )

    if item.get("status") == "ENVIADO":
        return {
            "bucket": item.get("bucket") or os.getenv("OCI_BUCKET", ""),
            "caminho_objeto": item.get("caminho_objeto") or "",
            "status": "salvo_com_sucesso",
            "etag": item.get("etag"),
            "sha256": None,
        }

    if item.get("status") == "LOCAL":
        return {
            "bucket": "local",
            "caminho_objeto": item.get("caminho_objeto") or "",
            "status": "salvo_localmente",
            "etag": None,
            "sha256": None,
        }

    package = item["pacote"]
    period = package.get(
        "periodo_referencia",
        "periodo-nao-informado",
    )

    candidate_name = (
        item.get("caminho_objeto")
        or storage.caminho_objeto(
            period,
            export_id,
            "aprovados.json",
        )
    )

    bucket_for_mode = (
        storage.bucket_name()
        if os.getenv(
            "OCI_STORAGE_MODE", "local"
        ).strip().lower() in {"oci", "required"}
        else "local"
    )

    object_name = repository.definir_objeto_exportacao(
        export_id,
        candidate_name,
        bucket_for_mode,
    )

    try:
        upload = storage.salvar_pacote(
            package,
            period,
            processamento_id=export_id,
            nome_arquivo="aprovados.json",
            object_name=object_name,
        )
    except Exception as exc:
        logger.warning(
            "Falha no upload da exportação %s (%s)",
            export_id,
            type(exc).__name__,
        )

        upload = _safe_upload_error(
            exc,
            object_name,
            (
                storage.bucket_name()
                if bucket_for_mode != "local"
                else "local"
            ),
        )

    repository.atualizar_exportacao_upload(
        export_id, upload
    )
    return upload


@app.post("/processamentos/{process_id}/exportar")
def exportar_aprovados(
    process_id: str,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
    actor: str = Depends(require_api_access),
):
    _require_oracle()
    _validar_chave_idempotencia(idempotency_key)

    persistido = (
        os.getenv("APP_ENV", "development").lower()
        == "production"
        or database.database_mode() == "oracle"
    )

    if persistido and not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "Idempotency-Key é obrigatório "
                "para exportação persistida."
            ),
        )

    try:
        export = repository.criar_exportacao(
            process_id,
            actor,
            idempotency_key,
        )

        upload = _upload_export(export["id"])

        return {
            "exportacao_id": export["id"],
            "processamento_id": process_id,
            "pacote": export["pacote"],
            "armazenamento_oci": upload,
        }

    except repository.IdempotencyConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except repository.RecordNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except repository.InvalidCuration as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Falha ao criar exportação do processamento %s",
            process_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível gerar a exportação.",
        ) from exc


@app.post("/exportacoes/{export_id}/repetir-upload")
def repetir_upload_exportacao(
    export_id: str,
    _actor: str = Depends(require_api_access),
):
    _require_oracle()

    try:
        item = repository.obter_exportacao(export_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Exportação não encontrada.",
            )

        upload = _upload_export(export_id)

        return {
            "exportacao_id": export_id,
            "armazenamento_oci": upload,
        }

    except repository.InvalidCuration as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Falha ao repetir upload da exportação %s",
            export_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível repetir o upload.",
        ) from exc


# Rotas do painel web (login, fontes, curadoria, insights)
app.include_router(rotas_web_router)

# Frontend estático (web/). Fica por último para não encobrir as rotas da API.
PASTA_WEB = RAIZ / "web"
if PASTA_WEB.exists():
    app.mount("/", StaticFiles(directory=str(PASTA_WEB), html=True), name="web")
