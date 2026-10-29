"""Pydantic schemas for audit log querying and verification."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Schema representing an individual audit log entry."""

    id: int
    ts: datetime
    actor_id: str | None = None
    actor_role: str | None = None
    action: str
    entity: str
    entity_id: str | None = None
    before_json: dict[str, Any] | None = None
    after_json: dict[str, Any] | None = None
    ip: str | None = None
    prev_hash: str | None = None
    hash: str

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated list response of audit log entries."""

    total: int = Field(..., description="Total count matching query filters")
    items: list[AuditLogResponse] = Field(..., description="List of audit log records")
    limit: int = Field(..., description="Max records returned per page")
    offset: int = Field(..., description="Record offset position")


class AuditChainVerificationResponse(BaseModel):
    """Cryptographic chain verification result."""

    verified: bool = Field(..., description="True if the entire hash chain is valid")
    total_records: int = Field(..., description="Total number of evaluated audit records")
    first_broken_id: int | None = Field(
        None, description="Primary key id of the first broken row, if tampered"
    )
    broken_at_index: int | None = Field(
        None, description="0-based sequence index where the chain was broken"
    )
    reason: str | None = Field(None, description="Technical explanation of the failure")
    message: str = Field(..., description="Human-readable verification status")
    genesis_hash: str | None = Field(None, description="SHA-256 hash of genesis record")
    latest_hash: str | None = Field(None, description="SHA-256 hash of most recent record")
