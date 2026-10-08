from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =========================
# Admin User Schemas
# =========================

class AdminUserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(min_length=8)
    role_id: int


class AdminUserUpdate(BaseModel):
    username: str
    email: str
    role_id: int


# =========================
# Task Schemas
# =========================

class TaskCreate(BaseModel):
    title: str
    description: str
    status: str = "pending"
    assigned_to_email: str 
    team_id: int | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    owner_id: int
    assigned_to_email: str | None = None
    team_id: int | None = None
    created_at: datetime
    updated_at: datetime


# =========================
# User Schemas
# =========================

class UserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if not any(char.isupper() for char in value):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )

        if not any(char.islower() for char in value):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )

        if not any(char.isdigit() for char in value):
            raise ValueError(
                "Password must contain at least one number"
            )

        if not any(not char.isalnum() for char in value):
            raise ValueError(
                "Password must contain at least one special character"
            )

        return value


class UserResponse(BaseModel):
    id: int
    username: str
    email: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# =========================
# Team Schemas
# =========================

class TeamCreate(BaseModel):
    name: str
    manager_id: int


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    manager_id: int
    created_at: datetime
    updated_at: datetime


class TeamMemberAdd(BaseModel):
    user_id: int


class TeamUpdate(BaseModel):
    name: str
    manager_id: int


# =========================
# Permission Schemas
# =========================

class PermissionCreate(BaseModel):
    name: str
    description: str | None = None


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None

class RolePermissionCreate(BaseModel):
    permission_id: int

# =========================
# Role Schemas
# =========================

class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str
    description: str | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    permissions: list[PermissionResponse] = Field(
        default_factory=list
    )