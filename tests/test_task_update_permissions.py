def test_regular_user_cannot_update_another_users_task(
    client,
    admin_headers
):
    # Admin creates a task owned by the admin
    task_data = {
        "title": "Admin's task",
        "description": "This task belongs to admin",
        "assigned_to_email": "testadmin@example.com"
    }

    create_response = client.post(
        "/tasks/",
        json=task_data,
        headers=admin_headers
    )

    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    # Regular user logs in
    login_response = client.post(
        "/users/login",
        data={
            "username": "testuser",
            "password": "TestUser123!"
        }
    )

    assert login_response.status_code == 200
    user_token = login_response.json()["access_token"]
    user_headers = {
        "Authorization": f"Bearer {user_token}"
    }

    # Regular user tries to update the admin's task
    update_data = {
        "title": "Unauthorized change",
        "description": "Trying to update another user's task",
        "assigned_to_email": "testadmin@example.com"
    }

    response = client.put(
        f"/tasks/{task_id}",
        json=update_data,
        headers=user_headers
    )

    assert response.status_code == 403

def test_regular_user_can_update_own_task(client):
    # Log in as the regular user
    login_response = client.post(
        "/users/login",
        data={
            "username": "testuser",
            "password": "TestUser123!",
        },
    )

    assert login_response.status_code == 200

    user_token = login_response.json()["access_token"]
    user_headers = {
        "Authorization": f"Bearer {user_token}"
    }

    # Create a task owned by the regular user
    task_data = {
        "title": "My original task",
        "description": "Original description",
        "assigned_to_email": "testuser@example.com",
    }

    create_response = client.post(
        "/tasks/",
        json=task_data,
        headers=user_headers,
    )

    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    # Update the user's own task
    update_data = {
        "title": "My updated task",
        "description": "Updated description",
        "assigned_to_email": "testuser@example.com",
    }

    update_response = client.put(
        f"/tasks/{task_id}",
        json=update_data,
        headers=user_headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "My updated task"


def test_manager_can_update_task_in_their_team(client, test_db):
    from app import models

    # Find the manager and regular user
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

    # Create a team managed by this manager
    team = models.Team(
        name="Manager Update Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add the regular user to the team
    membership = models.TeamMember(
        team_id=team.id,
        user_id=user.id,
    )
    test_db.add(membership)

    # Create a task owned by the regular user in this team
    task = models.Task(
        title="Original team task",
        description="Original description",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
        team_id=team.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    # Log in as the manager
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

    # Update the task in the manager's team
    update_response = client.put(
        f"/tasks/{task.id}",
        headers=manager_headers,
        json={
            "title": "Updated team task",
            "description": "Updated by the manager",
            "status": "pending",
            "assigned_to_email": user.email,
            "team_id": team.id,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated team task"

def test_manager_cannot_update_task_in_another_managers_team(
    client, test_db
):
    from app import models
    from app.auth import password_hash

    # Find the test manager and regular user
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

    # Create another manager with the manager role
    other_manager = models.User(
        username="othermanager",
        email="othermanager@example.com",
        password_hash=password_hash.hash("OtherManager123!"),
        role=manager.role,
        status="active",
    )
    test_db.add(other_manager)
    test_db.commit()
    test_db.refresh(other_manager)

    # Create a team owned by the other manager
    team = models.Team(
        name="Other Manager Update Team",
        manager_id=other_manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add the regular user to that team
    membership = models.TeamMember(
        team_id=team.id,
        user_id=user.id,
    )
    test_db.add(membership)

    # Create a task in the other manager's team
    task = models.Task(
        title="Restricted team task",
        description="Should not be updated by another manager",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
        team_id=team.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    # Log in as the original manager
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

    # Try to update the other manager's team's task
    response = client.put(
        f"/tasks/{task.id}",
        headers=manager_headers,
        json={
            "title": "Unauthorized update",
            "description": "This change should be rejected",
            "status": "pending",
            "assigned_to_email": user.email,
            "team_id": team.id,
        },
    )

    assert response.status_code == 403


def test_admin_can_update_any_users_task(client, test_db):
    from app import models

    # Find the regular user
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Create a task owned by the regular user
    task = models.Task(
        title="Original user task",
        description="Task owned by a regular user",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    # Log in as admin
    login_response = client.post(
        "/users/login",
        data={
            "username": "testadmin",
            "password": "TestAdmin123!",
        },
    )

    assert login_response.status_code == 200

    admin_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Admin updates the regular user's task
    response = client.put(
        f"/tasks/{task.id}",
        headers=admin_headers,
        json={
            "title": "Updated by admin",
            "description": "Admin updated this task",
            "status": "pending",
            "assigned_to_email": user.email,
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated by admin"

