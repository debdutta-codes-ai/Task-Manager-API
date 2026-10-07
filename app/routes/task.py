from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, crud
from app.database import get_db
from app.schemas import TaskCreate, TaskResponse


router = APIRouter(prefix="/tasks")


# =========================
# CREATE TASK
# =========================

@router.post(
    "/",
    status_code=201,
    response_model=TaskResponse
)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
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


# =========================
# READ ALL TASKS
# =========================

@router.get(
    "/",
    response_model=list[TaskResponse]
)
def get_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    return crud.get_tasks(
        db,
        current_user
    )


# =========================
# READ ONE TASK
# =========================

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

    # Admin can read any task
    if current_user.role.name == "admin":
        return task

    # User / Manager can read their own task
    if task.owner_id == current_user.id:
        return task

    # Manager can read tasks belonging to
    # teams they manage
    if current_user.role.name == "manager":

        if crud.is_manager_of_task(
            db,
            current_user.id,
            task_id
        ):
            return task

    raise HTTPException(
        status_code=403,
        detail="You are not allowed to access this task"
    )


# =========================
# UPDATE TASK
# =========================

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

    # =========================
    # ADMIN
    # =========================

    if current_user.role.name == "admin":

        db_task = crud.get_task(
            db,
            task_id
        )

        if db_task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )

        updated_task = (
            crud.update_task_by_manager_or_admin(
                db,
                db_task,
                task,
                current_user
            )
        )

        if updated_task == "assigned_user_not_found":
            raise HTTPException(
                status_code=404,
                detail="Assigned user email not found"
            )

        return updated_task


    # =========================
    # MANAGER
    # =========================

    if current_user.role.name == "manager":

        db_task = crud.get_task(
            db,
            task_id
        )

        if db_task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )

        # Manager can only update
        # their own team's tasks
        if not crud.is_manager_of_task(
            db,
            current_user.id,
            task_id
        ):
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to update this task"
            )

        updated_task = (
            crud.update_task_by_manager_or_admin(
                db,
                db_task,
                task,
                current_user
            )
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


    # =========================
    # NORMAL USER
    # =========================

    # User can update only their own task
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


# =========================
# DELETE TASK
# =========================

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):

    # =========================
    # ADMIN
    # =========================

    if current_user.role.name == "admin":

        db_task = crud.get_task(
            db,
            task_id
        )

        if db_task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )

        db.delete(db_task)
        db.commit()

        return {
            "message": "Task deleted successfully"
        }


    # =========================
    # MANAGER
    # =========================

    if current_user.role.name == "manager":

        db_task = crud.get_task(
            db,
            task_id
        )

        if db_task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )

        # Manager can delete only
        # tasks belonging to their team
        if not crud.is_manager_of_task(
            db,
            current_user.id,
            task_id
        ):
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to delete this task"
            )

        db.delete(db_task)
        db.commit()

        return {
            "message": "Task deleted successfully"
        }


    # =========================
    # NORMAL USER
    # =========================

    deleted_task = crud.delete_task(
        db,
        task_id,
        current_user.id
    )

    if deleted_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "message": "Task deleted successfully"
    }