from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    _format_user,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db_connection import get_db
from app.models import User
from app.schemas import (
    TokenResponse,
    UserLogin,
    UserProfileUpdate,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    role = payload.role if payload.role else "buyer"
    if role not in ["buyer", "seller"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'buyer' or 'seller'",
        )

    # Buyers cannot have a store name
    if role == "buyer" and payload.store_name and payload.store_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buyers cannot have a store name",
        )

    # Pre-check for duplicate email in database
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    now = datetime.now(timezone.utc)
    name = payload.name.strip() if payload.name and payload.name.strip() else None
    store_name = (
        payload.store_name.strip()
        if (role == "seller" and payload.store_name and payload.store_name.strip())
        else None
    )

    new_user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role,
        name=name,
        store_name=store_name,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    return _format_user(new_user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _format_user(user),
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
@router.put("/me", response_model=UserResponse)
def update_me(
    payload: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if payload.name is not None:
        user.name = payload.name.strip() if payload.name.strip() else None

    if payload.store_name is not None:
        if user.role != "seller":
            if payload.store_name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only sellers can set a store name",
                )
            target_store_name: Optional[str] = None
        else:
            stripped_name = payload.store_name.strip()
            target_store_name = stripped_name if stripped_name else None
        setattr(user, "store_name", target_store_name)

    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return _format_user(user)


@router.patch("/profile", response_model=UserResponse, include_in_schema=False)
@router.put("/profile", response_model=UserResponse, include_in_schema=False)
def update_profile_alias(
    payload: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_me(payload=payload, current_user=current_user, db=db)