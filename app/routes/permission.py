from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, crud, models
from app.database import get_db
from app.schemas import PermissionCreate, PermissionResponse, PermissionUpdate


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

# =========================================================
# GET ONE PERMISSION
# Requires: change_roles
# =========================================================

@router.get(
    "/{permission_id}",
    response_model=PermissionResponse
)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    # Find the permission by ID
    permission = crud.get_permission(db, permission_id)

    # Return 404 if the permission does not exist
    if permission is None:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    return permission


# =========================================================
# UPDATE PERMISSION
# Requires: change_roles
# =========================================================

@router.put(
    "/{permission_id}",
    response_model=PermissionResponse
)
def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    # Check whether another permission already uses the new name
    if permission_data.name is not None:
        existing_permission = (
            db.query(models.Permission)
            .filter(
                models.Permission.name == permission_data.name,
                models.Permission.id != permission_id
            )
            .first()
        )

        if existing_permission:
            raise HTTPException(
                status_code=409,
                detail="Permission with this name already exists"
            )

    # Update the permission using the CRUD function
    updated_permission = crud.update_permission(
        db,
        permission_id,
        permission_data
    )

    # Return 404 if the permission does not exist
    if updated_permission is None:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    return updated_permission


# =========================================================
# DELETE PERMISSION
# Requires: change_roles
# =========================================================

@router.delete("/{permission_id}")
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    # Find the permission before attempting deletion
    permission = crud.get_permission(
        db,
        permission_id
    )

    # Return 404 if the permission does not exist
    if permission is None:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    # Prevent deleting the permission required for role management
    if permission.name == "change_roles":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the change_roles permission"
        )

    # Delete the permission and remove its role associations
    crud.delete_permission(
        db,
        permission_id
    )

    return {
        "message": "Permission deleted successfully"
    }