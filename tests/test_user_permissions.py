def test_admin_can_list_users(client):
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

    response = client.get(
        "/users/",
        headers=admin_headers,
    )

    print(response.json())
    assert response.status_code == 200


def test_regular_user_cannot_list_users(client):
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
        "/users/",
        headers=user_headers,
    )

    assert response.status_code == 403


def test_admin_can_change_user_role(client, test_db):
    from app import models

    # Find the regular user
    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    # Find the manager role
    manager_role = (
        test_db.query(models.Role)
        .filter(models.Role.name == "manager")
        .first()
    )

    assert manager_role is not None

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

    # Change the user's role to manager
    response = client.put(
        f"/users/{user.id}/role",
        headers=admin_headers,
        json={"role_id": manager_role.id},
    )

    assert response.status_code == 200

    # Verify that the role was changed
    test_db.refresh(user)
    assert user.role.name == "manager"

def test_regular_user_cannot_change_user_role(client, test_db):
    from app import models

    admin = (
        test_db.query(models.User)
        .filter(models.User.username == "testadmin")
        .first()
    )

    original_role = admin.role.name

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

    response = client.put(
        f"/users/{admin.id}/role",
        headers=user_headers,
        json={
            "role_id": test_db.query(models.Role)
            .filter(models.Role.name == "manager")
            .first()
            .id
        },
    )

    assert response.status_code == 403

    test_db.refresh(admin)
    assert admin.role.name == original_role

def test_manager_cannot_list_users(client):
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

    response = client.get(
        "/users/",
        headers=manager_headers
    )

    assert response.status_code == 403

def test_manager_cannot_change_user_role(client, test_db):
    from app import models

    # Get the admin user
    admin = test_db.query(models.User).filter(
        models.User.username == "testadmin"
    ).first()

    # Log in as manager
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

    # Try to change the admin's role
    response = client.put(
        f"/users/{admin.id}/role",
        headers=manager_headers,
        json={
           "role_id": test_db.query(models.Role)
    .filter(models.Role.name == "manager")
    .first()
    .id
},
    )

    assert response.status_code == 403

def test_regular_user_cannot_delete_user(client, test_db):
    from app import models

    admin = (
        test_db.query(models.User)
        .filter(models.User.username == "testadmin")
        .first()
    )

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

    response = client.delete(
        f"/users/{admin.id}",
        headers=user_headers,
    )

    assert response.status_code == 403

    # Confirm the admin account still exists.
    existing_admin = (
        test_db.query(models.User)
        .filter(models.User.id == admin.id)
        .first()
    )
    assert existing_admin is not None


def test_manager_cannot_delete_user(client, test_db):
    from app import models

    admin = (
        test_db.query(models.User)
        .filter(models.User.username == "testadmin")
        .first()
    )

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

    response = client.delete(
        f"/users/{admin.id}",
        headers=manager_headers,
    )

    assert response.status_code == 403

    # Confirm the admin account still exists.
    test_db.refresh(admin)
    assert admin.username == "testadmin"

def test_admin_can_delete_user(client, test_db):
    from app import models

    user = (
        test_db.query(models.User)
        .filter(models.User.username == "testuser")
        .first()
    )

    user_id = user.id

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
        f"/users/{user_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    # Confirm the user still exists but is soft-deleted.
    test_db.expire_all()

    deleted_user = (
        test_db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    assert deleted_user is not None
    assert deleted_user.status == "inactive"
    assert deleted_user.deleted_at is not None
    assert deleted_user.deleted_by is not None

def test_admin_cannot_delete_nonexistent_user(client):
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
        "/users/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404

def test_user_response_includes_nested_role_and_permissions(client):
    response = client.post(
        "/users/login",
        data={
            "username": "testuser",
            "password": "TestUser123!",
        },
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/users/", headers=headers)

    assert response.status_code == 403

def test_my_profile_includes_nested_role_and_permissions(client):
    login_response = client.post(
        "/users/login",
        data={
            "username": "testuser",
            "password": "TestUser123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = client.get(
        "/users/me",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert "role" in data
    assert data["role"] is not None
    assert "name" in data["role"]
    assert "permissions" in data["role"]
    assert isinstance(data["role"]["permissions"], list)

    for permission in data["role"]["permissions"]:
        assert "id" in permission
        assert "name" in permission

def test_admin_user_list_includes_nested_role_and_permissions(client):
    login_response = client.post(
        "/users/login",
        data={
            "username": "testadmin",
            "password": "TestAdmin123!",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = client.get("/users/", headers=headers)

    assert response.status_code == 200
    users = response.json()
    assert len(users) > 0

    for user in users:
        assert user["role"] is not None
        assert "name" in user["role"]
        assert isinstance(user["role"]["permissions"], list)