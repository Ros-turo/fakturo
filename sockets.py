import asyncio
from asyncio import sleep
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, HTTPException, Path

from routers.auth import UserID

from logging_config import logger


class ConnectionManager:

    def __init__(self) -> None:
        # self.chats = {} - Placeholder for more rooms
        self.connected_users: dict[int, WebSocket] = {}

    async def connect(self, uid:int, wbs: WebSocket) -> None:

        self.connected_users[uid] = wbs
        await wbs.accept()

    def disconnect(self, uid: int) -> None:
        self.connected_users.pop(uid)
        print(self.connected_users)

    async def sender(self, uid: int, message: str) -> None:

        for user, wbs in self.connected_users.items():
            if user == uid:
                continue
            else:
                await wbs.send_text(message)

wbs = APIRouter(prefix="/ws")
manager = ConnectionManager()

@wbs.websocket('/chat')
async def chat(websocket: WebSocket):

    uid = websocket.query_params.get("uid")
    if uid is None:
        await websocket.close(code=1008, reason="Missing uid")
        return

    # Placeholder for take name, surname from db
    i_uid = int(uid)
    await manager.connect(wbs=websocket, uid=i_uid)

    try:
        while True:
            message = await websocket.receive_text()
            await manager.sender(i_uid, message)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(i_uid)


    ...




