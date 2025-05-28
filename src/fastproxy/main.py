# -*- encoding: utf-8 -*-
"""
main.py
----

@Time    :   2025/05/28 11:40:37
@Author  :   Mattholy
@Version :   1.0
@Contact :   smile.used@hotmail.com
@License :   MIT License
"""


import asyncio
from typing import AsyncGenerator, AsyncIterable, List, Tuple, cast

from fastapi import FastAPI, Request, WebSocket
from starlette.responses import StreamingResponse
from starlette.websockets import WebSocketDisconnect
from starlette.types import Message

import httpx
import websockets


class FastProxy(FastAPI):
    def __init__(
        self,
        base_url: str,
        *,
        debug: bool = False,
        title: str = "FastProxy",
        description: str = "",
        version: str = "0.1.0",
        openapi_url: str = "/openapi.json",
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
    ) -> None:
        """
        Initialize a FastProxy instance.

        :param base_url: The base URL of the downstream service to proxy to.
        :param debug: Enable debug mode.
        :param title: App title.
        :param description: App description.
        :param version: App version.
        :param openapi_url: URL for OpenAPI schema.
        :param docs_url: URL for Swagger UI.
        :param redoc_url: URL for ReDoc.
        """
        super().__init__(
            debug=debug,
            title=title,
            description=description,
            version=version,
            openapi_url=openapi_url,
            docs_url=docs_url,
            redoc_url=redoc_url,
        )
        self.base_url = base_url.rstrip("/")

        # HTTP streaming proxy
        @self.api_route(
            "/{full_path:path}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        )
        async def _proxy_request(  # type: ignore
            request: Request,
            full_path: str,
        ) -> StreamingResponse:
            target_url = f"{self.base_url}/{full_path}"
            # Forward headers except host
            forwarded_headers = {
                k: v for k, v in request.headers.items() if k.lower() != "host"
            }

            client = httpx.AsyncClient(timeout=None)
            # Stream both request body and response
            async with client.stream(
                method=request.method,
                url=target_url,
                params=request.query_params,
                headers=forwarded_headers,
                data=cast(AsyncIterable[bytes], request.stream()),  # type: ignore
            ) as resp:
                status = resp.status_code
                resp_headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() != "transfer-encoding"
                }

                async def stream_response() -> AsyncGenerator[bytes, None]:
                    try:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                    finally:
                        await client.aclose()

                return StreamingResponse(
                    content=stream_response(),
                    status_code=status,
                    headers=resp_headers,
                )

        # WebSocket proxy
        @self.websocket_route("/{full_path:path}")
        async def _proxy_websocket(  # type: ignore
            ws: WebSocket,
            full_path: str,
        ) -> None:
            await ws.accept()
            scheme = "wss" if self.base_url.startswith("https") else "ws"
            _, rest = self.base_url.split("://", 1)
            target_url = f"{scheme}://{rest}/{full_path}"
            extra_headers: List[Tuple[str, str]] = [
                (k, v) for k, v in ws.headers.items() if k.lower() != "host"
            ]

            try:
                async with websockets.connect(
                    target_url, extra_headers=extra_headers
                ) as downstream_ws:

                    async def forward_client_to_server() -> None:
                        try:
                            while True:
                                msg: Message = await ws.receive()
                                msg_type = msg.get("type", "")
                                if msg_type == "websocket.disconnect":
                                    break
                                if "text" in msg:
                                    await downstream_ws.send(msg["text"])
                                elif "bytes" in msg:
                                    await downstream_ws.send(msg["bytes"])
                        except WebSocketDisconnect:
                            pass
                        except Exception:
                            pass

                    async def forward_server_to_client() -> None:
                        try:
                            async for message in downstream_ws:
                                if isinstance(message, str):
                                    await ws.send_text(message)
                                else:
                                    await ws.send_bytes(message)
                        except Exception:
                            pass

                    await asyncio.gather(
                        forward_client_to_server(),
                        forward_server_to_client(),
                        return_exceptions=True,
                    )
            except Exception:
                await ws.close()
