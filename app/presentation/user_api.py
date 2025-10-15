import os

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.data.repositories.user_repository import SessionLocal, create_user_table
from app.domain.services.auth_service import (
    authenticate_user,
    change_password,
    change_username,
    create_access_token,
    delete_user_account,
    get_current_user,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserCreateRequest(BaseModel):
    username: str
    password: str
    hcaptcha_token: str


class ChangeUsernameRequest(BaseModel):
    new_username: str


class ChangePasswordRequest(BaseModel):
    new_password: str


def verify_hcaptcha(token: str) -> bool:
    secret = os.getenv("HCAPTCHA_SECRET")
    if not secret:
        raise RuntimeError("HCAPTCHA_SECRET environment variable is not set")
    resp = requests.post(
        "https://hcaptcha.com/siteverify",
        data={"secret": secret, "response": token},
        timeout=5,
    )
    data = resp.json()
    return data.get("success", False)


@router.post("/register")
def register_user_endpoint(req: UserCreateRequest):
    if not verify_hcaptcha(req.hcaptcha_token):
        raise HTTPException(status_code=400, detail="hCaptcha verification failed")
    db = SessionLocal()
    try:
        user = register_user(db, req.username, req.password)
    except ValueError as e:
        db.close()
        raise HTTPException(status_code=400, detail=str(e))
    db.close()
    return {"username": user.username}


@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid Username: " + str(e))
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
    return {"username": current_user.username}


@router.delete("/delete")
def delete_current_user(current_user=Depends(get_current_user)):
    db = SessionLocal()
    success = delete_user_account(db, current_user.id)
    db.close()
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}


@router.post("/change-username")
def change_username_endpoint(
    req: ChangeUsernameRequest, current_user=Depends(get_current_user)
):
    db = SessionLocal()
    try:
        user = change_username(db, current_user.id, req.new_username)
    except ValueError as e:
        db.close()
        raise HTTPException(status_code=400, detail=str(e))
    db.close()
    return {"username": user.username}


@router.post("/change-password")
def change_password_endpoint(
    req: ChangePasswordRequest, current_user=Depends(get_current_user)
):
    db = SessionLocal()
    try:
        change_password(db, current_user.id, req.new_password)
    except ValueError as e:
        db.close()
        raise HTTPException(status_code=400, detail=str(e))
    db.close()
    return {"success": True}


# Ensure user table exists at startup
create_user_table()
