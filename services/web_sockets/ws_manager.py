from abc import ABC, abstractmethod
from typing import List, AsyncGenerator, Annotated
from fastapi import Depends, WebSocket, WebSocketDisconnect
# from fastapi.websockets import WebSocket, WebSocketDisconnect

from core.logger import get_logger

logger = get_logger(__name__)


class WSClientInterface(ABC):

    @property
    @abstractmethod
    def active_connections(self) -> List[WebSocket]:
        """List of active WebSocket connections."""
        pass

    @abstractmethod
    async def connect(self, websocket: WebSocket) -> None:
        """Establish a WebSocket connection."""
        pass

    @abstractmethod
    async def close_connection(self, websocket: WebSocket) -> None:
        """Close the WebSocket connection."""
        pass

    @abstractmethod
    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected WebSocket clients."""
        pass


class WSClient(WSClientInterface):
    def __init__(self):
        self._active_connections: List[WebSocket] = []

    @property
    def active_connections(self) -> List[WebSocket]:
        return self._active_connections.copy()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active_connections.append(websocket)

    async def close_connection(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self._active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        disconnected = []
        logger.info(f"Broadcasting to {len(self.active_connections)} clients: {message}")
        for connection in self._active_connections:
            try:
                print("Broadcasting message to all connected clients")
                print(message)
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)

        for conn in disconnected:
            self._active_connections.remove(conn)


ws_manager = WSClient()


async def get_ws_manager_client() -> WSClientInterface:
    return ws_manager


ws_manager_dep = Annotated[WSClientInterface, Depends(get_ws_manager_client)]
