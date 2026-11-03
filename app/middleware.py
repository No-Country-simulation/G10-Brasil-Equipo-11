"""Middleware ASGI para correlação e limite de payload."""
from __future__ import annotations

import re
import uuid

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _RequestBodyTooLarge(Exception):
    pass


class RequestContextAndBodyLimitMiddleware:
    """Sanitiza X-Request-ID e limita o corpo da requisição."""

    def __init__(
        self,
        app: ASGIApp,
        max_bytes: int = 10 * 1024 * 1024,
    ):
        self.app = app
        self.max_bytes = max(1024, int(max_bytes))

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }

        supplied_id = headers.get(
            b"x-request-id", b""
        ).decode("latin-1", errors="ignore")

        request_id = (
            supplied_id
            if re.fullmatch(
                r"[A-Za-z0-9._:-]{1,100}", supplied_id
            )
            else str(uuid.uuid4())
        )

        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_context(message: Message) -> None:
            if message.get("type") == "http.response.start":
                output_headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ]
                output_headers.append(
                    (b"x-request-id", request_id.encode("ascii"))
                )
                message = {
                    **message,
                    "headers": output_headers,
                }

            await send(message)

        content_length = headers.get(b"content-length")

        if content_length:
            try:
                declared = int(content_length)
            except ValueError:
                await JSONResponse(
                    status_code=400,
                    content={"detail": "Content-Length inválido."},
                    headers={"X-Request-ID": request_id},
                )(scope, receive, send)
                return

            if declared > self.max_bytes:
                await JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            "Corpo da requisição excede "
                            "o limite permitido."
                        )
                    },
                    headers={"X-Request-ID": request_id},
                )(scope, receive, send)
                return

        received = 0
        response_started = False

        async def tracked_send(message: Message) -> None:
            nonlocal response_started

            if message.get("type") == "http.response.start":
                response_started = True

            await send_with_context(message)

        async def limited_receive() -> Message:
            nonlocal received

            message = await receive()

            if message.get("type") == "http.request":
                received += len(message.get("body", b""))

                if received > self.max_bytes:
                    raise _RequestBodyTooLarge()

            return message

        try:
            await self.app(
                scope,
                limited_receive,
                tracked_send,
            )
        except _RequestBodyTooLarge:
            if not response_started:
                await JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            "Corpo da requisição excede "
                            "o limite permitido."
                        )
                    },
                    headers={"X-Request-ID": request_id},
                )(scope, receive, send)