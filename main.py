from logging_config import logger
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from middleware import TimingLoggingMiddleware, CORSMiddleware, MaxBodySizeMiddleware
from routers import clients, auth, invoices
from exceptions import (
    ARESNotAvailableError,
    AuthError,
    FakturoNotFoundError,
    FakturoDeleteError,
    FakturoConflictError,
    BusinessRuleError,
)
from exception_handlers import (
    ares_not_available_handler,
    business_rule_handler,
    conflict_handler,
    invalid_credentials_handler,
    not_found_handler,
    cant_delete_handler,
)
from settings import settings


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

# 2 Inner wrapper
app.add_middleware(TimingLoggingMiddleware)
app.add_middleware(CORSMiddleware, allowed_origins=settings.allowed_origins)
app.add_middleware(MaxBodySizeMiddleware)
# 1 Global wrapper

app.include_router(clients.router)
app.include_router(auth.router)
app.include_router(invoices.router)


# Exceptions
app.add_exception_handler(FakturoNotFoundError, not_found_handler)  #  type: ignore[arg-type] # pyright: ignore [reportArgumentType]
app.add_exception_handler(AuthError, invalid_credentials_handler)  #  type: ignore[arg-type] # pyright: ignore [reportArgumentType]
app.add_exception_handler(FakturoDeleteError, cant_delete_handler)  #  type: ignore[arg-type] # pyright: ignore [reportArgumentType]
app.add_exception_handler(FakturoConflictError, conflict_handler)  #  type: ignore[arg-type] # pyright: ignore [reportArgumentType]
app.add_exception_handler(BusinessRuleError, business_rule_handler)  #  type: ignore[arg-type] # pyright: ignore [reportArgumentType]
app.add_exception_handler(ARESNotAvailableError, ares_not_available_handler)  #  type: ignore[arg-type] # pyright: ignore [reportArgumentType]


@app.get("/")
def info():

    return {
        "msg": {"API": "Facturo", "Version": "0.2", "Running": "run"},
        "status": "ok",
    }
