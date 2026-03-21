from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class SSEManager:
    def __init__(self):
        self._clients: list[asyncio.Queue] = []

    def connect(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._clients.append(queue)
        logger.info("SSEクライアント接続 (現在: %d)", len(self._clients))
        return queue

    def disconnect(self, queue: asyncio.Queue):
        if queue in self._clients:
            self._clients.remove(queue)
        logger.info("SSEクライアント切断 (現在: %d)", len(self._clients))

    async def broadcast(self, data: str):
        disconnected = []
        for queue in self._clients:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                disconnected.append(queue)
                logger.warning("SSEクライアントのキューが満杯のため切断します")
        for q in disconnected:
            if q in self._clients:
                self._clients.remove(q)

    @property
    def client_count(self) -> int:
        return len(self._clients)


sse_manager = SSEManager()
