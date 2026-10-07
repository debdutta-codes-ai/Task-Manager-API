from datetime import datetime, timedelta, timezone
from fastapi import HTTPException,Depends, status
import jwt
from pwdlib import PasswordHash
# from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app import models, crud
from app.database import get_db
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)


password_hash = PasswordHash.recommended()

oauth2_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    payload = decode_access_token(token)

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = db.query(models.User).filter(
        models.User.id == int(user_id)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user

def verify_password(
    plain_password: str,
    hashed_password: str
):
    return password_hash.verify(
        plain_password,
        hashed_password
    )

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None
):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=15
        )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

def require_roles(*allowed_roles):
    def role_checker(
        current_user=Depends(get_current_user)
    ):
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        return current_user

    return role_checker