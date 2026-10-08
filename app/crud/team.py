from sqlalchemy.orm import Session

from app import models


# =========================================================
# TEAM UPDATE
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


# =========================================================
# TEAM DELETE
# =========================================================


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