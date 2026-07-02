import secrets
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, Request, Response, Cookie
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from jose import jwt, JWTError
from starlette.responses import JSONResponse

from schemas import UserCreate
from database import DBSession, SessionLocal
from db_models import User, RefreshToken
from settings import settings
from repositories.user_repository import UserRepo
from repositories.auth_repository import AuthRepo
from logging_config import logger

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

def blocked_user_exception():
    return HTTPException(status_code=423, detail="Account is blocked")

pwd_hasher = PasswordHash.recommended()
def hash_password(password: str) -> str:
    return pwd_hasher.hash(password)

def verify_password(password: str, hashed_pwd) -> bool:
    return pwd_hasher.verify(password=password, hash=hashed_pwd)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

logging_attempt = {}
blocked_ip = {}

def ip_blocker(ip: str) -> None:

    blocked_to = datetime.now() + timedelta(minutes=10)
    blocked_ip[ip] = blocked_to

    logger.warning(f"{ip} has to many attempts and blocked to 10 minutes")

    raise HTTPException(status_code=429, detail="Too many attempts")

def checker_block(request: Request) -> None:

    ip = request.client.host

    blocked_to = blocked_ip.get(ip, None)

    if blocked_to is None or blocked_to < datetime.now():
        return None

    raise HTTPException(status_code=429, detail=" Too many attempts, try later")

def remove_attempt(ip: str) -> None:
    logging_attempt[ip] = []

def logger_attempt(request: Request) -> None:

    ip = request.client.host
    
    now = datetime.now()
    future = now + timedelta(minutes=10)

    if logging_attempt.get(ip) is None:
        logging_attempt[ip] = []

    logging_attempt[ip].append(future)

    for attempt in logging_attempt[ip][:]:
        if now > attempt:
            logging_attempt[ip].remove(attempt)

    if len(logging_attempt[ip]) >= 5:
        ip_blocker(ip)

    return ip


def create_access_token(email:str, uid:int) -> str:
    """
    ::param user data: email, password
    ::return user's token
    """
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(minutes=30)
    payload = {
        'sub': email,
        'uid': uid,
        'iat': now,
        'exp': expire_time,
        'type': 'access'
    }

    return jwt.encode(payload, settings.secret_key, settings.algorithm)

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

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],) -> dict:

    payload = decode_jwt_token(token)
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

    return user["uid"]

UserID = Annotated[int, Depends(get_user_id)]


def get_security_user_id(user: CurrentActiveUser):

    return user["uid"]

SecurityID = Annotated[int, Depends(get_security_user_id)]

@router.post('/register')
async def register(user_data: UserCreate, repo: UserDepends):

    user_exist = await repo.get_by_email(user_data.email)
    if user_exist:
        raise HTTPException(status_code=400, detail="Account with this email already exist")

    hashed_password = hash_password(user_data.password)

    new_user = User(**user_data.model_dump(exclude="password"), hashed_password=hashed_password)
    user = await repo.create_user(new_user)

    return {'msg': 'User registered', 'status': 'ok', 'UID': user.id}

@router.post('/login', dependencies=[Depends(checker_block)])
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                user_repo: UserDepends, auth_repo: AuthDepends,
                ip: Annotated[str, Depends(logger_attempt)],response: Response):

    current_user = await user_repo.get_by_email(form_data.username)
    if not current_user or not verify_password(form_data.password, current_user.hashed_password):
        raise invalid_credentials_exception()

    uid = current_user.id
    email = current_user.email

    remove_attempt(ip)
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
        raise HTTPException(status_code=401, detail="Refresh token ")

    await auth_repo.revoke_token(token_data)

    email = token_data.user_email
    content = await token_sender(email=email, uid=uid, response=response, auth_repo=auth_repo)

    return content

@router.post("/logout")
async def logout(request: Request, auth_repo: AuthDepends,
                 response: Response):

    try:
        payload = get_refresh_token_payload(request=request)
        
    except HTTPException as e:
        if e.status_code == 401:
            payload = False
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

