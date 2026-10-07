from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, crud
from app.database import get_db
from app.schemas import RoleCreate, RoleResponse, RoleUpdate


router = APIRouter(prefix="/roles")


@router.post(
    "/",
    status_code=201,
    response_model=RoleResponse
)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_roles("admin"))
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


@router.put(
    "/{role_id}",
    response_model=RoleResponse
)
def update_role(
    role_id: int,
    role: RoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_roles("admin")
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

@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_roles("admin")
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