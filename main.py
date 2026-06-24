from logging_config import logger
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from middleware import TimingLoggingMiddleware, SecondMiddleware
from routers import clients, auth, invoices



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

app.add_middleware(SecondMiddleware) #2 Inner wrapper
app.add_middleware(TimingLoggingMiddleware) #1 Global wrapper

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