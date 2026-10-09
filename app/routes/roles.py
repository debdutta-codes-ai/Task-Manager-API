from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, crud, models
from app.database import get_db
from app.schemas import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    RolePermissionCreate
)


router = APIRouter(
    prefix="/roles",
    tags=["Roles"]
)

# =========================================================
# GET ALL ROLES
# Requires: change_roles
# =========================================================

@router.get(
    "/",
    response_model=list[RoleResponse]
)
def get_roles(
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    # Fetch all roles using the CRUD function
    return crud.get_roles(db)

# =========================================================
# GET ONE ROLE
# Requires: change_roles
# =========================================================

@router.get(
    "/{role_id}",
    response_model=RoleResponse
)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    # Fetch the requested role using the CRUD function
    role = crud.get_role(db, role_id)

    # Return 404 if the role does not exist
    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    # Return the role, including its assigned permissions
    return role


# =========================================================
# CREATE ROLE
# Requires: change_roles
# =========================================================

@router.post(
    "/",
    status_code=201,
    response_model=RoleResponse
)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    db_role = crud.create_role(
        db,
        role.name,
        role.description
    )

    if db_role is None:
        raise HTTPException(
            status_code=409,
            detail="Role already exists"
        )

    return db_role


# =========================================================
# UPDATE ROLE
# Requires: change_roles
# =========================================================

@router.put(
    "/{role_id}",
    response_model=RoleResponse
)
def update_role(
    role_id: int,
    role: RoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    updated_role = crud.update_role(
        db,
        role_id,
        role
    )

    if updated_role is None:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    if updated_role == "role_exists":
        raise HTTPException(
            status_code=409,
            detail="Role with this name already exists"
        )

    return updated_role


# =========================================================
# DELETE ROLE
# Requires: change_roles
# =========================================================

@router.delete(
    "/{role_id}"
)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    deleted_role = crud.delete_role(
        db,
        role_id
    )

    if deleted_role is None:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    if deleted_role == "default_role":
        raise HTTPException(
            status_code=400,
            detail="Default roles cannot be deleted"
        )

    if deleted_role == "role_in_use":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete role because it is assigned to active users"
        )

    return {
        "message": "Role deleted successfully"
    }


# =========================================================
# ADD PERMISSION TO ROLE
# Requires: change_roles
# =========================================================

@router.post(
    "/{role_id}/permissions",
    status_code=201
)
def add_permission_to_role(
    role_id: int,
    data: RolePermissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    role = (
        db.query(models.Role)
        .filter(models.Role.id == role_id)
        .first()
    )

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    permission = (
        db.query(models.Permission)
        .filter(
            models.Permission.id == data.permission_id
        )
        .first()
    )

    if permission is None:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    if permission in role.permissions:
        raise HTTPException(
            status_code=409,
            detail="Permission already assigned to this role"
        )

    role.permissions.append(permission)

    db.commit()

    return {
        "message": "Permission assigned to role successfully"
    }


# =========================================================
# REMOVE PERMISSION FROM ROLE
# Requires: change_roles
# =========================================================

@router.delete(
    "/{role_id}/permissions/{permission_id}"
)
def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("change_roles")
    )
):
    role = (
        db.query(models.Role)
        .filter(models.Role.id == role_id)
        .first()
    )

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Role not found"
        )

    permission = (
        db.query(models.Permission)
        .filter(
            models.Permission.id == permission_id
        )
        .first()
    )

    if permission is None:
        raise HTTPException(
            status_code=404,
            detail="Permission not found"
        )

    if permission not in role.permissions:
        raise HTTPException(
            status_code=404,
            detail="Permission is not assigned to this role"
        )

    # Prevent removing change_roles from the admin role
    if (
        role.name == "admin"
        and permission.name == "change_roles"
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot remove change_roles from the admin role"
        )

    # Remove the permission from the role
    role.permissions.remove(permission)

    db.commit()

    return {
        "message": "Permission removed from role successfully"
    }