from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, room: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(room, set()).add(websocket)

    async def disconnect(self, room: str, websocket: WebSocket) -> None:
        async with self._lock:
            peers = self._rooms.get(room)
            if not peers:
                return
            peers.discard(websocket)
            if not peers:
                del self._rooms[room]

    async def broadcast(self, room: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            peers = list(self._rooms.get(room, ()))
        if not peers:
            return
        text = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in peers:
            try:
                await ws.send_text(text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("websocket send failed: %s", exc)
                dead.append(ws)
        if dead:
            async with self._lock:
                room_peers = self._rooms.get(room)
                if room_peers:
                    for ws in dead:
                        room_peers.discard(ws)


game_connections = ConnectionManager()
