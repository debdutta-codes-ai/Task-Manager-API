def test_regular_user_cannot_read_another_users_task(
    client, test_db, admin_headers
):
    from app import models

    # Find the regular test user.
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Admin creates a task assigned to the admin.
    create_response = client.post(
        "/tasks/",
        headers=admin_headers,
        json={
            "title": "Admin private task",
            "description": "Only authorized users should read this",
            "status": "pending",
            "assigned_to_email": "testadmin@example.com",
            "team_id": None,
        },
    )

    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

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

    # Try to read the admin's task as a regular user.
    response = client.get(
        f"/tasks/{task_id}",
        headers=user_headers,
    )

    # The regular user should be denied access.
    assert response.status_code == 403


def test_regular_user_can_read_own_task(client, test_db):
    from app import models

    # Find the regular test user.
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Create a task assigned to the regular user.
    task = models.Task(
        title="User's own task",
        description="The user should be able to read this task",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

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

    # Read the user's own task.
    response = client.get(
        f"/tasks/{task.id}",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == task.id
    assert response.json()["title"] == "User's own task"


def test_manager_can_read_task_in_their_team(client, test_db):
    from app import models

    # Find the manager and regular user.
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
        name="Manager Read Team",
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

    # Create a task belonging to the team and owned by the regular user.
    task = models.Task(
        title="Team task",
        description="The manager should be able to read this task",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
        team_id=team.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

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

    # Read the team task as its manager.
    response = client.get(
        f"/tasks/{task.id}",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == task.id
    assert response.json()["title"] == "Team task"



def test_manager_cannot_read_task_in_another_managers_team(
    client, test_db
):
    from app import models

    # Find the two managers and the regular user.
    manager = (
        test_db.query(models.User)
        .filter(models.User.username == "testmanager")
        .first()
    )
    other_manager = models.User(
        username="othermanager",
        email="othermanager@example.com",
        password_hash=__import__("app.auth", fromlist=["password_hash"])
        .password_hash.hash("OtherManager123!"),
        role=manager.role,
        status="active",
    )
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    test_db.add(other_manager)
    test_db.commit()
    test_db.refresh(other_manager)

    # Create a team managed by the other manager.
    team = models.Team(
        name="Other Manager Team",
        manager_id=other_manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add the regular user to that team.
    membership = models.TeamMember(
        team_id=team.id,
        user_id=user.id,
    )
    test_db.add(membership)

    # Create a task in the other manager's team.
    task = models.Task(
        title="Restricted team task",
        description="This task belongs to another manager's team",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
        team_id=team.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    # Log in as the first manager.
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

    # Try to read a task managed by someone else.
    response = client.get(
        f"/tasks/{task.id}",
        headers=manager_headers,
    )

    assert response.status_code == 403

def test_admin_can_read_all_tasks(client, test_db):
    from app import models

    # Find the regular user and admin
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Create a task owned by the regular user
    task = models.Task(
        title="User's private task",
        description="Admin should be able to read this",
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

    # Request all tasks
    response = client.get(
        "/tasks/",
        headers=admin_headers,
    )

    assert response.status_code == 200

    task_ids = [item["id"] for item in response.json()]
    assert task.id in task_ids