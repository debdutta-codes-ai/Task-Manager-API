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