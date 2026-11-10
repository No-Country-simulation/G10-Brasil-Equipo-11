"""Cliente HTTP usado pelo Streamlit para conversar com a API."""
from __future__ import annotations

import os
from typing import Any

import httpx


class APIClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code


def modo_api() -> bool:
    return (
        os.getenv("COMMUNITYLAB_UI_BACKEND", "api")
        .strip()
        .lower()
        == "api"
    )


def headers(
    idempotency_key: str | None = None,
) -> dict[str, str]:
    result = {
        "X-Actor": os.getenv(
            "COMMUNITYLAB_ACTOR", "curador-local"
        )[:255]
    }

    api_key = os.getenv("COMMUNITYLAB_API_KEY")
    if api_key:
        result["X-API-Key"] = api_key

    if idempotency_key:
        result["Idempotency-Key"] = idempotency_key

    return result


def request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    params: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> Any:
    base = os.getenv(
        "COMMUNITYLAB_API_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    timeout = float(
        os.getenv("COMMUNITYLAB_API_TIMEOUT_SECONDS", "300")
    )

    try:
        response = httpx.request(
            method,
            f"{base}{path}",
            json=payload,
            params=params,
            headers=headers(idempotency_key),
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise APIClientError(
            "A API excedeu o tempo limite. Repita a operação "
            "com a mesma chave de idempotência."
        ) from exc
    except httpx.HTTPError as exc:
        raise APIClientError(
            "Não foi possível conectar à API. Confira se o "
            "FastAPI está em execução e se COMMUNITYLAB_API_URL "
            "está correto."
        ) from exc

    try:
        body = response.json()
    except ValueError:
        body = {
            "detail": "A API devolveu uma resposta que não é JSON."
        }

    if response.is_error:
        if isinstance(body, dict):
            detail = body.get(
                "detail", "Falha ao executar a operação na API."
            )
        else:
            detail = "Falha na API."

        raise APIClientError(str(detail), response.status_code)

    return body