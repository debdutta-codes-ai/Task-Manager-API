from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, models, crud
from app.database import get_db
from app.schemas import TeamCreate, TeamResponse, TeamMemberAdd, TeamUpdate


router = APIRouter(prefix="/teams")


# =========================
# Create Team
# Admin Only
# =========================

@router.post(
    "/",
    status_code=201,
    response_model=TeamResponse
)
def create_team(
    team: TeamCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_roles("admin"))
):
    manager = (
        db.query(models.User)
        .filter(models.User.id == team.manager_id)
        .first()
    )

    if manager is None:
        raise HTTPException(
            status_code=404,
            detail="Manager not found"
        )

    # Check the user's dynamic role
    if manager.role is None or manager.role.name != "manager":
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a manager"
        )

    db_team = models.Team(
        name=team.name,
        manager_id=team.manager_id
    )

    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    return db_team


# =========================
# Add Team Member
# Admin Only
# =========================

@router.post("/{team_id}/members")
def add_team_member(
    team_id: int,
    member: TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user=Depends(auth.require_roles("admin"))
):
    team = (
        db.query(models.Team)
        .filter(models.Team.id == team_id)
        .first()
    )

    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    user = (
        db.query(models.User)
        .filter(models.User.id == member.user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Only users with the "user" role can be team members
    if user.role is None or user.role.name != "user":
        raise HTTPException(
            status_code=400,
            detail="Only users can be added as team members"
        )

    existing_member = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == member.user_id
        )
        .first()
    )

    if existing_member:
        raise HTTPException(
            status_code=409,
            detail="User is already a team member"
        )

    team_member = models.TeamMember(
        team_id=team_id,
        user_id=member.user_id
    )

    db.add(team_member)
    db.commit()
    db.refresh(team_member)

    return {
        "message": "User added to team successfully"
    }

# update team (admin only)
@router.put(
    "/{team_id}",
    response_model=TeamResponse
)
def update_team(
    team_id: int,
    team: TeamUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_roles("admin")
    )
):
    updated_team = crud.update_team(
        db,
        team_id,
        team
    )

    if updated_team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    if updated_team == "manager_not_found":
        raise HTTPException(
            status_code=404,
            detail="Manager not found"
        )

    if updated_team == "not_manager":
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a manager"
        )

    return updated_team

# delete team (admin only)
@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        auth.require_roles("admin")
    )
):
    deleted_team = crud.delete_team(
        db,
        team_id
    )

    if deleted_team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    if deleted_team == "has_members":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete team because it has members"
        )

    if deleted_team == "has_tasks":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete team because it has tasks"
        )

    return {
        "message": "Team deleted successfully"
    }