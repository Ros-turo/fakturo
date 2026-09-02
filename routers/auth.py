import secrets
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Request, Response, Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from starlette.responses import JSONResponse

from schemas import UserCreate, RefreshTokensResponse
from database import DBSession
from db_models import User
from security.rate_limit import check_timeout, LADepends
from settings import settings
from repositories.user_repository import UserRepo
from repositories.auth_repository import AuthRepo
from cache import is_token_in_blacklist, add_token_to_blacklist
from security.hashing import hash_password, verify_password

router = APIRouter(prefix='/auth', tags=['auth'])


def get_user_repo(db:DBSession)->UserRepo:

    user_repo = UserRepo(db)
    return user_repo

UserDepends = Annotated[UserRepo, Depends(get_user_repo)]

def get_auth_repo(db:DBSession) -> AuthRepo:

    return AuthRepo(db)

AuthDepends = Annotated[AuthRepo, Depends(get_auth_repo)]

def invalid_credentials_exception() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid credentials")

def unauthorized_exception() -> HTTPException:
    return HTTPException(status_code=401, detail="Unauthorized")

def blocked_user_exception():
    return HTTPException(status_code=423, detail="Account is blocked")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


def create_access_token(email:str, uid:int) -> str:
    """
    ::param user data: email, password
    ::return user's token
    """
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(minutes=30)
    jti = str(uuid4())
    payload = {
        'sub': email,
        'jti': jti,
        'uid': uid,
        'iat': now,
        'exp': expire_time,
        'type': 'access'
    }

    return jwt.encode(payload, settings.secret_key, settings.algorithm)

def extract_access_token(request: Request) -> str | None:

    value = request.headers.get("Authorization")

    if value is None:
        return None

    token = value.removeprefix("Bearer ")
    return token

AccessTokenExtractor = Annotated[str|None, Depends(extract_access_token)]

async def blacklist_token(token: AccessTokenExtractor) -> None:

    if token:
        await add_token_to_blacklist(token)

AddTokenBlacklist = Annotated[None, Depends(blacklist_token)]

async def create_refresh_token(email: str, uid: int, auth_repo: AuthRepo):
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(days=15)
    jti = secrets.token_urlsafe(32)
    payload = {
        'uid': uid,
        'jti': jti,
        'iat': now,
        'exp': expire_time,
        'type': 'refresh'
    }

    token = jwt.encode(payload, settings.secret_key, settings.algorithm)

    await auth_repo.post_refresh_token(uid=uid, email=email,
                                      jti=jti, expired_at=expire_time)

    return token


def check_refresh_token(expired_at: datetime, revoked: bool) -> bool:

    now = datetime.now(timezone.utc)
    if expired_at < now or revoked:
        return False

    return True

def get_refresh_token_payload(request:Request) -> dict:

    token = request.cookies.get("refresh_token", None)
    if token is None:
        raise HTTPException(status_code=401, detail="Refresh token not found")


    payload = decode_jwt_token(token)

    return payload

def decode_jwt_token(token:str) -> dict:

    try:
        payload = jwt.decode(token, settings.secret_key, settings.algorithm)
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return payload

async def token_sender(email:str, uid: int, response: Response, auth_repo: AuthRepo) -> dict:

    access_token = create_access_token(email=email, uid=uid)
    refresh_token = await create_refresh_token(email=email, uid=uid, auth_repo= auth_repo)

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
        raise unauthorized_exception()
    else:
        return payload

CurrentUser = Annotated[dict, Depends(get_current_user)]


async def get_current_user_active(user: CurrentUser, repo: UserDepends):

    uid = user["uid"]
    user_data = await repo.get_by_uid(uid=uid)
    if user_data is None:
        raise invalid_credentials_exception()
    if not user_data.is_active:
        raise blocked_user_exception()
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
        raise HTTPException(status_code=400, detail="Account with this email already exist")

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
        raise invalid_credentials_exception()

    inst.clear_attempt()
    uid = current_user.id
    email = current_user.email

    content = await token_sender(email=email, uid=uid, response=response, auth_repo= auth_repo)

    return content

@router.post('/refresh')
async def token_refresh(request: Request, response: Response, auth_repo: AuthDepends):

    payload = get_refresh_token_payload(request=request)
    uid = payload["uid"]
    jti = payload['jti']

    token_data = await auth_repo.get_refresh_token(jti=jti)
    if token_data is None or not check_refresh_token(token_data.expired_at,
                                                     token_data.revoked):
        raise HTTPException(status_code=401, detail="Refresh token is not found")

    await auth_repo.revoke_token(token_data)

    email = token_data.user_email
    content = await token_sender(email=email, uid=uid, response=response, auth_repo=auth_repo)

    return content

@router.post("/logout", dependencies=[Depends(blacklist_token)])
async def logout(request: Request, auth_repo: AuthDepends,
                 response: Response):

    try:
        payload = get_refresh_token_payload(request=request)

    except HTTPException as e:
        if e.status_code == 401:
            payload = None
        else:
            raise

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

    raise HTTPException(status_code=403, detail="Not found device")