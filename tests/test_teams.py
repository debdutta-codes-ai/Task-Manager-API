def test_admin_can_create_team(client, test_db, admin_headers):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    response = client.post(
        "/teams/",
        headers=admin_headers,
        json={
            "name": "Admin Created Team",
            "manager_id": manager.id,
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Admin Created Team"

def test_admin_can_add_team_member(client, admin_headers, test_db):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    team = models.Team(
        name="Member Test Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    response = client.post(
        f"/teams/{team.id}/members",
        headers=admin_headers,
        json={"user_id": user.id},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "User added to team successfully"

    membership = (
        test_db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team.id,
            models.TeamMember.user_id == user.id,
        )
        .first()
    )
    assert membership is not None

def test_admin_gets_404_when_adding_nonexistent_user(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Missing User Test Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    response = client.post(
        f"/teams/{team.id}/members",
        headers=admin_headers,
        json={"user_id": 99999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

# Test that a manager cannot assign a task to a team
# that the assigned user does not belong to.
def test_manager_cannot_assign_task_to_wrong_team(client, test_db):
    from app import models

    # Find the test manager and regular user.
    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Create two teams managed by the same manager.
    team_a = models.Team(
        name="Team A",
        manager_id=manager.id,
    )
    team_b = models.Team(
        name="Team B",
        manager_id=manager.id,
    )
    test_db.add_all([team_a, team_b])
    test_db.commit()
    test_db.refresh(team_a)
    test_db.refresh(team_b)

    # Add the user to Team A only.
    membership = models.TeamMember(
        team_id=team_a.id,
        user_id=user.id,
    )
    test_db.add(membership)
    test_db.commit()

    # Log in as the manager.
    login_response = client.post(
        "/users/login",
        data={
            "username": "testmanager",
            "password": "TestManager123!",
        },
    )
    assert login_response.status_code == 200

    manager_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Try assigning the user to a task for Team B,
    # even though the user belongs only to Team A.
    response = client.post(
        "/tasks/",
        headers=manager_headers,
        json={
            "title": "Wrong team assignment",
            "description": "This assignment should be rejected",
            "status": "pending",
            "assigned_to_email": user.email,
            "team_id": team_b.id,
        },
    )

    # The API should forbid this cross-team assignment.
    assert response.status_code == 403



def test_manager_can_assign_task_to_user_in_their_team(client, test_db):
    from app import models

    # Find the test manager and regular user.
    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Create a team managed by this manager.
    team = models.Team(
        name="Manager Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add the regular user to the team.
    membership = models.TeamMember(
        team_id=team.id,
        user_id=user.id,
    )
    test_db.add(membership)
    test_db.commit()

    # Log in as the manager.
    login_response = client.post(
        "/users/login",
        data={
            "username": "testmanager",
            "password": "TestManager123!",
        },
    )
    assert login_response.status_code == 200

    manager_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Assign a task to the user who belongs to the selected team.
    response = client.post(
        "/tasks/",
        headers=manager_headers,
        json={
            "title": "Valid team assignment",
            "description": "The user belongs to this team",
            "status": "pending",
            "assigned_to_email": user.email,
            "team_id": team.id,
        },
    )

    assert response.status_code == 201


def test_regular_user_cannot_create_team(client, test_db):
    from app import models

    # Find the regular test user.
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Log in as the regular user.
    login_response = client.post(
        "/users/login",
        data={
            "username": "testuser",
            "password": "TestUser123!",
        },
    )
    assert login_response.status_code == 200

    user_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Try to create a team as a regular user.
    response = client.post(
        "/teams/",
        headers=user_headers,
        json={
            "name": "Unauthorized Team",
            "manager_id": user.id,
        },
    )

    # A regular user should not have permission to create a team.
    assert response.status_code == 403

def test_manager_cannot_create_team(client):
    login_response = client.post(
        "/users/login",
        data={
            "username": "testmanager",
            "password": "TestManager123!"
        }
    )

    assert login_response.status_code == 200

    manager_headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }

    response = client.post(
        "/teams/",
        headers=manager_headers,
        json={"name": "Manager Created Team"}
    )

    assert response.status_code == 403

def test_admin_can_list_teams(client, admin_headers, test_db):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Test Listing Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()

    response = client.get(
        "/teams/",
        headers=admin_headers,
    )

    assert response.status_code == 200

    team_names = [item["name"] for item in response.json()]
    assert "Test Listing Team" in team_names

def test_admin_can_get_existing_team(client, admin_headers, test_db):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Team Detail Test",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    response = client.get(
        f"/teams/{team.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == team.id
    assert response.json()["name"] == "Team Detail Test"

def test_admin_gets_404_for_missing_team(client, admin_headers):
    response = client.get(
        "/teams/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Team not found"

def test_admin_cannot_add_duplicate_team_member(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    team = models.Team(
        name="Duplicate Member Test Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add the user to the team for the first time.
    first_response = client.post(
        f"/teams/{team.id}/members",
        headers=admin_headers,
        json={"user_id": user.id},
    )

    assert first_response.status_code == 200

    # Try adding the same user to the same team again.
    second_response = client.post(
        f"/teams/{team.id}/members",
        headers=admin_headers,
        json={"user_id": user.id},
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "User is already a team member"
    )

def test_unauthenticated_user_cannot_list_teams(client):
    response = client.get("/teams/")

    assert response.status_code == 401


def test_regular_user_cannot_get_team(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Protected Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    login_response = client.post(
        "/users/login",
        data={
            "username": "testuser",
            "password": "TestUser123!",
        },
    )
    assert login_response.status_code == 200

    user_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    response = client.get(
        f"/teams/{team.id}",
        headers=user_headers,
    )

    assert response.status_code == 403


def test_admin_gets_404_when_adding_member_to_missing_team(
    client,
    admin_headers,
    test_db,
):
    from app import models

    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    response = client.post(
        "/teams/99999/members",
        headers=admin_headers,
        json={"user_id": user.id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Team not found"


def test_admin_cannot_add_manager_as_team_member(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Manager Membership Test",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    response = client.post(
        f"/teams/{team.id}/members",
        headers=admin_headers,
        json={"user_id": manager.id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only users can be added as team members"
    )


def test_admin_gets_404_when_creating_team_with_missing_manager(
    client,
    admin_headers,
):
    response = client.post(
        "/teams/",
        headers=admin_headers,
        json={
            "name": "Missing Manager Team",
            "manager_id": 99999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Manager not found"


def test_admin_cannot_create_team_with_regular_user_as_manager(
    client,
    admin_headers,
    test_db,
):
    from app import models

    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    response = client.post(
        "/teams/",
        headers=admin_headers,
        json={
            "name": "Invalid Manager Team",
            "manager_id": user.id,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Selected user is not a manager"
    )


def test_admin_can_update_existing_team(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Team Before Update",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    response = client.put(
        f"/teams/{team.id}",
        headers=admin_headers,
        json={
            "name": "Team After Update",
            "manager_id": manager.id,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Team After Update"


def test_admin_gets_404_when_updating_missing_team(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    response = client.put(
        "/teams/99999",
        headers=admin_headers,
        json={
            "name": "Missing Team Update",
            "manager_id": manager.id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Team not found"

def test_admin_cannot_delete_team_with_tasks(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Team With Task",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    task = models.Task(
        title="Task Preventing Team Deletion",
        description="This task should prevent team deletion",
        owner_id=manager.id,
        team_id=team.id,
    )
    test_db.add(task)
    test_db.commit()

    response = client.delete(
        f"/teams/{team.id}",
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot delete team because it has tasks"
    )

    # Confirm the team still exists
    existing_team = (
        test_db.query(models.Team)
        .filter(models.Team.id == team.id)
        .first()
    )
    assert existing_team is not None

def test_admin_can_delete_empty_team(
    client,
    admin_headers,
    test_db,
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Empty Team To Delete",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    response = client.delete(
        f"/teams/{team.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Team deleted successfully"

def test_manager_can_read_own_team(client, test_db):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    team = models.Team(
        name="Managers Own Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    login_response = client.post(
        "/users/login",
        data={
            "username": "testmanager",
            "password": "TestManager123!",
        },
    )
    assert login_response.status_code == 200

    manager_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    response = client.get(
        f"/teams/{team.id}",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == team.id


def test_manager_cannot_read_another_managers_team(
    client, test_db
):
    from app import models

    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )

    other_manager = models.User(
        username="othermanager",
        email="othermanager@example.com",
        password_hash=manager.password_hash,
        role_id=manager.role_id,
    )
    test_db.add(other_manager)
    test_db.commit()
    test_db.refresh(other_manager)

    team = models.Team(
        name="Other Managers Team",
        manager_id=other_manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    login_response = client.post(
        "/users/login",
        data={
            "username": "testmanager",
            "password": "TestManager123!",
        },
    )
    assert login_response.status_code == 200

    manager_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    response = client.get(
        f"/teams/{team.id}",
        headers=manager_headers,
    )

    assert response.status_code == 403