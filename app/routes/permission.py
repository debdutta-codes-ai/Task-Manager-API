from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, crud, models
from app.database import get_db
from app.schemas import PermissionCreate, PermissionResponse


router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"]
)


# =========================================================
# CREATE PERMISSION
# Requires: change_roles
# =========================================================

@router.post(
    "/",
    status_code=201,
    response_model=PermissionResponse
)
def create_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    existing_permission = (
        db.query(models.Permission)
        .filter(
            models.Permission.name == permission.name
        )
        .first()
    )

    if existing_permission:
        raise HTTPException(
            status_code=409,
            detail="Permission already exists"
        )

    db_permission = models.Permission(
        name=permission.name,
        description=permission.description
    )

    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)

    return db_permission


# =========================================================
# GET ALL PERMISSIONS
# Requires: change_roles
# =========================================================

@router.get(
    "/",
    response_model=list[PermissionResponse]
)
def get_permissions(
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    permissions = (
        db.query(models.Permission)
        .order_by(models.Permission.id)
        .all()
    )

    return permissions