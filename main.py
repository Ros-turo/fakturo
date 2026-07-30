import asyncio

from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse

from logging_config import logger
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from middleware import TimingLoggingMiddleware, SecondMiddleware, CORSMiddleware
from routers import clients, auth, invoices
from sockets import wbs
from exceptions import FakturoNotFoundError, FakturoDeleteError, FakturoConflictError, BusinessRuleError



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

app.add_middleware(SecondMiddleware) #2 Inner wrapper
app.add_middleware(TimingLoggingMiddleware)
app.add_middleware(CORSMiddleware)#1 Global wrapper

app.include_router(clients.router)
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(wbs)


# Exceptions
@app.exception_handler(FakturoNotFoundError)
def not_found_exception(request: Request, exc: FakturoNotFoundError) -> JSONResponse :

    return JSONResponse(
        status_code=404,
        content={"detail": f"{exc.resource_name} {exc.resource_id} is not found"}
    )

@app.exception_handler(FakturoDeleteError)
def cant_delete_exception(request: Request, exc: FakturoDeleteError) -> JSONResponse:

    return JSONResponse(
        status_code= 405,
        content={"detail": f"{exc.resource_name}: {exc.resource_reason}"}
    )

@app.exception_handler(FakturoConflictError)
def conflict_error(request:Request, exc: FakturoConflictError):

    return JSONResponse(
        status_code=409,
        content={"detail": f"{exc.resource_name}: {exc.exc_detail}"}
    )

@app.exception_handler(BusinessRuleError)
def business_rule_error(request: Request, exc: BusinessRuleError):

    return JSONResponse(
        status_code=422,
        content={
            "rule_name": exc.rule,
            "detail": exc.detail
        }
    )

@app.get('/')
def info():

    return {"msg": {
        "API": "Facturo",
        "Version": "0.2",
        "Running": "run"
    }, "status": "ok"}