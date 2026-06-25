import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WebSocketMessage:
    agent: str
    status: str
    progress: int
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        async with self._lock:
            if run_id not in self.active_connections:
                self.active_connections[run_id] = set()
            self.active_connections[run_id].add(websocket)
            logger.info(f"WebSocket connected for run {run_id}")

    async def disconnect(self, websocket: WebSocket, run_id: str):
        async with self._lock:
            if run_id in self.active_connections:
                self.active_connections[run_id].discard(websocket)
                if not self.active_connections[run_id]:
                    del self.active_connections[run_id]
            logger.info(f"WebSocket disconnected for run {run_id}")

    async def send_to_run(self, run_id: str, message: WebSocketMessage):
        async with self._lock:
            connections = self.active_connections.get(run_id, set()).copy()

        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message.to_dict())
            except Exception as e:
                logger.warning(f"Failed to send message: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            await self.disconnect(conn, run_id)

    async def broadcast(self, message: WebSocketMessage):
        for run_id in list(self.active_connections.keys()):
            await self.send_to_run(run_id, message)

    async def send_agent_status(
        self,
        run_id: str,
        agent_name: str,
        status: str,
        progress: int,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        ws_message = WebSocketMessage(
            agent=agent_name,
            status=status,
            progress=progress,
            message=message,
            data=data,
        )
        await self.send_to_run(run_id, ws_message)

    async def send_log(self, run_id: str, agent_name: str, log_message: str, level: str = "info"):
        message = WebSocketMessage(
            agent=agent_name,
            status="running",
            progress=0,
            message=log_message,
            data={"type": "log", "level": level},
        )
        await self.send_to_run(run_id, message)

    async def send_completion(self, run_id: str, success: bool, summary: Dict[str, Any]):
        message = WebSocketMessage(
            agent="Orchestrator",
            status="completed" if success else "failed",
            progress=100,
            message="Pipeline completed" if success else "Pipeline failed",
            data=summary,
        )
        await self.send_to_run(run_id, message)

    def get_connection_count(self, run_id: str) -> int:
        return len(self.active_connections.get(run_id, set()))


websocket_manager = ConnectionManager()
