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
        json={"role": "manager"},
    )

    assert response.status_code == 403

    test_db.refresh(admin)
    assert admin.role.name == original_role