from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import User
from ..auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if "@" not in data.email or "." not in data.email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    existing = db.query(User).filter_by(email=data.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=data.email.lower().strip(),
        name=data.name.strip(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }


@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email.lower().strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.email)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name}
