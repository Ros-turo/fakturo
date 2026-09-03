from starlette.requests import Request
from fastapi.responses import JSONResponse
from logging_config import logger
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from middleware import TimingLoggingMiddleware, CORSMiddleware
from routers import clients, auth, invoices
from sockets import wbs
from exceptions import AuthError, FakturoNotFoundError, FakturoDeleteError, FakturoConflictError, BusinessRuleError
from exception_handlers import (business_rule_handler, conflict_handler, invalid_credentials_handler,
                                not_found_handler, cant_delete_handler)



@asynccontextmanager
async def lifespan(app: FastAPI):
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

#2 Inner wrapper
app.add_middleware(TimingLoggingMiddleware)
app.add_middleware(CORSMiddleware)
#1 Global wrapper

app.include_router(clients.router)
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(wbs)


# Exceptions
app.add_exception_handler(FakturoNotFoundError, not_found_handler)  # pyright: ignore [reportArgumentType]
app.add_exception_handler(AuthError, invalid_credentials_handler)  # pyright: ignore [reportArgumentType]
app.add_exception_handler(FakturoDeleteError, cant_delete_handler)  # pyright: ignore [reportArgumentType]
app.add_exception_handler(FakturoConflictError, conflict_handler)  # pyright: ignore [reportArgumentType]
app.add_exception_handler(BusinessRuleError, business_rule_handler)  # pyright: ignore [reportArgumentType]

@app.get('/')
def info():

    return {"msg": {
        "API": "Facturo",
        "Version": "0.2",
        "Running": "run"
    }, "status": "ok"}