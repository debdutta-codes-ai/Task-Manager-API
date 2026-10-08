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