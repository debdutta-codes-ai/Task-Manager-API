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


def test_unauthenticated_user_cannot_list_roles(client):
    response = client.get("/roles/")

    assert response.status_code in (401, 403)


def test_regular_user_cannot_list_roles(client):
    headers = login_headers(
        client,
        "testuser",
        "TestUser123!",
    )

    response = client.get("/roles/", headers=headers)

    assert response.status_code == 403


def test_manager_cannot_list_roles(client):
    headers = login_headers(
        client,
        "testmanager",
        "TestManager123!",
    )

    response = client.get("/roles/", headers=headers)

    assert response.status_code == 403


def test_admin_can_list_roles(client, admin_headers):
    response = client.get("/roles/", headers=admin_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_can_get_existing_role(client, admin_headers, test_db):
    from app import models

    role = (
        test_db.query(models.Role)
        .filter_by(name="manager")
        .first()
    )

    response = client.get(
        f"/roles/{role.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "manager"


def test_admin_gets_404_for_missing_role(client, admin_headers):
    response = client.get(
        "/roles/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_can_create_role(client, admin_headers):
    response = client.post(
        "/roles/",
        headers=admin_headers,
        json={
            "name": "test_role",
            "description": "Role created by test",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "test_role"


def test_admin_cannot_create_duplicate_role(client, admin_headers):
    response = client.post(
        "/roles/",
        headers=admin_headers,
        json={
            "name": "manager",
            "description": "Duplicate manager role",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Role already exists"

def test_regular_user_cannot_create_role(client):
    headers = login_headers(
        client,
        "testuser",
        "TestUser123!",
    )

    response = client.post(
        "/roles/",
        headers=headers,
        json={
            "name": "unauthorized_role",
            "description": "Should not be created",
        },
    )

    assert response.status_code == 403


def test_admin_can_update_role(client, admin_headers, test_db):
    from app import models

    role = (
        test_db.query(models.Role)
        .filter_by(name="manager")
        .first()
    )

    response = client.put(
        f"/roles/{role.id}",
        headers=admin_headers,
        json={
            "name": "manager",
            "description": "Updated manager description",
        },
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated manager description"


def test_admin_gets_404_when_updating_missing_role(client, admin_headers):
    response = client.put(
        "/roles/99999",
        headers=admin_headers,
        json={
            "name": "missing_role",
            "description": "Updated description",
        },
    )

    assert response.status_code == 404


def test_admin_cannot_delete_default_role(client, admin_headers, test_db):
    from app import models

    role = (
        test_db.query(models.Role)
        .filter_by(name="admin")
        .first()
    )

    response = client.delete(
        f"/roles/{role.id}",
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Default roles cannot be deleted"


def test_admin_cannot_delete_role_assigned_to_user(
    client,
    admin_headers,
    test_db,
):
    from app import models

    role = models.Role(
        name="custom_manager",
        description="Custom role assigned to an active user",
    )
    test_db.add(role)
    test_db.flush()

    user = (
        test_db.query(models.User)
        .filter_by(username="testmanager")
        .first()
    )
    user.role_id = role.id
    test_db.commit()

    response = client.delete(
        f"/roles/{role.id}",
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot delete role because it is assigned to active users"
    )


def test_admin_gets_404_when_deleting_missing_role(client, admin_headers):
    response = client.delete(
        "/roles/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_can_assign_permission_to_role(
    client,
    admin_headers,
    test_db,
):
    from app import models

    role = models.Role(
        name="custom_role",
        description="Custom test role",
    )
    permission = (
        test_db.query(models.Permission)
        .filter_by(name="manage_users")
        .first()
    )
    test_db.add_all([role, permission])
    test_db.commit()
    test_db.refresh(role)
    test_db.refresh(permission)

    response = client.post(
        f"/roles/{role.id}/permissions",
        headers=admin_headers,
        json={"permission_id": permission.id},
    )

    assert response.status_code == 201


def test_admin_cannot_assign_duplicate_permission_to_role(
    client,
    admin_headers,
    test_db,
):
    from app import models

    role = models.Role(
        name="custom_role",
        description="Custom test role",
    )
    permission = (
        test_db.query(models.Permission)
        .filter_by(name="manage_users")
        .first()
    )
    
    test_db.add_all([role, permission])
    test_db.commit()
    test_db.refresh(role)
    test_db.refresh(permission)

    response = client.post(
        f"/roles/{role.id}/permissions",
        headers=admin_headers,
        json={"permission_id": permission.id},
    )
    assert response.status_code == 201

    response = client.post(
        f"/roles/{role.id}/permissions",
        headers=admin_headers,
        json={"permission_id": permission.id},
    )

    assert response.status_code == 409


def test_admin_gets_404_when_assigning_permission_to_missing_role(
    client,
    admin_headers,
    test_db,
):
    from app import models

    permission = (
        test_db.query(models.Permission)
        .filter_by(name="manage_users")
        .first()
    )
    test_db.add(permission)
    test_db.commit()
    test_db.refresh(permission)

    response = client.post(
        "/roles/99999/permissions",
        headers=admin_headers,
        json={"permission_id": permission.id},
    )

    assert response.status_code == 404


def test_admin_gets_404_when_assigning_missing_permission(
    client,
    admin_headers,
    test_db,
):
    from app import models

    role = models.Role(
        name="custom_role",
        description="Custom test role",
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client.post(
        f"/roles/{role.id}/permissions",
        headers=admin_headers,
        json={"permission_id": 99999},
    )

    assert response.status_code == 404

def test_admin_can_remove_permission_from_role(
    client,
    admin_headers,
    test_db,
):
    from app import models

    role = models.Role(
        name="custom_role",
        description="Custom test role",
    )
    permission = (
        test_db.query(models.Permission)
        .filter_by(name="manage_users")
        .first()
    )

    role.permissions.append(permission)
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client.delete(
        f"/roles/{role.id}/permissions/{permission.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

def test_admin_cannot_remove_change_roles_from_admin_role(
    client,
    admin_headers,
    test_db,
):
    from app import models

    admin_role = (
        test_db.query(models.Role)
        .filter_by(name="admin")
        .first()
    )
    permission = (
        test_db.query(models.Permission)
        .filter_by(name="change_roles")
        .first()
    )

    response = client.delete(
        f"/roles/{admin_role.id}/permissions/{permission.id}",
        headers=admin_headers,
    )

    assert response.status_code == 400

def test_admin_gets_404_when_removing_permission_from_missing_role(
    client,
    admin_headers,
    test_db,
):
    from app import models

    permission = (
        test_db.query(models.Permission)
        .filter_by(name="manage_users")
        .first()
    )

    response = client.delete(
        f"/roles/99999/permissions/{permission.id}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_gets_404_when_removing_missing_permission(
    client,
    admin_headers,
    test_db,
):
    from app import models

    role = models.Role(
        name="custom_role",
        description="Custom test role",
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client.delete(
        f"/roles/{role.id}/permissions/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404

def test_admin_gets_404_when_removing_unassigned_permission(
    client,
    admin_headers,
    test_db,
):
    from app import models

    role = models.Role(
        name="custom_role",
        description="Custom test role",
    )
    permission = (
        test_db.query(models.Permission)
        .filter_by(name="manage_users")
        .first()
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client.delete(
        f"/roles/{role.id}/permissions/{permission.id}",
        headers=admin_headers,
    )

    assert response.status_code == 404