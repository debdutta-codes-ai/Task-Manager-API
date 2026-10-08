from datetime import datetime

from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from app import models
from app.schemas import (
    UserCreate,
    AdminUserCreate,
    AdminUserUpdate
)


password_hash = PasswordHash.recommended()


# =========================================================
# USER CRUD
# =========================================================


def create_user(
    db: Session,
    user: UserCreate
):
    hashed_password = password_hash.hash(
        user.password
    )

    # Public registration always gets
    # the normal "user" role
    default_role = (
        db.query(models.Role)
        .filter(
            models.Role.name == "user"
        )
        .first()
    )

    if default_role is None:
        return None

    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role_id=default_role.id,
        status="active"
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def get_user_by_username(
    db: Session,
    username: str
):
    return (
        db.query(models.User)
        .filter(
            models.User.username == username
        )
        .first()
    )


def get_user_by_email(
    db: Session,
    email: str
):
    return (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )


# =========================================================
# ADMIN USER CRUD
# =========================================================


def create_user_by_admin(
    db: Session,
    user: AdminUserCreate,
    admin_id: int
):
    # Check that the role exists
    role = (
        db.query(models.Role)
        .filter(
            models.Role.id == user.role_id
        )
        .first()
    )

    if role is None:
        return None

    hashed_password = password_hash.hash(
        user.password
    )

    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role_id=role.id,
        status="active",
        created_by=admin_id
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def update_user_by_admin(
    db: Session,
    user_id: int,
    user: AdminUserUpdate
):
    db_user = (
        db.query(models.User)
        .filter(
            models.User.id == user_id
        )
        .first()
    )

    if db_user is None:
        return None

    # Check that the new role exists
    role = (
        db.query(models.Role)
        .filter(
            models.Role.id == user.role_id
        )
        .first()
    )

    if role is None:
        return None

    db_user.username = user.username
    db_user.email = user.email
    db_user.role_id = role.id

    db.commit()
    db.refresh(db_user)

    return db_user


def delete_user_by_admin(
    db: Session,
    user_id: int,
    admin_id: int
):
    db_user = (
        db.query(models.User)
        .filter(
            models.User.id == user_id
        )
        .first()
    )

    if db_user is None:
        return None

    db_user.status = "inactive"
    db_user.deleted_at = datetime.utcnow()
    db_user.deleted_by = admin_id

    db.commit()
    db.refresh(db_user)

    return db_user