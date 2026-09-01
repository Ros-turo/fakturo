from pwdlib import PasswordHash

pwd_hasher = PasswordHash.recommended()
def hash_password(password:str) -> str:
    return pwd_hasher.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_hasher.verify(password=password, hash=hashed_password)