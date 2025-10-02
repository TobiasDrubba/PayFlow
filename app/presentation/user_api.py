from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.data.user_repository import SessionLocal, create_user, get_user_by_username, create_user_table
from app.domain.user_service import get_password_hash, authenticate_user, create_access_token, get_current_user
from app.domain.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreateRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
def register_user(req: UserCreateRequest):
    db = SessionLocal()
    if get_user_by_username(db, req.username):
        db.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(req.password)
    user = create_user(db, req.username, hashed_password)
    db.close()
    return {"username": user.username}

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = authenticate_user(db, form_data.username, form_data.password)
    db.close()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def read_users_me(current_user=Depends(get_current_user)):
    return {
        "username": current_user.username
    }

# Ensure user table exists at startup
create_user_table()
