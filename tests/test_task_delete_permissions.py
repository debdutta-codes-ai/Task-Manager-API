def test_regular_user_can_delete_own_task(client, test_db):
    from app import models

    # Find the regular user
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Create a task owned by the regular user
    task = models.Task(
        title="Task to delete",
        description="This task belongs to the user",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    # Log in as the regular user
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

    # Delete the user's own task
    response = client.delete(
        f"/tasks/{task.id}",
        headers=user_headers,
    )

    assert response.status_code in (200, 204)

    # Verify that the task was deleted
    deleted_task = (
        test_db.query(models.Task)
        .filter(models.Task.id == task.id)
        .first()
    )

    assert deleted_task is None

def test_regular_user_cannot_delete_another_users_task(
    client, test_db
):
    from app import models

    # Find the regular user and admin
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Create a task owned by the admin
    admin = (
        test_db.query(models.User)
        .filter(models.User.username == "testadmin")
        .first()
    )

    task = models.Task(
        title="Admin's task",
        description="The regular user must not delete this",
        status="pending",
        owner_id=admin.id,
        assigned_to=admin.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    # Log in as the regular user
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

    # Try to delete the admin's task
    response = client.delete(
        f"/tasks/{task.id}",
        headers=user_headers,
    )

    assert response.status_code == 403

    # Verify that the task still exists
    existing_task = (
        test_db.query(models.Task)
        .filter(models.Task.id == task.id)
        .first()
    )

    assert existing_task is not None

def test_manager_can_delete_task_in_their_team(client, test_db):
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

    # Create a team managed by this manager
    team = models.Team(
        name="Manager Delete Team",
        manager_id=manager.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    # Add the user to the team
    membership = models.TeamMember(
        team_id=team.id,
        user_id=user.id,
    )
    test_db.add(membership)

    # Create a task in the team
    task = models.Task(
        title="Team task to delete",
        description="Manager should be allowed to delete this",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
        team_id=team.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    # Log in as manager
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

    # Delete the team task
    response = client.delete(
        f"/tasks/{task.id}",
        headers=manager_headers,
    )

    assert response.status_code in (200, 204)

    deleted_task = (
        test_db.query(models.Task)
        .filter(models.Task.id == task.id)
        .first()
    )
    assert deleted_task is None


def test_admin_can_delete_any_users_task(client, test_db):
    from app import models

    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    task = models.Task(
        title="Task for admin deletion",
        description="Admin can delete this task",
        status="pending",
        owner_id=user.id,
        assigned_to=user.id,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

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

    response = client.delete(
        f"/tasks/{task.id}",
        headers=admin_headers,
    )

    assert response.status_code in (200, 204)

    deleted_task = (
        test_db.query(models.Task)
        .filter(models.Task.id == task.id)
        .first()
    )
    assert deleted_task is None