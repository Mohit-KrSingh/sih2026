"""FastAPI dependencies for authentication, RBAC, and institution scoping."""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import Role
from app.auth.security import decode_token
from app.db import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    description="Bearer JWT token",
    auto_error=True,
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Validate bearer token and return authenticated active user.

    Raises:
        HTTPException 401: Token expired or invalid.
        HTTPException 403: User account is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise credentials_exception from None

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise credentials_exception

    try:
        user_id = int(user_id_raw)
    except ValueError:
        raise credentials_exception from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Factory creating a FastAPI dependency that restricts access to specified roles.

    Raises:
        HTTPException 403: User role is not among allowed roles.
    """

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role}' lacks required permissions",
            )
        return current_user

    return role_checker


# Named role dependencies
require_authenticated = Depends(get_current_user)
require_aicte_admin = Depends(require_roles(Role.AICTE_ADMIN.value))
require_aicte_officer = Depends(require_roles(Role.AICTE_ADMIN.value, Role.AICTE_OFFICER.value))
require_aicte_role = require_aicte_officer
require_aicte_user = require_aicte_officer
require_college_admin = Depends(require_roles(Role.COLLEGE_ADMIN.value))
require_college_staff = Depends(require_roles(Role.COLLEGE_ADMIN.value, Role.COLLEGE_STAFF.value))
require_college_viewer = Depends(
    require_roles(
        Role.COLLEGE_ADMIN.value,
        Role.COLLEGE_STAFF.value,
        Role.COLLEGE_VIEWER.value,
    )
)
require_college_user = require_college_viewer
require_verifier = Depends(require_roles(Role.VERIFIER.value))


def check_institution_access(institution_id: int, current_user: User) -> None:
    """Enforce strict institution scoping and IDOR prevention.

    - AICTE roles (aicte_admin, aicte_officer) have supervisory access across all institutions.
    - College roles (college_admin, college_staff, college_viewer) can ONLY access their own.
    - Other roles are denied.

    Raises:
        HTTPException 403: If institution access is unauthorized.
    """
    if current_user.role in Role.aicte_roles():
        return

    if current_user.role in Role.college_roles():
        if current_user.institution_id is None or current_user.institution_id != institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access another institution's data",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Insufficient privileges for institution data",
    )


def verify_institution_access(
    institution_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> int:
    """Dependency for endpoints with {institution_id} path parameter.

    Verifies the user is permitted to access this institution.
    Returns the validated institution_id.
    """
    check_institution_access(institution_id, current_user)
    return institution_id


def get_institution_scope(
    current_user: Annotated[User, Depends(get_current_user)],
) -> int | None:
    """Return institution_id for college-scoped users, or None for AICTE users with global scope.

    Raises:
        HTTPException 403: If the user lacks college association or AICTE permissions.
    """
    if current_user.role in Role.aicte_roles():
        return None

    if current_user.role in Role.college_roles():
        if current_user.institution_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="College user has no associated institution",
            )
        return current_user.institution_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: No institution scope available",
    )
