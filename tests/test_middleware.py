from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from app.middleware import (
    RequestContextAndBodyLimitMiddleware,
)


def _app(max_bytes: int = 1024):
    async def echo(request: Request):
        body = await request.body()
        return JSONResponse({
            "size": len(body),
            "request_id": request.state.request_id,
        })

    application = Starlette()
    application.add_route(
        "/echo",
        echo,
        methods=["POST"],
    )

    application.add_middleware(
        RequestContextAndBodyLimitMiddleware,
        max_bytes=max_bytes,
    )

    return application


def test_rejeita_body_maior_que_limite():
    client = TestClient(_app())

    response = client.post(
        "/echo",
        content=b"x" * 2048,
        headers={"X-Request-ID": "valid-id-123"},
    )

    assert response.status_code == 413
    assert response.headers["x-request-id"] == "valid-id-123"
    assert "limite" in response.json()["detail"]


def test_sanitiza_request_id():
    client = TestClient(_app())

    response = client.post(
        "/echo",
        content=b"ok",
        headers={"X-Request-ID": "bad injected"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "bad injected"
    assert (
        response.json()["request_id"]
        == response.headers["x-request-id"]
    )


def test_rejeita_body_chunked_maior_que_limite():
    client = TestClient(_app())

    response = client.post(
        "/echo",
        content=iter([b"x" * 700, b"y" * 700]),
    )

    assert response.status_code == 413
    assert "limite" in response.json()["detail"]