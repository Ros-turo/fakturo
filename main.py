import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from routers import clients, auth, invoices

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(fmt="%(asctime)s | %(levelname)s | %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")

handler = logging.FileHandler("app.log")
handler.setLevel(logging.NOTSET)
handler.setFormatter(fmt=formatter)

logger.addHandler(handler)

@asynccontextmanager
async def lifespan(app):
    logger.info("Try to connect to database")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection SUCCESSFUL")
    except Exception as e:
        logger.exception("Database connection FAILED")
        raise
    yield
    logger.info("App shutdown")

app = FastAPI(lifespan=lifespan)
app.include_router(clients.router)
app.include_router(auth.router)
app.include_router(invoices.router)

@app.get('/')
def info():

    return {"msg": {
        "API": "Facturo",
        "Version": "0.2",
        "Running": "run"
    }, "status": "ok"}