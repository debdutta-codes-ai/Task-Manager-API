from datetime import datetime

from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from app import models
from app.schemas import (
    TaskCreate,
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
        .filter(models.Role.name == "user")
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


# =========================================================
# TASK HELPERS
# =========================================================


def get_assigned_user(
    db: Session,
    email: str | None
):
    if email is None:
        return None

    return (
        db.query(models.User)
        .filter(
            models.User.email == email,
            models.User.status == "active"
        )
        .first()
    )


def task_to_response(task):
    """
    Convert database task into the format
    expected by TaskResponse.
    """

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "owner_id": task.owner_id,
        "assigned_to_email": (
            task.assigned_user.email
            if task.assigned_user
            else None
        ),
        "team_id": task.team_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }


# =========================================================
# CREATE TASK
# =========================================================


def create_task(
    db: Session,
    task: TaskCreate,
    owner_id: int,
    current_user
):
    assigned_user = None

    # -----------------------------------------------------
    # Resolve assigned_to_email -> User
    # -----------------------------------------------------

    if task.assigned_to_email is not None:

        assigned_user = get_assigned_user(
            db,
            task.assigned_to_email
        )

        if assigned_user is None:
            return None

    user_permissions = {
        permission.name
        for permission in current_user.role.permissions
    }

    # Route already requires create_task.
    # Keep this check here as an extra CRUD-level safeguard.
    if "create_task" not in user_permissions:
        return "not_allowed"

    # Default assignment is the current user.
    assigned_user_id = current_user.id

    # =====================================================
    # ASSIGNED TO SOMEONE ELSE
    # =====================================================

    if assigned_user is not None:

        # -------------------------------------------------
        # Assigning to self
        # -------------------------------------------------

        if assigned_user.id == current_user.id:

            assigned_user_id = assigned_user.id

        # -------------------------------------------------
        # Assigning to another user
        # -------------------------------------------------

        else:

            # User without team-level or unrestricted
            # assignment capability cannot assign to
            # another user.
            if (
                "update_team_task" not in user_permissions
                and "update_any_task" not in user_permissions
            ):
                return "not_allowed"

            # -------------------------------------------------
            # update_any_task
            #
            # Can assign to any active user.
            # -------------------------------------------------

            if "update_any_task" in user_permissions:

                assigned_user_id = assigned_user.id

            # -------------------------------------------------
            # update_team_task
            #
            # Can assign to a user belonging to a team
            # managed by the current user.
            # -------------------------------------------------

            else:

                member = (
                    db.query(models.TeamMember)
                    .join(
                        models.Team,
                        models.Team.id
                        == models.TeamMember.team_id
                    )
                    .filter(
                        models.Team.manager_id
                        == current_user.id,
                        models.TeamMember.user_id
                        == assigned_user.id
                    )
                    .first()
                )

                if member is None:
                    return "not_allowed"

                assigned_user_id = assigned_user.id

    # =====================================================
    # TEAM VALIDATION
    # =====================================================

    if task.team_id is not None:

        # -------------------------------------------------
        # Users who do not have team-task capability
        # must belong to the specified team.
        # -------------------------------------------------

        if (
            "update_team_task" not in user_permissions
            and "update_any_task" not in user_permissions
        ):

            member = (
                db.query(models.TeamMember)
                .filter(
                    models.TeamMember.team_id == task.team_id,
                    models.TeamMember.user_id == current_user.id
                )
                .first()
            )

            if member is None:
                return "not_allowed"

    # =====================================================
    # CREATE DATABASE TASK
    # =====================================================

    db_task = models.Task(
        title=task.title,
        description=task.description,
        status=task.status,
        owner_id=owner_id,
        assigned_to=assigned_user_id,
        team_id=task.team_id
    )

    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return task_to_response(db_task)

# =========================================================
# GET TASKS
# =========================================================


def get_tasks(
    db: Session,
    current_user
):
    user_permissions = {
        permission.name
        for permission in current_user.role.permissions
    }

    # =====================================================
    # READ ALL TASKS
    # =====================================================

    if "read_all_tasks" in user_permissions:

        tasks = (
            db.query(models.Task)
            .all()
        )

        return [
            task_to_response(task)
            for task in tasks
        ]

    # =====================================================
    # READ TEAM TASKS
    # =====================================================

    if "read_team_tasks" in user_permissions:

        managed_team_ids = (
            db.query(models.Team.id)
            .filter(
                models.Team.manager_id == current_user.id
            )
            .subquery()
        )

        tasks = (
            db.query(models.Task)
            .filter(
                (models.Task.owner_id == current_user.id)
                |
                (
                    models.Task.team_id.in_(
                        managed_team_ids
                    )
                )
            )
            .all()
        )

        return [
            task_to_response(task)
            for task in tasks
        ]

    # =====================================================
    # READ OWN TASKS
    # =====================================================

    if "read_own_task" in user_permissions:

        tasks = (
            db.query(models.Task)
            .filter(
                models.Task.owner_id == current_user.id
            )
            .all()
        )

        return [
            task_to_response(task)
            for task in tasks
        ]

    return []


# =========================================================
# GET ONE TASK
# =========================================================


def get_task(
    db: Session,
    task_id: int
):
    return (
        db.query(models.Task)
        .filter(
            models.Task.id == task_id
        )
        .first()
    )


# =========================================================
# UPDATE TASK
# =========================================================


def update_task(
    db: Session,
    task_id: int,
    task: TaskCreate,
    owner_id: int
):
    db_task = (
        db.query(models.Task)
        .filter(
            models.Task.id == task_id,
            models.Task.owner_id == owner_id
        )
        .first()
    )

    if db_task is None:
        return None

    assigned_user = None

    # -----------------------------------------------------
    # Resolve assigned_to_email -> User
    # -----------------------------------------------------

    if task.assigned_to_email is not None:

        assigned_user = get_assigned_user(
            db,
            task.assigned_to_email
        )

        if assigned_user is None:
            return "assigned_user_not_found"

        # Own-task update can only assign the task
        # to the owner themselves.
        if assigned_user.id != owner_id:
            return "not_allowed"

    # -----------------------------------------------------
    # Update task
    # -----------------------------------------------------

    db_task.title = task.title
    db_task.description = task.description
    db_task.status = task.status

    db_task.assigned_to = (
        assigned_user.id
        if assigned_user
        else owner_id
    )

    db_task.team_id = task.team_id

    db.commit()
    db.refresh(db_task)

    return task_to_response(db_task)


# =========================================================
# UPDATE TASK
# ADMIN / MANAGER / PERMISSION-BASED
# =========================================================


def update_task_by_manager_or_admin(
    db: Session,
    db_task,
    task: TaskCreate,
    current_user
):
    assigned_user = None

    user_permissions = {
        permission.name
        for permission in current_user.role.permissions
    }

    # -----------------------------------------------------
    # Resolve assigned_to_email -> User
    # -----------------------------------------------------

    if task.assigned_to_email is not None:

        assigned_user = get_assigned_user(
            db,
            task.assigned_to_email
        )

        if assigned_user is None:
            return "assigned_user_not_found"

    # =====================================================
    # TEAM VALIDATION
    # =====================================================

    if task.team_id is not None:

        # -------------------------------------------------
        # Admin / unrestricted users
        # -------------------------------------------------

        if "update_any_task" in user_permissions:

            team = (
                db.query(models.Team)
                .filter(
                    models.Team.id == task.team_id
                )
                .first()
            )

            if team is None:
                return "team_not_found"

        # -------------------------------------------------
        # Manager / team-scoped users
        # -------------------------------------------------

        elif "update_team_task" in user_permissions:

            team = (
                db.query(models.Team)
                .filter(
                    models.Team.id == task.team_id,
                    models.Team.manager_id == current_user.id
                )
                .first()
            )

            if team is None:
                return "not_allowed"

        # -------------------------------------------------
        # No team-management permission
        # -------------------------------------------------

        else:
            return "not_allowed"

    # =====================================================
    # ASSIGNMENT
    # =====================================================

    if assigned_user is not None:

        # -------------------------------------------------
        # Assigning to another user
        # -------------------------------------------------

        if assigned_user.id != current_user.id:

            # -------------------------------------------------
            # update_any_task
            #
            # Unrestricted assignment.
            # -------------------------------------------------

            if "update_any_task" in user_permissions:

                assigned_user_id = assigned_user.id

            # -------------------------------------------------
            # update_team_task
            #
            # Assignment must be to a member of a team
            # managed by the current user.
            # -------------------------------------------------

            elif "update_team_task" in user_permissions:

                member = (
                    db.query(models.TeamMember)
                    .join(
                        models.Team,
                        models.Team.id
                        == models.TeamMember.team_id
                    )
                    .filter(
                        models.Team.manager_id
                        == current_user.id,
                        models.TeamMember.user_id
                        == assigned_user.id
                    )
                    .first()
                )

                if member is None:
                    return "not_allowed"

                assigned_user_id = assigned_user.id

            else:
                return "not_allowed"

        # -------------------------------------------------
        # Assigning to themselves
        # -------------------------------------------------

        else:

            assigned_user_id = assigned_user.id

    # =====================================================
    # NO ASSIGNED EMAIL PROVIDED
    # =====================================================

    else:

        # Preserve the existing assignment when no new
        # email is supplied.
        assigned_user_id = db_task.assigned_to

        if assigned_user_id is None:
            assigned_user_id = current_user.id

    # =====================================================
    # UPDATE DATABASE TASK
    # =====================================================

    db_task.title = task.title
    db_task.description = task.description
    db_task.status = task.status
    db_task.assigned_to = assigned_user_id
    db_task.team_id = task.team_id

    db.commit()
    db.refresh(db_task)

    return task_to_response(db_task)


# =========================================================
# DELETE TASK
# =========================================================


def delete_task(
    db: Session,
    task_id: int,
    owner_id: int
):
    db_task = (
        db.query(models.Task)
        .filter(
            models.Task.id == task_id,
            models.Task.owner_id == owner_id
        )
        .first()
    )

    if db_task is None:
        return None

    db.delete(db_task)
    db.commit()

    return task_to_response(db_task)


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


# =========================================================
# MANAGER / TASK HELPER
# =========================================================


def is_manager_of_task(
    db: Session,
    manager_id: int,
    task_id: int
):
    task = (
        db.query(models.Task)
        .filter(
            models.Task.id == task_id
        )
        .first()
    )

    if task is None:
        return None

    if task.team_id is None:
        return False

    team = (
        db.query(models.Team)
        .filter(
            models.Team.id == task.team_id,
            models.Team.manager_id == manager_id
        )
        .first()
    )

    return team is not None


# =========================================================
# TEAM UPDATE AND DELETE
# =========================================================


def update_team(
    db: Session,
    team_id: int,
    team_data
):
    db_team = (
        db.query(models.Team)
        .filter(
            models.Team.id == team_id
        )
        .first()
    )

    if db_team is None:
        return None

    manager = (
        db.query(models.User)
        .filter(
            models.User.id == team_data.manager_id,
            models.User.status == "active"
        )
        .first()
    )

    if manager is None:
        return "manager_not_found"

    if manager.role is None or manager.role.name != "manager":
        return "not_manager"

    db_team.name = team_data.name
    db_team.manager_id = team_data.manager_id

    db.commit()
    db.refresh(db_team)

    return db_team


def delete_team(
    db: Session,
    team_id: int
):
    db_team = (
        db.query(models.Team)
        .filter(
            models.Team.id == team_id
        )
        .first()
    )

    if db_team is None:
        return None

    # Check whether the team has members
    member = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id
        )
        .first()
    )

    if member is not None:
        return "has_members"

    # Check whether the team has tasks
    task = (
        db.query(models.Task)
        .filter(
            models.Task.team_id == team_id
        )
        .first()
    )

    if task is not None:
        return "has_tasks"

    db.delete(db_team)
    db.commit()

    return db_team
















# from datetime import datetime

# from sqlalchemy.orm import Session
# from pwdlib import PasswordHash

# from app import models
# from app.schemas import (
#     TaskCreate,
#     UserCreate,
#     AdminUserCreate,
#     AdminUserUpdate
# )


# password_hash = PasswordHash.recommended()


# # =========================================================
# # USER CRUD
# # =========================================================

# def create_user(
#     db: Session,
#     user: UserCreate
# ):
#     hashed_password = password_hash.hash(
#         user.password
#     )

#     # Public registration always gets
#     # the normal "user" role
#     default_role = (
#         db.query(models.Role)
#         .filter(models.Role.name == "user")
#         .first()
#     )

#     if default_role is None:
#         return None

#     db_user = models.User(
#         username=user.username,
#         email=user.email,
#         password_hash=hashed_password,
#         role_id=default_role.id,
#         status="active"
#     )

#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)

#     return db_user


# def get_user_by_username(
#     db: Session,
#     username: str
# ):
#     return (
#         db.query(models.User)
#         .filter(
#             models.User.username == username
#         )
#         .first()
#     )


# def get_user_by_email(
#     db: Session,
#     email: str
# ):
#     return (
#         db.query(models.User)
#         .filter(
#             models.User.email == email
#         )
#         .first()
#     )


# # =========================================================
# # ADMIN USER CRUD
# # =========================================================

# def create_user_by_admin(
#     db: Session,
#     user: AdminUserCreate,
#     admin_id: int
# ):
#     # Check that the role exists
#     role = (
#         db.query(models.Role)
#         .filter(
#             models.Role.id == user.role_id
#         )
#         .first()
#     )

#     if role is None:
#         return None

#     hashed_password = password_hash.hash(
#         user.password
#     )

#     db_user = models.User(
#         username=user.username,
#         email=user.email,
#         password_hash=hashed_password,
#         role_id=role.id,
#         status="active",
#         created_by=admin_id
#     )

#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)

#     return db_user


# def update_user_by_admin(
#     db: Session,
#     user_id: int,
#     user: AdminUserUpdate
# ):
#     db_user = (
#         db.query(models.User)
#         .filter(
#             models.User.id == user_id
#         )
#         .first()
#     )

#     if db_user is None:
#         return None

#     # Check that the new role exists
#     role = (
#         db.query(models.Role)
#         .filter(
#             models.Role.id == user.role_id
#         )
#         .first()
#     )

#     if role is None:
#         return None

#     db_user.username = user.username
#     db_user.email = user.email
#     db_user.role_id = role.id

#     db.commit()
#     db.refresh(db_user)

#     return db_user


# def delete_user_by_admin(
#     db: Session,
#     user_id: int,
#     admin_id: int
# ):
#     db_user = (
#         db.query(models.User)
#         .filter(
#             models.User.id == user_id
#         )
#         .first()
#     )

#     if db_user is None:
#         return None

#     db_user.status = "inactive"
#     db_user.deleted_at = datetime.utcnow()
#     db_user.deleted_by = admin_id

#     db.commit()
#     db.refresh(db_user)

#     return db_user


# # =========================================================
# # TASK HELPERS
# # =========================================================

# def get_assigned_user(
#     db: Session,
#     email: str | None
# ):
#     if email is None:
#         return None

#     return (
#         db.query(models.User)
#         .filter(
#             models.User.email == email,
#             models.User.status == "active"
#         )
#         .first()
#     )


# def task_to_response(task):
#     """
#     Convert database task into the format
#     expected by TaskResponse.
#     """

#     return {
#         "id": task.id,
#         "title": task.title,
#         "description": task.description,
#         "status": task.status,
#         "owner_id": task.owner_id,
#         "assigned_to_email": (
#             task.assigned_user.email
#             if task.assigned_user
#             else None
#         ),
#         "team_id": task.team_id,
#         "created_at": task.created_at,
#         "updated_at": task.updated_at
#     }


# # =========================================================
# # CREATE TASK
# # =========================================================

# def create_task(
#     db: Session,
#     task: TaskCreate,
#     owner_id: int,
#     current_user
# ):
#     assigned_user = None

#     # -----------------------------------------------------
#     # Resolve assigned_to_email -> User
#     # -----------------------------------------------------

#     if task.assigned_to_email is not None:

#         assigned_user = get_assigned_user(
#             db,
#             task.assigned_to_email
#         )

#         if assigned_user is None:
#             return None

#     user_permissions = {
#         permission.name
#         for permission in current_user.role.permissions
#     }

#     # Route already requires create_task.
#     # Keep this check here as an extra CRUD-level safeguard.
#     if "create_task" not in user_permissions:
#         return "not_allowed"

#     # Default assignment is the current user.
#     assigned_user_id = current_user.id

#     # =====================================================
#     # ASSIGNED TO SOMEONE ELSE
#     # =====================================================

#     if assigned_user is not None:

#         # -------------------------------------------------
#         # Assigning to self
#         # -------------------------------------------------

#         if assigned_user.id == current_user.id:

#             assigned_user_id = assigned_user.id

#         # -------------------------------------------------
#         # Assigning to another user
#         # -------------------------------------------------

#         else:

#             # User without team-level or unrestricted
#             # assignment capability cannot assign to
#             # another user.
#             if (
#                 "update_team_task" not in user_permissions
#                 and "update_any_task" not in user_permissions
#             ):
#                 return "not_allowed"

#             # -------------------------------------------------
#             # update_any_task
#             #
#             # Can assign to any active user.
#             # -------------------------------------------------

#             if "update_any_task" in user_permissions:

#                 assigned_user_id = assigned_user.id

#             # -------------------------------------------------
#             # update_team_task
#             #
#             # Can assign to a user belonging to a team
#             # managed by the current user.
#             # -------------------------------------------------

#             else:

#                 member = (
#                     db.query(models.TeamMember)
#                     .join(
#                         models.Team,
#                         models.Team.id
#                         == models.TeamMember.team_id
#                     )
#                     .filter(
#                         models.Team.manager_id
#                         == current_user.id,
#                         models.TeamMember.user_id
#                         == assigned_user.id
#                     )
#                     .first()
#                 )

#                 if member is None:
#                     return "not_allowed"

#                 assigned_user_id = assigned_user.id

#     # =====================================================
#     # TEAM VALIDATION
#     # =====================================================

#     if task.team_id is not None:

#         # -------------------------------------------------
#         # Users who do not have team-task capability
#         # must belong to the specified team.
#         # -------------------------------------------------

#         if (
#             "update_team_task" not in user_permissions
#             and "update_any_task" not in user_permissions
#         ):

#             member = (
#                 db.query(models.TeamMember)
#                 .filter(
#                     models.TeamMember.team_id == task.team_id,
#                     models.TeamMember.user_id == current_user.id
#                 )
#                 .first()
#             )

#             if member is None:
#                 return "not_allowed"

#     # =====================================================
#     # CREATE DATABASE TASK
#     # =====================================================

#     db_task = models.Task(
#         title=task.title,
#         description=task.description,
#         status=task.status,
#         owner_id=owner_id,
#         assigned_to=assigned_user_id,
#         team_id=task.team_id
#     )

#     db.add(db_task)
#     db.commit()
#     db.refresh(db_task)

#     return db_task


# # =========================================================
# # GET TASKS
# # =========================================================

# def get_tasks(
#     db: Session,
#     current_user
# ):
#     user_permissions = {
#         permission.name
#         for permission in current_user.role.permissions
#     }

#     # =====================================================
#     # READ ALL TASKS
#     # =====================================================

#     if "read_all_tasks" in user_permissions:

#         return (
#             db.query(models.Task)
#             .all()
#         )

#     # =====================================================
#     # READ TEAM TASKS
#     # =====================================================

#     if "read_team_tasks" in user_permissions:

#         managed_team_ids = (
#             db.query(models.Team.id)
#             .filter(
#                 models.Team.manager_id == current_user.id
#             )
#             .subquery()
#         )

#         return (
#             db.query(models.Task)
#             .filter(
#                 (models.Task.owner_id == current_user.id)
#                 |
#                 (
#                     models.Task.team_id.in_(
#                         managed_team_ids
#                     )
#                 )
#             )
#             .all()
#         )

#     # =====================================================
#     # READ OWN TASKS
#     # =====================================================

#     if "read_own_task" in user_permissions:

#         return (
#             db.query(models.Task)
#             .filter(
#                 models.Task.owner_id == current_user.id
#             )
#             .all()
#         )

#     return []


# # =========================================================
# # GET ONE TASK
# # =========================================================

# def get_task(
#     db: Session,
#     task_id: int
# ):
#     return (
#         db.query(models.Task)
#         .filter(
#             models.Task.id == task_id
#         )
#         .first()
#     )


# # =========================================================
# # UPDATE TASK
# # =========================================================

# def update_task(
#     db: Session,
#     task_id: int,
#     task: TaskCreate,
#     owner_id: int
# ):
#     db_task = (
#         db.query(models.Task)
#         .filter(
#             models.Task.id == task_id,
#             models.Task.owner_id == owner_id
#         )
#         .first()
#     )

#     if db_task is None:
#         return None

#     assigned_user = None

#     # -----------------------------------------------------
#     # Resolve assigned_to_email -> User
#     # -----------------------------------------------------

#     if task.assigned_to_email is not None:

#         assigned_user = get_assigned_user(
#             db,
#             task.assigned_to_email
#         )

#         if assigned_user is None:
#             return "assigned_user_not_found"

#         # Own-task update can only assign the task
#         # to the owner themselves.
#         if assigned_user.id != owner_id:
#             return "not_allowed"

#     # -----------------------------------------------------
#     # Update task
#     # -----------------------------------------------------

#     db_task.title = task.title
#     db_task.description = task.description
#     db_task.status = task.status

#     db_task.assigned_to = (
#         assigned_user.id
#         if assigned_user
#         else owner_id
#     )

#     db_task.team_id = task.team_id

#     db.commit()
#     db.refresh(db_task)

#     return db_task


# # =========================================================
# # UPDATE TASK
# # ADMIN / MANAGER / PERMISSION-BASED
# # =========================================================

# def update_task_by_manager_or_admin(
#     db: Session,
#     db_task,
#     task: TaskCreate,
#     current_user
# ):
#     assigned_user = None

#     user_permissions = {
#         permission.name
#         for permission in current_user.role.permissions
#     }

#     # -----------------------------------------------------
#     # Resolve assigned_to_email -> User
#     # -----------------------------------------------------

#     if task.assigned_to_email is not None:

#         assigned_user = get_assigned_user(
#             db,
#             task.assigned_to_email
#         )

#         if assigned_user is None:
#             return "assigned_user_not_found"

#     # =====================================================
#     # ASSIGNMENT
#     # =====================================================

#     if assigned_user is not None:

#         # -------------------------------------------------
#         # Assigning to another user
#         # -------------------------------------------------

#         if assigned_user.id != current_user.id:

#             # -------------------------------------------------
#             # update_any_task
#             #
#             # Unrestricted assignment.
#             # -------------------------------------------------

#             if "update_any_task" in user_permissions:

#                 assigned_user_id = assigned_user.id

#             # -------------------------------------------------
#             # update_team_task
#             #
#             # Assignment must be to a member of a team
#             # managed by the current user.
#             # -------------------------------------------------

#             elif "update_team_task" in user_permissions:

#                 member = (
#                     db.query(models.TeamMember)
#                     .join(
#                         models.Team,
#                         models.Team.id
#                         == models.TeamMember.team_id
#                     )
#                     .filter(
#                         models.Team.manager_id
#                         == current_user.id,
#                         models.TeamMember.user_id
#                         == assigned_user.id
#                     )
#                     .first()
#                 )

#                 if member is None:
#                     return "not_allowed"

#                 assigned_user_id = assigned_user.id

#             else:
#                 return "not_allowed"

#         # -------------------------------------------------
#         # Assigning to themselves
#         # -------------------------------------------------

#         else:
#             assigned_user_id = assigned_user.id

#     # =====================================================
#     # NO ASSIGNED EMAIL PROVIDED
#     # =====================================================

#     else:
#         assigned_user_id = current_user.id

#     # =====================================================
#     # UPDATE DATABASE TASK
#     # =====================================================

#     db_task.title = task.title
#     db_task.description = task.description
#     db_task.status = task.status
#     db_task.assigned_to = assigned_user_id
#     db_task.team_id = task.team_id

#     db.commit()
#     db.refresh(db_task)

#     return db_task


# # =========================================================
# # DELETE TASK
# # =========================================================

# def delete_task(
#     db: Session,
#     task_id: int,
#     owner_id: int
# ):
#     db_task = (
#         db.query(models.Task)
#         .filter(
#             models.Task.id == task_id,
#             models.Task.owner_id == owner_id
#         )
#         .first()
#     )

#     if db_task is None:
#         return None

#     db.delete(db_task)
#     db.commit()

#     return db_task


# # =========================================================
# # CREATE ROLE
# # =========================================================

# def create_role(
#     db: Session,
#     role_name: str,
#     description: str | None = None
# ):
#     existing_role = (
#         db.query(models.Role)
#         .filter(
#             models.Role.name == role_name
#         )
#         .first()
#     )

#     if existing_role:
#         return None

#     db_role = models.Role(
#         name=role_name,
#         description=description
#     )

#     db.add(db_role)
#     db.commit()
#     db.refresh(db_role)

#     return db_role


# # =========================================================
# # UPDATE ROLE
# # =========================================================

# def update_role(
#     db: Session,
#     role_id: int,
#     role_data
# ):
#     db_role = (
#         db.query(models.Role)
#         .filter(
#             models.Role.id == role_id
#         )
#         .first()
#     )

#     if db_role is None:
#         return None

#     existing_role = (
#         db.query(models.Role)
#         .filter(
#             models.Role.name == role_data.name,
#             models.Role.id != role_id
#         )
#         .first()
#     )

#     if existing_role:
#         return "role_exists"

#     db_role.name = role_data.name
#     db_role.description = role_data.description

#     db.commit()
#     db.refresh(db_role)

#     return db_role


# # =========================================================
# # DELETE ROLE
# # =========================================================

# def delete_role(
#     db: Session,
#     role_id: int
# ):
#     db_role = (
#         db.query(models.Role)
#         .filter(
#             models.Role.id == role_id
#         )
#         .first()
#     )

#     if db_role is None:
#         return None

#     # Protect default roles
#     if db_role.name in ["admin", "manager", "user"]:
#         return "default_role"

#     # Check whether users are using this role
#     user = (
#         db.query(models.User)
#         .filter(
#             models.User.role_id == role_id,
#             models.User.status == "active"
#         )
#         .first()
#     )

#     if user is not None:
#         return "role_in_use"

#     db.delete(db_role)
#     db.commit()

#     return db_role


# # =========================================================
# # MANAGER / TASK HELPER
# # =========================================================

# def is_manager_of_task(
#     db: Session,
#     manager_id: int,
#     task_id: int
# ):
#     task = (
#         db.query(models.Task)
#         .filter(
#             models.Task.id == task_id
#         )
#         .first()
#     )

#     if task is None:
#         return None

#     if task.team_id is None:
#         return False

#     team = (
#         db.query(models.Team)
#         .filter(
#             models.Team.id == task.team_id,
#             models.Team.manager_id == manager_id
#         )
#         .first()
#     )

#     return team is not None


# # =========================================================
# # TEAM UPDATE AND DELETE
# # =========================================================

# def update_team(
#     db: Session,
#     team_id: int,
#     team_data
# ):
#     db_team = (
#         db.query(models.Team)
#         .filter(
#             models.Team.id == team_id
#         )
#         .first()
#     )

#     if db_team is None:
#         return None

#     manager = (
#         db.query(models.User)
#         .filter(
#             models.User.id == team_data.manager_id,
#             models.User.status == "active"
#         )
#         .first()
#     )

#     if manager is None:
#         return "manager_not_found"

#     if manager.role is None or manager.role.name != "manager":
#         return "not_manager"

#     db_team.name = team_data.name
#     db_team.manager_id = team_data.manager_id

#     db.commit()
#     db.refresh(db_team)

#     return db_team


# def delete_team(
#     db: Session,
#     team_id: int
# ):
#     db_team = (
#         db.query(models.Team)
#         .filter(
#             models.Team.id == team_id
#         )
#         .first()
#     )

#     if db_team is None:
#         return None

#     # Check whether the team has members
#     member = (
#         db.query(models.TeamMember)
#         .filter(
#             models.TeamMember.team_id == team_id
#         )
#         .first()
#     )

#     if member is not None:
#         return "has_members"

#     # Check whether the team has tasks
#     task = (
#         db.query(models.Task)
#         .filter(
#             models.Task.team_id == team_id
#         )
#         .first()
#     )

#     if task is not None:
#         return "has_tasks"

#     db.delete(db_team)
#     db.commit()

#     return db_team