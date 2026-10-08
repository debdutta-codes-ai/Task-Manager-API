from sqlalchemy.orm import Session

from app import models


# =========================================================
# CREATE ROLE
# =========================================================


def create_role(
    db: Session,
    role_name: str,
    description: str | None = None
):
    existing_role = (
        db.query(models.Role)
        .filter(
            models.Role.name == role_name
        )
        .first()
    )

    if existing_role:
        return None

    db_role = models.Role(
        name=role_name,
        description=description
    )

    db.add(db_role)
    db.commit()
    db.refresh(db_role)

    return db_role


# =========================================================
# UPDATE ROLE
# =========================================================


def update_role(
    db: Session,
    role_id: int,
    role_data
):
    db_role = (
        db.query(models.Role)
        .filter(
            models.Role.id == role_id
        )
        .first()
    )

    if db_role is None:
        return None

    existing_role = (
        db.query(models.Role)
        .filter(
            models.Role.name == role_data.name,
            models.Role.id != role_id
        )
        .first()
    )

    if existing_role:
        return "role_exists"

    db_role.name = role_data.name
    db_role.description = role_data.description

    db.commit()
    db.refresh(db_role)

    return db_role


# =========================================================
# DELETE ROLE
# =========================================================


def delete_role(
    db: Session,
    role_id: int
):
    db_role = (
        db.query(models.Role)
        .filter(
            models.Role.id == role_id
        )
        .first()
    )

    if db_role is None:
        return None

    # Protect default roles
    if db_role.name in ["admin", "manager", "user"]:
        return "default_role"

    # Check whether users are using this role
    user = (
        db.query(models.User)
        .filter(
            models.User.role_id == role_id,
            models.User.status == "active"
        )
        .first()
    )

    if user is not None:
        return "role_in_use"

    db.delete(db_role)
    db.commit()

    return db_role