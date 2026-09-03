from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from starlette.responses import JSONResponse

from exceptions import DeviceNotFoundError, EmailExistError, InvalidCredentialsError, RefreshTokenNotFoundError, SessionInBlacklistError, UserInactiveError
from schemas import UserCreate, RefreshTokensResponse
from database import DBSession
from db_models import User
from security.rate_limit import check_timeout, LADepends
from security.hashing import hash_password, verify_password
from security.tokens import decode_jwt_token, check_refresh_token
from repositories.user_repository import UserRepo
from repositories.auth_repository import AuthRepo
from services.auth_service import blacklist_token, get_refresh_token_payload, create_token_tuple
from cache import is_token_in_blacklist


router = APIRouter(prefix='/auth', tags=['auth'])


def get_user_repo(db:DBSession)->UserRepo:

    user_repo = UserRepo(db)
    return user_repo

UserDepends = Annotated[UserRepo, Depends(get_user_repo)]

def get_auth_repo(db:DBSession) -> AuthRepo:

    return AuthRepo(db)

AuthDepends = Annotated[AuthRepo, Depends(get_auth_repo)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

async def token_sender(email:str, uid: int, response: Response, auth_repo: AuthDepends):
    access_token, refresh_token = await create_token_tuple(email=email, uid=uid, auth_repo=auth_repo)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        max_age=14*24*60*60
    )
    return  {'access_token': access_token, 'token_type': 'bearer'}


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],) -> dict[str, Any]:

    payload = decode_jwt_token(token)
    jti = payload['jti']
    if await is_token_in_blacklist(jti):
        raise SessionInBlacklistError()
    else:
        return payload

CurrentUser = Annotated[dict, Depends(get_current_user)]


async def get_current_user_active(user: CurrentUser, repo: UserDepends):

    uid = user["uid"]
    user_data = await repo.get_by_uid(uid=uid)
    if user_data is None:
        raise InvalidCredentialsError()
    if not user_data.is_active:
        raise UserInactiveError()
    return user

CurrentActiveUser = Annotated[dict, Depends(get_current_user_active)]


def get_user_id(user: CurrentUser) -> int:

    return int(user["uid"])

UserID = Annotated[int, Depends(get_user_id)]


def get_security_user_id(user: CurrentActiveUser):

    return user["uid"]

SecurityID = Annotated[int, Depends(get_security_user_id)]

@router.post('/register', status_code=201)
async def register(user_data: UserCreate, repo: UserDepends):

    user_exist = await repo.get_by_email(user_data.email)
    if user_exist:
        raise EmailExistError()

    hashed_password = hash_password(user_data.password)

    new_user = User(**user_data.model_dump(exclude={"password"}), hashed_password=hashed_password)
    user = await repo.create_user(new_user)

    return JSONResponse(
        status_code=201,
        content={'msg': 'User registered', 'status': 'ok', 'UID': user.id}
    )

@router.post('/login', dependencies=[Depends(check_timeout)])
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                user_repo: UserDepends, auth_repo: AuthDepends,
                inst: LADepends, response: Response):

    current_user = await user_repo.get_by_email(form_data.username)
    if not current_user or not verify_password(form_data.password, current_user.hashed_password):
        inst.logging_attempt()
        raise InvalidCredentialsError()

    inst.clear_attempt()
    uid = current_user.id
    email = current_user.email

    content = await token_sender(email=email, uid=uid, response=response, auth_repo=auth_repo)

    return content

@router.post('/refresh')
async def token_refresh(request: Request, response: Response, auth_repo: AuthDepends):

    payload = get_refresh_token_payload(request=request)
    uid = payload["uid"]
    jti = payload['jti']

    token_data = await auth_repo.get_refresh_token(jti=jti)
    if token_data is None:
        raise RefreshTokenNotFoundError()

    check_refresh_token(token_data.expired_at,token_data.revoked)

    await auth_repo.revoke_token(token_data)

    email = token_data.user_email
    content = await token_sender(email=email, uid=uid, response=response, auth_repo=auth_repo)

    return content

@router.post("/logout", dependencies=[Depends(blacklist_token)])
async def logout(request: Request, auth_repo: AuthDepends,
                 response: Response):

    try:
        payload = get_refresh_token_payload(request=request)

    except RefreshTokenNotFoundError:
        payload = None


    if payload:
        jti = payload['jti']
        token_data = await auth_repo.get_refresh_token(jti=jti)

        if token_data is not None:
            await auth_repo.revoke_token(token_data)
            response.delete_cookie('refresh_token')

    return {
        "status": "logout"
    }

@router.post("/logout_device/all")
async def logout_all_devices(uid: SecurityID, auth_repo: AuthDepends):

    tokens = await auth_repo.get_actual_tokens(uid=uid)
    await auth_repo.bulk_revoke_tokens(tokens)

    return JSONResponse(status_code=200,
                        content={
                            "message": "Successful logout"
                        })


@router.get("/sessions", response_model=list[RefreshTokensResponse])
async def get_actual_sessions(uid: SecurityID, auth_repo: AuthDepends):

    tokens = await auth_repo.get_actual_tokens(uid=uid)
    return tokens

@router.post("/logout_device/{jti}")
async def logout_by_jti(jti: Annotated[str, Path()], uid: SecurityID, auth_repo: AuthDepends):

    token = await auth_repo.get_refresh_token(jti=jti)
    if token and token.user_id == uid:

        await auth_repo.revoke_token(token=token)
        return JSONResponse(status_code=200,
                            content={
                                "message": "Device was success logout"
                            })

    raise DeviceNotFoundError()