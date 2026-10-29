"""Institutional API Key Lifecycle, Hashing, Authentication, and Scopes."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from enum import StrEnum

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit_service
from app.institutions.service import check_institution_can_upload
from app.models import ApiKey, Institution, User


class ApiKeyScope(StrEnum):
    """Supported scopes for institutional integration API keys."""

    STUDENTS_WRITE = "students:write"
    STUDENTS_READ = "students:read"
    COURSES_READ = "courses:read"
    ALL = "*"


DEFAULT_SCOPES: list[str] = [
    ApiKeyScope.STUDENTS_WRITE.value,
    ApiKeyScope.STUDENTS_READ.value,
]


# Schemas


class ApiKeyCreateRequest(BaseModel):
    """Payload to generate a new institutional API key."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Descriptive name (e.g. Campus ERP)",
    )
    scopes: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SCOPES),
        description="Allowed scopes: students:write, students:read, courses:read",
    )


class ApiKeyResponse(BaseModel):
    """Public representation of an institutional API key (never exposes full secret)."""

    id: int
    institution_id: int
    name: str
    key_prefix: str = Field(description="Safe prefix preview (e.g. apaar_live_a1b2...c3d4)")
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Response returned upon key creation or rotation containing plaintext key once."""

    raw_key: str = Field(description="Full secret API key. Displayed ONLY ONCE!")


class ApiKeyRotateResponse(BaseModel):
    """Response returned upon rotating an API key."""

    id: int
    institution_id: int
    name: str
    key_prefix: str
    raw_key: str = Field(description="New secret API key. Displayed ONLY ONCE!")
    scopes: list[str]
    updated_at: datetime


class ApiKeyListResponse(BaseModel):
    """Collection of API keys for an institution."""

    items: list[ApiKeyResponse]
    total: int


# Security & Hashing Helpers


def generate_raw_key() -> str:
    """Generate a high-entropy cryptographically secure raw API key."""
    token = secrets.token_urlsafe(32)
    return f"apaar_live_{token}"


def hash_key(raw_key: str) -> str:
    """Compute SHA-256 hexadecimal digest of raw API key for secure database storage."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def compute_key_prefix(raw_key: str) -> str:
    """Format safe prefix preview for UI and logs (e.g. 'apaar_live_a1b2...c3d4')."""
    raw = raw_key.strip()
    if raw.startswith("apaar_live_") and len(raw) > 20:
        secret = raw[len("apaar_live_") :]
        return f"apaar_live_{secret[:4]}...{secret[-4:]}"
    if len(raw) > 10:
        return f"{raw[:6]}...{raw[-4:]}"
    return "apaar_live_****"


def to_api_key_response(key: ApiKey) -> ApiKeyResponse:
    """Convert ORM ApiKey to safe response DTO."""
    # Since key_hash is stored in DB, we generate a stable preview from the hash prefix
    hash_slice = key.key_hash[:4] + "..." + key.key_hash[-4:]
    return ApiKeyResponse(
        id=key.id,
        institution_id=key.institution_id,
        name=key.name,
        key_prefix=f"apaar_live_{hash_slice}",
        scopes=list(key.scopes) if isinstance(key.scopes, list) else [],
        created_at=key.created_at,
        last_used_at=key.last_used_at,
        revoked_at=key.revoked_at,
        is_active=key.revoked_at is None,
    )


# Service Functions


def create_api_key(
    db: Session,
    institution_id: int,
    name: str,
    scopes: list[str],
    user: User | None = None,
    client_ip: str | None = None,
) -> tuple[ApiKey, str]:
    """Create and persist a new scoped API key for an institution."""
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )

    # Validate scopes
    valid_scope_values = {s.value for s in ApiKeyScope}
    for s in scopes:
        if s not in valid_scope_values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope '{s}'. Allowed scopes: {sorted(valid_scope_values)}",
            )

    raw_key = generate_raw_key()
    key_hash = hash_key(raw_key)

    api_key = ApiKey(
        institution_id=institution_id,
        name=name.strip(),
        key_hash=key_hash,
        scopes=scopes,
    )
    db.add(api_key)
    db.flush()

    # Record hash-chained audit log
    audit_service.record(
        db=db,
        actor_id=user.id if user else None,
        actor_role=user.role if user else "college_admin",
        action="api_key.create",
        entity="api_key",
        entity_id=str(api_key.id),
        before_json=None,
        after_json={
            "id": api_key.id,
            "institution_id": institution_id,
            "name": api_key.name,
            "scopes": api_key.scopes,
            "key_prefix": compute_key_prefix(raw_key),
        },
        ip=client_ip,
    )

    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def list_api_keys(db: Session, institution_id: int) -> list[ApiKey]:
    """Retrieve all API keys belonging to an institution."""
    return list(
        db.scalars(
            select(ApiKey)
            .where(ApiKey.institution_id == institution_id)
            .order_by(ApiKey.created_at.desc())
        ).all()
    )


def rotate_api_key(
    db: Session,
    institution_id: int,
    key_id: int,
    user: User | None = None,
    client_ip: str | None = None,
) -> tuple[ApiKey, str]:
    """Rotate an active API key: generates a new secret hash and resets last_used_at."""
    api_key = db.get(ApiKey, key_id)
    if not api_key or api_key.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key #{key_id} not found for institution #{institution_id}",
        )

    if api_key.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rotate a revoked API key. Generate a new API key instead.",
        )

    old_hash = api_key.key_hash
    raw_key = generate_raw_key()
    new_hash = hash_key(raw_key)

    api_key.key_hash = new_hash
    api_key.last_used_at = None
    api_key.updated_at = datetime.now(UTC)
    db.flush()

    # Audit rotation
    audit_service.record(
        db=db,
        actor_id=user.id if user else None,
        actor_role=user.role if user else "college_admin",
        action="api_key.rotate",
        entity="api_key",
        entity_id=str(api_key.id),
        before_json={"key_hash_prefix": old_hash[:8]},
        after_json={"key_hash_prefix": new_hash[:8], "key_prefix": compute_key_prefix(raw_key)},
        ip=client_ip,
    )

    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def revoke_api_key(
    db: Session,
    institution_id: int,
    key_id: int,
    user: User | None = None,
    client_ip: str | None = None,
) -> ApiKey:
    """Revoke an API key so it can no longer authenticate."""
    api_key = db.get(ApiKey, key_id)
    if not api_key or api_key.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key #{key_id} not found for institution #{institution_id}",
        )

    if api_key.revoked_at is not None:
        return api_key

    api_key.revoked_at = datetime.now(UTC)
    api_key.updated_at = datetime.now(UTC)
    db.flush()

    audit_service.record(
        db=db,
        actor_id=user.id if user else None,
        actor_role=user.role if user else "college_admin",
        action="api_key.revoke",
        entity="api_key",
        entity_id=str(api_key.id),
        before_json={"revoked_at": None},
        after_json={"revoked_at": api_key.revoked_at.isoformat()},
        ip=client_ip,
    )

    db.commit()
    db.refresh(api_key)
    return api_key


def authenticate_api_key(db: Session, raw_key: str) -> tuple[Institution, ApiKey]:
    """Validate incoming raw API key, check institution approval status, and update last_used_at."""
    if not raw_key or not isinstance(raw_key, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    incoming_hash = hash_key(raw_key)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == incoming_hash))

    if not api_key or api_key.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    institution = db.get(Institution, api_key.institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Institution associated with this API key no longer exists",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # SPEC 6: Suspended/withdrawn/expired approval blocks operations (403 Forbidden)
    check_institution_can_upload(institution)

    # Touch last_used_at timestamp
    api_key.last_used_at = datetime.now(UTC)
    db.commit()

    return institution, api_key
