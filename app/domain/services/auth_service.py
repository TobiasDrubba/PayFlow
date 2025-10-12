import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.data.repositories.payment_repository import delete_all_user_data
from app.data.repositories.user_repository import (
    SessionLocal,
    create_user,
    delete_user,
    get_user_by_username,
    update_password,
    update_username,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    db = SessionLocal()
    user = get_user_by_username(db, username)
    db.close()
    if user is None:
        raise credentials_exception
    return user


def delete_user_account(db: Session, user_id: int):
    delete_all_user_data(db, user_id)
    return delete_user(db, user_id)


def change_username(db: Session, user_id: int, new_username: str):
    if get_user_by_username(db, new_username):
        raise ValueError("Username already taken")
    return update_username(db, user_id, new_username)


def change_password(db: Session, user_id: int, new_password: str):
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    hashed = get_password_hash(new_password)
    return update_password(db, user_id, hashed)


def register_user(db: Session, username: str, password: str):
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if get_user_by_username(db, username):
        raise ValueError("Username already registered")
    hashed_password = get_password_hash(password)
    return create_user(db, username, hashed_password)
