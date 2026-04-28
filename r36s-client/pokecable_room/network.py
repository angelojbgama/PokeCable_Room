from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import ssl
import struct
from typing import Any
from urllib.parse import urlparse


class NetworkUnavailable(RuntimeError):
    pass


class StdlibWebSocket:
    def __init__(self, url: str) -> None:
        self.url = url
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"ws", "wss"}:
            raise NetworkUnavailable("URL do servidor precisa comecar com ws:// ou wss://.")
        host = parsed.hostname
        if not host:
            raise NetworkUnavailable("URL WebSocket sem host.")
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        ssl_context = ssl.create_default_context() if parsed.scheme == "wss" else None
        connect_kwargs: dict[str, Any] = {"ssl": ssl_context}
        if ssl_context is not None:
            connect_kwargs["server_hostname"] = host
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, **connect_kwargs),
            timeout=20,
        )
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        host_header = host if parsed.port is None else f"{host}:{port}"
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.writer.write(request.encode("ascii"))
        await self.writer.drain()
        status = await self.reader.readline()
        if b" 101 " not in status:
            raise NetworkUnavailable(f"Servidor recusou WebSocket: {status.decode('ascii', 'replace').strip()}")
        headers: dict[str, str] = {}
        while True:
            line = await self.reader.readline()
            if line in {b"\r\n", b""}:
                break
            name, _, value = line.decode("ascii", "replace").partition(":")
            headers[name.lower().strip()] = value.strip()
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected_accept:
            raise NetworkUnavailable("Handshake WebSocket invalido.")

    async def send(self, text: str) -> None:
        await self._send_frame(0x1, text.encode("utf-8"))

    async def recv(self) -> str:
        fragments: list[bytes] = []
        while True:
            fin, opcode, payload = await self._read_frame()
            if opcode == 0x8:
                raise NetworkUnavailable("WebSocket fechado pelo servidor.")
            if opcode == 0x9:
                await self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                fragments = [payload]
            elif opcode == 0x0:
                fragments.append(payload)
            else:
                continue
            if fin:
                return b"".join(fragments).decode("utf-8")

    async def close(self) -> None:
        if self.writer is None:
            return
        try:
            await self._send_frame(0x8, b"")
        except Exception:
            pass
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except Exception:
            pass

    async def _send_frame(self, opcode: int, payload: bytes) -> None:
        if self.writer is None:
            raise NetworkUnavailable("WebSocket nao conectado.")
        first = 0x80 | opcode
        length = len(payload)
        if length <= 125:
            header = bytes([first, 0x80 | length])
        elif length <= 65535:
            header = bytes([first, 0x80 | 126]) + struct.pack("!H", length)
        else:
            header = bytes([first, 0x80 | 127]) + struct.pack("!Q", length)
        mask = os.urandom(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.writer.write(header + mask + masked)
        await self.writer.drain()

    async def _read_frame(self) -> tuple[bool, int, bytes]:
        if self.reader is None:
            raise NetworkUnavailable("WebSocket nao conectado.")
        header = await self.reader.readexactly(2)
        first, second = header
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", await self.reader.readexactly(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", await self.reader.readexactly(8))[0]
        mask = await self.reader.readexactly(4) if masked else b""
        payload = await self.reader.readexactly(length) if length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return fin, opcode, payload


class PokeCableNetworkClient:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url
        self.websocket = None
        self.client_id: str | None = None

    async def __aenter__(self) -> "PokeCableNetworkClient":
        try:
            import websockets
        except ImportError:
            self.websocket = StdlibWebSocket(self.server_url)
            await self.websocket.connect()
        else:
            self.websocket = await websockets.connect(self.server_url, max_size=64 * 1024, open_timeout=20)
        first = await self.receive()
        if first.get("type") == "connected":
            self.client_id = str(first.get("client_id"))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.websocket is not None:
            await self.websocket.close()

    async def send(self, payload: dict[str, Any]) -> None:
        if self.websocket is None:
            raise NetworkUnavailable("WebSocket nao conectado.")
        await self.websocket.send(json.dumps(payload))

    async def receive(self) -> dict[str, Any]:
        if self.websocket is None:
            raise NetworkUnavailable("WebSocket nao conectado.")
        raw = await self.websocket.recv()
        return json.loads(raw)

    async def wait_for(self, accepted_types: set[str], error_types: set[str] | None = None) -> dict[str, Any]:
        error_types = error_types or {"error", "generation_mismatch", "game_mismatch", "trade_cancelled"}
        while True:
            message = await self.receive()
            message_type = str(message.get("type"))
            if message_type in accepted_types:
                return message
            if message_type in error_types:
                raise RuntimeError(message.get("message") or message.get("reason") or message_type)
