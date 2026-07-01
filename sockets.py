import asyncio

from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from logging_config import logger

wbs = APIRouter(prefix="/ws")

async def receiver(websocket: WebSocket):
    while True:
        text = await websocket.receive_text()
        await websocket.send_text(f"Server detect a message: {text}")

async def ticker(websocket: WebSocket):

    while True:
        await asyncio.sleep(2)
        await websocket.send_text("Ticker activate")

@wbs.websocket('/')
async def chat(websocket: WebSocket):

    await websocket.accept()
    coros = [receiver(websocket), ticker(websocket)]
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(c) for c in coros]
    except* WebSocketDisconnect:
        logger.info("Client was disconnected")
