from fastapi.websockets import WebSocket, WebSocketDisconnect
from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from core.logger import get_logger

logger = get_logger(__name__)


class WSConnectionManagerInterface(ABC):
    @abstractmethod
    async def connect(self, websocket: WebSocket):
        pass

    @abstractmethod
    def disconnect(self, websocket: WebSocket):
        pass

    @abstractmethod
    async def send_message(self, websocket: WebSocket, message: str):
        pass

    @abstractmethod
    async def broadcast(self, websocket: WebSocket, message: str):
        pass


class WSConnectionManager(WSConnectionManagerInterface):
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, websocket: WebSocket, message: str):
        await websocket.send_text(data=message)

    async def broadcast(self, websocket: WebSocket, message: str):
        for connection in self.active_connections:
            connection.send_text(data=message)


async def get_ws_connection_manager() -> AsyncGenerator[WSConnectionManagerInterface, None]:
    try:
        manager = WSConnectionManager()
        yield manager
    except WebSocketDisconnect as e:
        logger.error(f"Error stablishing WebSocket connection: {str(e)}")
        raise e




