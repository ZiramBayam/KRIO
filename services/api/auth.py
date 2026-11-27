"""Demo login and authenticated tenant context."""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .db import transaction

router = APIRouter(prefix="/auth")
bearer = HTTPBearer(auto_error=False)
DUMMY_HASH = bcrypt.hashpw(b"unused", bcrypt.gensalt())


class Login(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=72)


class User(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: Literal["owner", "admin", "viewer"]


class Session(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: User


def password_matches(password: str, stored: str) -> bool:
    raw = password.encode()
    if len(raw) > 72:
        return False
    try:
        return bcrypt.checkpw(raw, stored.encode())
    except ValueError:
        return False


def secret() -> str:
    return os.environ["JWT_SECRET_KEY"]


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(401, "Invalid or expired session", {"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        claims = jwt.decode(
            credentials.credentials, secret(), algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
        user_id = str(UUID(claims["sub"]))
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized from None
    with transaction() as cur:
        cur.execute("SELECT id, tenant_id, email, role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    if row is None:
        raise unauthorized
    return User.model_validate(row)


Authenticated = Annotated[User, Depends(current_user)]


def writer(user: Authenticated) -> User:
    if user.role == "viewer":
        raise HTTPException(403, "This role has read-only access")
    return user


Writer = Annotated[User, Depends(writer)]


@router.post("/login")
def login(form: Login) -> Session:
    with transaction() as cur:
        cur.execute(
            "SELECT id, tenant_id, email, role, password_hash FROM users WHERE email = %s",
            (form.email.strip(),),
        )
        row = cur.fetchone()
    stored = row["password_hash"] if row else DUMMY_HASH.decode()
    if not password_matches(form.password, stored) or row is None:
        raise HTTPException(401, "Invalid email or password", {"WWW-Authenticate": "Bearer"})
    user = User.model_validate(row)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=30)},
        secret(), algorithm="HS256",
    )
    return Session(access_token=token, user=user)


@router.get("/me")
def me(user: Authenticated) -> User:
    return user
