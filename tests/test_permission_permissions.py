def login_headers(client, username, password):
    response = client.post(
        "/users/login",
        data={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def test_unauthenticated_user_cannot_list_permissions(client):
    response = client.get("/permissions/")

    assert response.status_code in (401, 403)


def test_regular_user_cannot_list_permissions(client):
    headers = login_headers(
        client,
        "testuser",
        "TestUser123!",
    )

    response = client.get("/permissions/", headers=headers)

    assert response.status_code == 403


def test_manager_cannot_create_permission(client):
    headers = login_headers(
        client,
        "testmanager",
        "TestManager123!",
    )

    response = client.post(
        "/permissions/",
        headers=headers,
        json={
            "name": "test_permission",
            "description": "Permission created by test",
        },
    )

    assert response.status_code == 403


def test_admin_can_list_permissions(client, admin_headers):
    response = client.get(
        "/permissions/",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_can_create_permission(client, admin_headers):
    response = client.post(
        "/permissions/",
        headers=admin_headers,
        json={
            "name": "test_permission",
            "description": "Permission created by admin",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "test_permission"


def test_admin_cannot_delete_change_roles_permission(
    client,
    admin_headers,
    test_db,
):
    permission = (
        test_db.query(__import__("app.models", fromlist=["Permission"]).Permission)
        .filter_by(name="change_roles")
        .first()
    )

    assert permission is not None

    response = client.delete(
        f"/permissions/{permission.id}",
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Cannot delete the change_roles permission"
    )


def test_admin_gets_404_for_missing_permission(client, admin_headers):
    response = client.get(
        "/permissions/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404