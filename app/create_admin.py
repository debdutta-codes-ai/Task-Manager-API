from pwdlib import PasswordHash

from app.database import Base, engine, SessionLocal
from app import models
from app.config import settings


ADMIN_USERNAME = settings.admin_username
ADMIN_EMAIL = settings.admin_email
ADMIN_PASSWORD = settings.admin_password


if not ADMIN_USERNAME or not ADMIN_EMAIL or not ADMIN_PASSWORD:
    raise ValueError(
        "ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD "
        "must be set in .env"
    )


# Create database tables
Base.metadata.create_all(bind=engine)

password_hash = PasswordHash.recommended()

db = SessionLocal()


# =========================
# Create default roles
# =========================

default_roles = [
    {
        "name": "admin",
        "description": "Full system access"
    },
    {
        "name": "manager",
        "description": "Can manage team tasks"
    },
    {
        "name": "user",
        "description": "Regular user"
    }
]


for role_data in default_roles:
    existing_role = (
        db.query(models.Role)
        .filter(models.Role.name == role_data["name"])
        .first()
    )

    if existing_role is None:
        role = models.Role(
            name=role_data["name"],
            description=role_data["description"]
        )

        db.add(role)


db.commit()

# =========================
# Create standard permissions
# =========================

default_permissions = [
    # Read permissions
    {
        "name": "read_all_tasks",
        "description": "Read all tasks"
    },
    {
        "name": "read_own_task",
        "description": "Read own tasks"
    },
    {
        "name": "read_team_tasks",
        "description": "Read team tasks"
    },

    # Create permissions
    {
        "name": "create_task",
        "description": "Create tasks"
    },

    # Update permissions
    {
        "name": "update_any_task",
        "description": "Update any task"
    },
    {
        "name": "update_own_task",
        "description": "Update own tasks"
    },
    {
        "name": "update_team_task",
        "description": "Update team tasks"
    },

    # Delete permissions
    {
        "name": "delete_any_task",
        "description": "Delete any task"
    },
    {
        "name": "delete_own_task",
        "description": "Delete own tasks"
    },
    {
        "name": "delete_team_task",
        "description": "Delete team tasks"
    },

    # User and role management
    {
        "name": "manage_users",
        "description": "Manage users"
    },
    {
        "name": "change_roles",
        "description": "Manage roles and permissions"
    }
]

for permission_data in default_permissions:
    existing_permission = (
        db.query(models.Permission)
        .filter(
            models.Permission.name == permission_data["name"]
        )
        .first()
    )

    if existing_permission is None:
        permission = models.Permission(
            name=permission_data["name"],
            description=permission_data["description"]
        )

        db.add(permission)

db.commit()

# =========================
# Assign permissions to roles
# =========================

role_permissions = {
    "admin": [
        "read_all_tasks",
        "read_own_task",
        "read_team_tasks",
        "create_task",
        "update_any_task",
        "update_own_task",
        "update_team_task",
        "delete_any_task",
        "delete_own_task",
        "delete_team_task",
        "manage_users",
        "change_roles"
    ],
    "manager": [
        "read_own_task",
        "read_team_tasks",
        "create_task",
        "update_own_task",
        "update_team_task",
        "delete_own_task",
        "delete_team_task"
    ],
    "user": [
        "read_own_task",
        "create_task",
        "update_own_task",
        "delete_own_task"
    ]
}

for role_name, permission_names in role_permissions.items():
    # Find the role
    role = (
        db.query(models.Role)
        .filter(models.Role.name == role_name)
        .first()
    )

    if role is None:
        continue

    for permission_name in permission_names:
        # Find the permission
        permission = (
            db.query(models.Permission)
            .filter(
                models.Permission.name == permission_name
            )
            .first()
        )

        if permission is not None and permission not in role.permissions:
            # Add the permission only if it is not already assigned
            role.permissions.append(permission)

db.commit()

# =========================
# Get admin role
# =========================

admin_role = (
    db.query(models.Role)
    .filter(models.Role.name == "admin")
    .first()
)


# =========================
# Create admin user
# =========================

existing_admin = (
    db.query(models.User)
    .filter(
        models.User.username == ADMIN_USERNAME
    )
    .first()
)


if existing_admin is None:

    admin = models.User(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password_hash=password_hash.hash(ADMIN_PASSWORD),
        role_id=admin_role.id,
        status="active"
    )

    db.add(admin)
    db.commit()

    print("Admin created successfully!")

else:
    print("Admin already exists!")


db.close()