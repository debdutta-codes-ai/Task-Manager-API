from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, crud, models
from app.database import get_db
from app.schemas import (
    UserResponse,
    AdminUserCreate,
    AdminUserUpdate,
    Token
)


router = APIRouter(prefix="/users")


# =========================================================
# LOGIN
# =========================================================

@router.post(
    "/login",
    response_model=Token
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_username(
        db,
        form_data.username
    )

    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not auth.verify_password(
        form_data.password,
        db_user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = auth.create_access_token(
        data={
            "sub": str(db_user.id)
        },
        expires_delta=timedelta(
            minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# =========================================================
# MY PROFILE
# =========================================================

@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user=Depends(auth.get_current_user)
):
    return current_user


# =========================================================
# GET ALL USERS
# Requires: manage_users
# =========================================================

@router.get(
    "/",
    response_model=list[UserResponse]
)
def get_users(
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("manage_users")
    )
):
    return (
        db.query(models.User)
        .filter(models.User.status == "active")
        .all()
    )


# =========================================================
# GET ONE USER
# Requires: manage_users
# =========================================================

@router.get(
    "/{user_id}",
    response_model=UserResponse
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("manage_users")
    )
):
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


# =========================================================
# CREATE USER
# Requires: manage_users
# =========================================================

@router.post(
    "/",
    status_code=201,
    response_model=UserResponse,
    summary="Create User"
)
def create_user(
    user: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("manage_users")
    )
):
    new_user = crud.create_user_by_admin(
        db,
        user,
        current_user.id
    )

    if new_user is None:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    return new_user


# =========================================================
# UPDATE USER
# Requires: manage_users
# =========================================================

@router.put(
    "/{user_id}",
    response_model=UserResponse
)
def update_user(
    user_id: int,
    user: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("manage_users")
    )
):
    updated_user = crud.update_user_by_admin(
        db,
        user_id,
        user
    )

    if updated_user is None:
        raise HTTPException(
            status_code=404,
            detail="User or role not found"
        )

    return updated_user


# =========================================================
# DELETE USER
# Requires: manage_users
# =========================================================

@router.delete(
    "/{user_id}",
    response_model=UserResponse
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("manage_users")
    )
):
    deleted_user = crud.delete_user_by_admin(
        db,
        user_id,
        current_user.id
    )

    if deleted_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return deleted_user