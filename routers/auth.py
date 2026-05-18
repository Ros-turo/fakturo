from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from jose import jwt, JWTError

from sqlalchemy.orm import Session

from schemas import UserCreate
from database import get_db
from db_models import User
from config import p_key, p_alg

router = APIRouter(prefix='/auth', tags=['auth'])


pwd_hasher = PasswordHash.recommended()
def hash_password(password: str) -> str:
    return pwd_hasher.hash(password)

def verify_password(password: str, hashed_pwd) -> bool:
    return pwd_hasher.verify(password=password, hash=hashed_pwd)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload.update({"exp": expire_time})
    return jwt.encode(payload, p_key, p_alg)

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token,p_key,p_alg)
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return payload

CurrentUser = Annotated[dict, Depends(get_current_user)]

@router.post('/register')
def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]):

    user_exist = db.query(User).filter(User.email == user_data.email).first()
    if user_exist:
        raise HTTPException(status_code=400, detail="Account with this email already exist")

    hashed_password = hash_password(user_data.password)

    new_user = User(**user_data.model_dump(exclude="password"), hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {'msg': 'User registered', 'status': 'ok', 'UID': new_user.id}

@router.post('/login')
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
          db: Annotated[Session, Depends(get_db)]):

    current_user: User = db.query(User).filter(User.email == form_data.username).first()
    if not current_user or not verify_password(form_data.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")


    token:str = create_access_token({"sub":current_user.email, "uid":current_user.id})
    return  {'access_token': token, 'token_type': 'bearer'}
