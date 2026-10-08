from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, crud
from app.database import get_db
from app.schemas import TaskCreate, TaskResponse


router = APIRouter(prefix="/tasks")


# =========================================================
# CREATE TASK
# =========================================================

@router.post(
    "/",
    status_code=201,
    response_model=TaskResponse
)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_permissions("create_task")
    )
):
    created_task = crud.create_task(
        db,
        task,
        current_user.id,
        current_user
    )

    if created_task == "not_allowed":
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to assign this task"
        )

    if created_task is None:
        raise HTTPException(
            status_code=404,
            detail="Assigned user email not found"
        )

    return created_task


# =========================================================
# READ ALL TASKS
# =========================================================

@router.get(
    "/",
    response_model=list[TaskResponse]
)
def get_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    user_permissions = {
        permission.name
        for permission in current_user.role.permissions
    }

    if "read_all_tasks" in user_permissions:
        return crud.get_tasks(
            db,
            current_user
        )

    if (
        "read_team_tasks" in user_permissions
        or "read_own_task" in user_permissions
    ):
        return crud.get_tasks(
            db,
            current_user
        )

    raise HTTPException(
        status_code=403,
        detail="Insufficient permissions"
    )


# =========================================================
# READ ONE TASK
# =========================================================

@router.get(
    "/{task_id}",
    response_model=TaskResponse
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    task = crud.get_task(
        db,
        task_id
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    user_permissions = {
        permission.name
        for permission in current_user.role.permissions
    }

    # -----------------------------------------------------
    # Read any task
    # -----------------------------------------------------

    if "read_all_tasks" in user_permissions:
        return task

    # -----------------------------------------------------
    # Read own task
    # -----------------------------------------------------

    if task.owner_id == current_user.id:

        if "read_own_task" in user_permissions:
            return task

        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )

    # -----------------------------------------------------
    # Read team task
    # -----------------------------------------------------

    if crud.is_manager_of_task(
        db,
        current_user.id,
        task_id
    ):

        if "read_team_tasks" in user_permissions:
            return task

        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )

    raise HTTPException(
        status_code=403,
        detail="You are not allowed to access this task"
    )


# =========================================================
# UPDATE TASK
# =========================================================

@router.put(
    "/{task_id}",
    response_model=TaskResponse
)
def update_task(
    task_id: int,
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    db_task = crud.get_task(
        db,
        task_id
    )

    if db_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    user_permissions = {
        permission.name
        for permission in current_user.role.permissions
    }

    # -----------------------------------------------------
    # Update any task
    # -----------------------------------------------------

    if "update_any_task" in user_permissions:

        updated_task = crud.update_task_by_manager_or_admin(
            db,
            db_task,
            task,
            current_user
        )

        if updated_task == "assigned_user_not_found":
            raise HTTPException(
                status_code=404,
                detail="Assigned user email not found"
            )

        if updated_task == "not_allowed":
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to assign this task to that user"
            )

        return updated_task

    # -----------------------------------------------------
    # Update own task
    # -----------------------------------------------------

    if db_task.owner_id == current_user.id:

        if "update_own_task" not in user_permissions:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        updated_task = crud.update_task(
            db,
            task_id,
            task,
            current_user.id
        )

        if updated_task == "assigned_user_not_found":
            raise HTTPException(
                status_code=404,
                detail="Assigned user email not found"
            )

        if updated_task == "not_allowed":
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to assign this task to another user"
            )

        if updated_task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )

        return updated_task

    # -----------------------------------------------------
    # Update team task
    # -----------------------------------------------------

    if crud.is_manager_of_task(
        db,
        current_user.id,
        task_id
    ):

        if "update_team_task" not in user_permissions:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        updated_task = crud.update_task_by_manager_or_admin(
            db,
            db_task,
            task,
            current_user
        )

        if updated_task == "assigned_user_not_found":
            raise HTTPException(
                status_code=404,
                detail="Assigned user email not found"
            )

        if updated_task == "not_allowed":
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to assign this task to that user"
            )

        return updated_task

    raise HTTPException(
        status_code=403,
        detail="You are not allowed to update this task"
    )


# =========================================================
# DELETE TASK
# =========================================================

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    db_task = crud.get_task(
        db,
        task_id
    )

    if db_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    user_permissions = {
        permission.name
        for permission in current_user.role.permissions
    }

    # -----------------------------------------------------
    # Delete any task
    # -----------------------------------------------------

    if "delete_any_task" in user_permissions:

        db.delete(db_task)
        db.commit()

        return {
            "message": "Task deleted successfully"
        }

    # -----------------------------------------------------
    # Delete own task
    # -----------------------------------------------------

    if db_task.owner_id == current_user.id:

        if "delete_own_task" not in user_permissions:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        db.delete(db_task)
        db.commit()

        return {
            "message": "Task deleted successfully"
        }

    # -----------------------------------------------------
    # Delete team task
    # -----------------------------------------------------

    if crud.is_manager_of_task(
        db,
        current_user.id,
        task_id
    ):

        if "delete_team_task" not in user_permissions:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        db.delete(db_task)
        db.commit()

        return {
            "message": "Task deleted successfully"
        }

    raise HTTPException(
        status_code=403,
        detail="You are not allowed to delete this task"
    )


















# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session

# from app import auth, crud
# from app.database import get_db
# from app.schemas import TaskCreate, TaskResponse


# router = APIRouter(prefix="/tasks")


# # =========================
# # CREATE TASK
# # =========================

# @router.post(
#     "/",
#     status_code=201,
#     response_model=TaskResponse
# )
# def create_task(
#     task: TaskCreate,
#     db: Session = Depends(get_db),
#     current_user=Depends(
#         auth.require_permissions("create_task")
#     )
# ):
#     created_task = crud.create_task(
#         db,
#         task,
#         current_user.id,
#         current_user
#     )

#     if created_task == "not_allowed":
#         raise HTTPException(
#             status_code=403,
#             detail="You are not allowed to assign this task"
#         )

#     if created_task is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Assigned user email not found"
#         )

#     return created_task


# # =========================
# # READ ALL TASKS
# # =========================

# @router.get(
#     "/",
#     response_model=list[TaskResponse]
# )
# def get_tasks(
#     db: Session = Depends(get_db),
#     current_user=Depends(auth.get_current_user)
# ):
#     user_permissions = {
#         permission.name
#         for permission in current_user.role.permissions
#     }

#     # -------------------------
#     # ADMIN
#     # -------------------------

#     if "read_all_tasks" in user_permissions:
#         return crud.get_tasks(
#             db,
#             current_user
#         )

#     # -------------------------
#     # MANAGER
#     # -------------------------

#     if (
#         "read_own_task" in user_permissions
#         or "read_team_tasks" in user_permissions
#     ):
#         return crud.get_tasks(
#             db,
#             current_user
#         )

#     # -------------------------
#     # NORMAL USER
#     # -------------------------

#     if "read_own_task" in user_permissions:
#         return crud.get_tasks(
#             db,
#             current_user
#         )

#     raise HTTPException(
#         status_code=403,
#         detail="Insufficient permissions"
#     )

# # =========================
# # READ ONE TASK
# # =========================

# @router.get(
#     "/{task_id}",
#     response_model=TaskResponse
# )
# def get_task(
#     task_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(auth.get_current_user)
# ):
#     task = crud.get_task(
#         db,
#         task_id
#     )

#     if task is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Task not found"
#         )

#     # Admin can read any task
#     if current_user.role.name == "admin":
#         return task

#     # User / Manager can read their own task
#     if task.owner_id == current_user.id:
#         return task

#     # Manager can read tasks belonging to
#     # teams they manage
#     if current_user.role.name == "manager":

#         if crud.is_manager_of_task(
#             db,
#             current_user.id,
#             task_id
#         ):
#             return task

#     raise HTTPException(
#         status_code=403,
#         detail="You are not allowed to access this task"
#     )


# # =========================
# # UPDATE TASK
# # =========================

# @router.put(
#     "/{task_id}",
#     response_model=TaskResponse
# )
# def update_task(
#     task_id: int,
#     task: TaskCreate,
#     db: Session = Depends(get_db),
#     current_user=Depends(auth.get_current_user)
# ):

#     db_task = crud.get_task(
#         db,
#         task_id
#     )

#     if db_task is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Task not found"
#         )

#     # =========================
#     # ADMIN
#     # =========================

#     if current_user.role.name == "admin":

#         has_permission = any(
#             permission.name == "update_any_task"
#             for permission in current_user.role.permissions
#         )

#         if not has_permission:
#             raise HTTPException(
#                 status_code=403,
#                 detail="Insufficient permissions"
#             )

#         updated_task = crud.update_task_by_manager_or_admin(
#             db,
#             db_task,
#             task,
#             current_user
#         )

#         if updated_task == "assigned_user_not_found":
#             raise HTTPException(
#                 status_code=404,
#                 detail="Assigned user email not found"
#             )

#         return updated_task

#     # =========================
#     # MANAGER
#     # =========================

#     if current_user.role.name == "manager":

#         # -------------------------
#         # Manager updating own task
#         # -------------------------

#         if crud.is_manager_of_task(
#             db,
#             current_user.id,
#             task_id
#         ):

#             has_permission = any(
#                 permission.name == "update_team_task"
#                 for permission in current_user.role.permissions
#             )

#             if not has_permission:
#                 raise HTTPException(
#                 status_code=403,
#                 detail="Insufficient permissions"
#             )

#             updated_task = crud.update_task(
#                 db,
#                 task_id,
#                 task,
#                 current_user.id
#             )

#             if updated_task == "assigned_user_not_found":
#                 raise HTTPException(
#                     status_code=404,
#                     detail="Assigned user email not found"
#                 )

#             if updated_task == "not_allowed":
#                 raise HTTPException(
#                     status_code=403,
#                     detail="You are not allowed to assign this task to another user"
#                 )

#             return updated_task

#         # -------------------------
#         # Manager updating team task
#         # -------------------------

#         if crud.is_manager_of_task(
#             db,
#             current_user.id,
#             task_id
#         ):

#             has_permission = any(
#                 permission.name == "update_team_task"
#                 for permission in current_user.role.permissions
#             )

#             if not has_permission:
#                 raise HTTPException(
#                     status_code=403,
#                     detail="Insufficient permissions"
#                 )

#             updated_task = crud.update_task_by_manager_or_admin(
#                 db,
#                 db_task,
#                 task,
#                 current_user
#             )

#             if updated_task == "assigned_user_not_found":
#                 raise HTTPException(
#                     status_code=404,
#                     detail="Assigned user email not found"
#                 )

#             if updated_task == "not_allowed":
#                 raise HTTPException(
#                     status_code=403,
#                     detail="You are not allowed to assign this task to that user"
#                 )

#             return updated_task

#         raise HTTPException(
#             status_code=403,
#             detail="You are not allowed to update this task"
#         )

#     # =========================
#     # NORMAL USER
#     # =========================

#     has_permission = any(
#         permission.name == "update_own_task"
#         for permission in current_user.role.permissions
#     )

#     if not has_permission:
#         raise HTTPException(
#             status_code=403,
#             detail="Insufficient permissions"
#         )

#     updated_task = crud.update_task(
#         db,
#         task_id,
#         task,
#         current_user.id
#     )

#     if updated_task == "assigned_user_not_found":
#         raise HTTPException(
#             status_code=404,
#             detail="Assigned user email not found"
#         )

#     if updated_task == "not_allowed":
#         raise HTTPException(
#             status_code=403,
#             detail="You are not allowed to assign this task to another user"
#         )

#     if updated_task is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Task not found"
#         )

#     return updated_task


# # =========================
# # DELETE TASK
# # =========================

# @router.delete("/{task_id}")
# def delete_task(
#     task_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(auth.get_current_user)
# ):

#     db_task = crud.get_task(
#         db,
#         task_id
#     )

#     if db_task is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Task not found"
#         )

#     # =========================
#     # ADMIN
#     # =========================

#     if current_user.role.name == "admin":

#         has_permission = any(
#             permission.name == "delete_any_task"
#             for permission in current_user.role.permissions
#         )

#         if not has_permission:
#             raise HTTPException(
#                 status_code=403,
#                 detail="Insufficient permissions"
#             )

#         db.delete(db_task)
#         db.commit()

#         return {
#             "message": "Task deleted successfully"
#         }

#     # =========================
#     # MANAGER
#     # =========================

#     if current_user.role.name == "manager":

#         # -------------------------
#         # Manager deleting own task
#         # -------------------------

#         if db_task.owner_id == current_user.id:

#             has_permission = any(
#                 permission.name == "delete_own_task"
#                 for permission in current_user.role.permissions
#             )

#             if not has_permission:
#                 raise HTTPException(
#                     status_code=403,
#                     detail="Insufficient permissions"
#                 )

#             db.delete(db_task)
#             db.commit()

#             return {
#                 "message": "Task deleted successfully"
#             }

#         # -------------------------
#         # Manager deleting team task
#         # -------------------------

#         if crud.is_manager_of_task(
#             db,
#             current_user.id,
#             task_id
#         ):

#             has_permission = any(
#                 permission.name == "delete_team_task"
#                 for permission in current_user.role.permissions
#             )

#             if not has_permission:
#                 raise HTTPException(
#                     status_code=403,
#                     detail="Insufficient permissions"
#                 )

#             db.delete(db_task)
#             db.commit()

#             return {
#                 "message": "Task deleted successfully"
#             }

#         raise HTTPException(
#             status_code=403,
#             detail="You are not allowed to delete this task"
#         )

#     # =========================
#     # NORMAL USER
#     # =========================

#     has_permission = any(
#         permission.name == "delete_own_task"
#         for permission in current_user.role.permissions
#     )

#     if not has_permission:
#         raise HTTPException(
#             status_code=403,
#             detail="Insufficient permissions"
#         )

#     deleted_task = crud.delete_task(
#         db,
#         task_id,
#         current_user.id
#     )

#     if deleted_task is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Task not found"
#         )

#     return {
#         "message": "Task deleted successfully"
#     }