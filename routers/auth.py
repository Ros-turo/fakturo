from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from jose import jwt, JWTError

from schemas import UserCreate
from database import DBSession
from db_models import User
from config import p_key, p_alg
from repositories.user_repository import UserRepository

router = APIRouter(prefix='/auth', tags=['auth'])

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


def create_access_token(data: dict) -> str:
    """
    ::param user data: email, password
    ::return user's token
    """
    payload = data.copy()
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload.update({"exp": expire_time})
    token = jwt.encode(payload, p_key, p_alg)
    return token

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    """
    :param token
    :return:
    """
    try:
        payload = jwt.decode(token,p_key,p_alg)
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return payload

CurrentUser = Annotated[dict, Depends(get_current_user)]

def get_user_repo(db:DBSession)->UserRepository:
    user_repo = UserRepository(db)
    return user_repo

UserDepends = Annotated[UserRepository, Depends(get_user_repo)]

async def get_current_user_active(user: CurrentUser, repo: UserDepends):
    uid = user["uid"]
    user_data = await repo.get_by_uid(uid=uid)
    if user_data is None:
        raise invalid_credentials_exception()
    if not user_data.is_active:
        raise blocked_user_exception()
    return user

CurrentActiveUser = Annotated[dict, Depends(get_current_user_active)]

@router.post('/register')
async def register(user_data: UserCreate, repo: UserDepends):

    user_exist = await repo.get_by_email(user_data.email)
    if user_exist:
        raise HTTPException(status_code=400, detail="Account with this email already exist")

    hashed_password = hash_password(user_data.password)

    new_user = User(**user_data.model_dump(exclude="password"), hashed_password=hashed_password)
    user = await repo.create_user(new_user)

    return {'msg': 'User registered', 'status': 'ok', 'UID': user.id}

@router.post('/login')
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                repo: UserDepends):

    current_user = await repo.get_by_email(form_data.username)
    if not current_user or not verify_password(form_data.password, current_user.hashed_password):
        raise invalid_credentials_exception()


    token:str = create_access_token({"sub":current_user.email, "uid":current_user.id})
    return  {'access_token': token, 'token_type': 'bearer'}
