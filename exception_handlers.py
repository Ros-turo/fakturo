from fastapi import Request
from fastapi.responses import JSONResponse

from exceptions import AuthError, FakturoNotFoundError, FakturoDeleteError, FakturoConflictError, BusinessRuleError


def invalid_credentials_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": f"{exc.detail}"},
    )

def not_found_handler(request: Request, exc: FakturoNotFoundError) -> JSONResponse:
    if exc.resource_id is None:
        content = {"detail": f"{exc.resource_name}: Not Found"}
    else:
        content = {"detail": f"{exc.resource_name} {exc.resource_id} is not found"}
    return JSONResponse(
        status_code=404,
        content=content)

def cant_delete_handler(request: Request, exc: FakturoDeleteError) -> JSONResponse:

    return JSONResponse(
        status_code= 405,
        content={"detail": f"{exc.resource_name}: {exc.resource_reason}"}
    )

def conflict_handler(request:Request, exc: FakturoConflictError):

    return JSONResponse(
        status_code=409,
        content={"detail": f"{exc.resource_name}: {exc.exc_detail}"}
    )

def business_rule_handler(request: Request, exc: BusinessRuleError):

    return JSONResponse(
        status_code=422,
        content={
            "rule_name": exc.rule,
            "detail": exc.detail
        }
    )