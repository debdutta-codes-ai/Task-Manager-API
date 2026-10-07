from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    role_id = Column(
        Integer,
        ForeignKey("roles.id"),
        nullable=False
    )

    role = relationship("Role")

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        default="active",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    last_login = Column(
        DateTime,
        nullable=True
    )

    deleted_at = Column(
        DateTime,
        nullable=True
    )

    deleted_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    assigned_to = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    assigned_user = relationship(
        "User",
        foreign_keys=[assigned_to]
    )

    team_id = Column(
        Integer,
        ForeignKey("teams.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )



class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    manager_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)

    team_id = Column(
        Integer,
        ForeignKey("teams.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

class Role(Base):
    __tablename__ = "roles"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    description = Column(
        String,
        nullable=True
    )