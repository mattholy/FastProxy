# src/my_fastapi_proxy/proxy_fastapi.py
import asyncio
from typing import Any, Dict, AsyncGenerator, List, Tuple

from fastapi import FastAPI, Request, WebSocket
from starlette.responses import StreamingResponse
from starlette.websockets import WebSocketDisconnect
from starlette.types import Message

import httpx
import websockets


class FastProxy(FastAPI):
    def __init__(self, base_url: str, **fastapi_kwargs: Any) -> None:
        """
        Initialize a FastProxy instance.

        :param base_url: The base URL of the downstream service to proxy to.
        :param fastapi_kwargs: Additional FastAPI parameters (title, docs_url, etc.).
        """
        super().__init__(**fastapi_kwargs)
        self.base_url: str = base_url.rstrip("/")

        # HTTP streaming proxy
        @self.api_route(
            "/{full_path:path}",
            methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        )
        async def _proxy_request(  # type: ignore
            request: Request,
            full_path: str,
        ) -> StreamingResponse:
            target_url: str = f"{self.base_url}/{full_path}"
            forwarded_headers: Dict[str, str] = {
                k: v for k, v in request.headers.items() if k.lower() != "host"
            }
            # Read body once before streaming
            body: bytes = await request.body()

            client: httpx.AsyncClient = httpx.AsyncClient(timeout=None)
            async with client.stream(
                method=request.method,
                url=target_url,
                params=request.query_params,
                headers=forwarded_headers,
                content=body,
            ) as resp:
                status_code: int = resp.status_code
                resp_headers: Dict[str, str] = {
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
                    status_code=status_code,
                    headers=resp_headers,
                )

        # WebSocket proxy
        @self.websocket_route("/{full_path:path}")
        async def _proxy_websocket(  # type: ignore
            ws: WebSocket,
            full_path: str,
        ) -> None:
            await ws.accept()
            scheme: str = "wss" if self.base_url.startswith("https") else "ws"
            _, rest = self.base_url.split("://", 1)
            target_url: str = f"{scheme}://{rest}/{full_path}"
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
                                msg_type: str = msg.get("type", "")
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
                    )
            except Exception:
                await ws.close()
