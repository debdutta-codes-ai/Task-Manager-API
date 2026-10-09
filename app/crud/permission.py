from sqlalchemy.orm import Session

from app import models


# =========================================================
# GET ONE PERMISSION
# =========================================================

def get_permission(
    db: Session,
    permission_id: int
):
    # Find a permission by its ID
    return (
        db.query(models.Permission)
        .filter(
            models.Permission.id == permission_id
        )
        .first()
    )


# =========================================================
# UPDATE PERMISSION
# =========================================================

def update_permission(
    db: Session,
    permission_id: int,
    data
):
    # Find the permission to update
    permission = get_permission(db, permission_id)

    if permission is None:
        return None

    # Update only the fields provided by the client
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(permission, field, value)

    db.commit()
    db.refresh(permission)

    return permission


# =========================================================
# DELETE PERMISSION
# =========================================================

def delete_permission(
    db: Session,
    permission_id: int
):
    # Find the permission to delete
    permission = get_permission(db, permission_id)

    if permission is None:
        return None

    # Remove associations between this permission and its roles
    permission.roles.clear()

    # Delete the permission from the database
    db.delete(permission)
    db.commit()

    return permission