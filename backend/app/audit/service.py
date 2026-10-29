"""Hash-chained, tamper-evident audit logging service."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import AuditLog

APAAR_PATTERN = re.compile(r"\b\d{8}(\d{4})\b")


def mask_apaar_id(value: str) -> str:
    """Mask a 12-digit APAAR ID, preserving only the last 4 digits."""
    return APAAR_PATTERN.sub(r"********\1", value)


def mask_sensitive_data(obj: Any) -> Any:
    """Recursively mask APAAR IDs in dictionaries, lists, or string values."""
    if isinstance(obj, dict):
        masked: dict[str, Any] = {}
        for k, v in obj.items():
            if k == "apaar_id" and isinstance(v, str):
                masked[k] = mask_apaar_id(v)
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(obj, list):
        return [mask_sensitive_data(item) for item in obj]
    elif isinstance(obj, str):
        return mask_apaar_id(obj)
    return obj


def format_canonical_ts(ts: datetime) -> str:
    """Format a datetime object into a canonical UTC ISO-8601 string."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC).isoformat()


def serialize_canonical_row(
    ts: datetime,
    actor_id: str | None,
    actor_role: str | None,
    action: str,
    entity: str,
    entity_id: str | None,
    before_json: dict[str, Any] | None,
    after_json: dict[str, Any] | None,
    ip: str | None,
) -> str:
    """Deterministic JSON serialization for canonical audit row hashing."""
    canonical = {
        "ts": format_canonical_ts(ts),
        "actor_id": str(actor_id) if actor_id is not None else None,
        "actor_role": str(actor_role) if actor_role is not None else None,
        "action": str(action),
        "entity": str(entity),
        "entity_id": str(entity_id) if entity_id is not None else None,
        "before_json": before_json,
        "after_json": after_json,
        "ip": str(ip) if ip is not None else None,
    }
    return json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def compute_hash(prev_hash: str | None, canonical_payload: str) -> str:
    """Compute SHA-256 hash over prev_hash + canonical row representation."""
    prefix = prev_hash or ""
    payload = f"{prefix}{canonical_payload}".encode()
    return hashlib.sha256(payload).hexdigest()


def record(
    db: Session,
    action: str,
    actor_id: str | int | None = None,
    actor_role: str | None = None,
    entity: str = "",
    entity_id: str | int | None = None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
    ip: str | None = None,
    commit: bool = False,
) -> AuditLog:
    """Record an append-only, hash-chained audit log entry.

    Args:
        db: Active SQLAlchemy database session.
        action: Event action name (e.g. 'auth.login', 'intake.update').
        actor_id: Identifier of the user or system actor.
        actor_role: Role of the actor (e.g. 'aicte_admin', 'college_admin').
        entity: Affected entity table/domain (e.g. 'user', 'course_intake').
        entity_id: Identifier of the affected entity.
        before_json: Previous state snapshot (if applicable).
        after_json: New state snapshot (if applicable).
        ip: Client IP address.
        commit: If True, commits the transaction immediately; otherwise flushes.

    Returns:
        The newly created AuditLog instance.
    """
    actor_id_str = str(actor_id) if actor_id is not None else None
    entity_id_str = str(entity_id) if entity_id is not None else None

    # Mask APAAR IDs in payloads and entity identifiers
    masked_before = mask_sensitive_data(before_json) if before_json is not None else None
    masked_after = mask_sensitive_data(after_json) if after_json is not None else None
    if entity_id_str is not None:
        entity_id_str = str(mask_sensitive_data(entity_id_str))

    # Serialize audit log appends via PostgreSQL transaction-level advisory lock
    try:
        db.execute(text("SELECT pg_advisory_xact_lock(7461937)"))
    except Exception:
        pass

    # Retrieve latest audit record to establish cryptographic chain linkage
    latest_entry = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev_hash = latest_entry.hash if latest_entry is not None else None

    # Generate timestamp and canonical hash
    ts = datetime.now(UTC)
    canonical_str = serialize_canonical_row(
        ts=ts,
        actor_id=actor_id_str,
        actor_role=actor_role,
        action=action,
        entity=entity,
        entity_id=entity_id_str,
        before_json=masked_before,
        after_json=masked_after,
        ip=ip,
    )
    row_hash = compute_hash(prev_hash, canonical_str)

    entry = AuditLog(
        ts=ts,
        actor_id=actor_id_str,
        actor_role=actor_role,
        action=action,
        entity=entity,
        entity_id=entity_id_str,
        before_json=masked_before,
        after_json=masked_after,
        ip=ip,
        prev_hash=prev_hash,
        hash=row_hash,
    )
    db.add(entry)
    db.flush()

    if commit:
        db.commit()
        db.refresh(entry)

    return entry


def verify_chain(db: Session) -> dict[str, Any]:
    """Recompute the complete audit log hash chain and verify cryptographic integrity.

    Returns a dictionary reporting:
        verified: True if the entire chain is valid, False otherwise.
        total_records: Total number of records audited.
        first_broken_id: The primary key (id) of the first broken row, or None if valid.
        broken_at_index: The 0-based sequential index of the broken row, or None.
        reason: Explanation of the failure if tampered.
        message: Human-readable status summary.
        genesis_hash: Hash of the initial record, if present.
        latest_hash: Hash of the latest record, if present.
    """
    records = db.scalars(select(AuditLog).order_by(AuditLog.id.asc())).all()

    if not records:
        return {
            "verified": True,
            "total_records": 0,
            "first_broken_id": None,
            "broken_at_index": None,
            "reason": None,
            "message": "Audit chain is empty and valid",
            "genesis_hash": None,
            "latest_hash": None,
        }

    expected_prev_hash: str | None = None

    for idx, row in enumerate(records):
        if idx == 0:
            if row.prev_hash is not None:
                return {
                    "verified": False,
                    "total_records": len(records),
                    "first_broken_id": row.id,
                    "broken_at_index": idx,
                    "reason": f"Genesis record must have prev_hash None, got '{row.prev_hash}'",
                    "message": f"Audit chain linkage broken at record id {row.id}",
                    "genesis_hash": records[0].hash,
                    "latest_hash": records[-1].hash,
                }
        else:
            if row.prev_hash != expected_prev_hash:
                return {
                    "verified": False,
                    "total_records": len(records),
                    "first_broken_id": row.id,
                    "broken_at_index": idx,
                    "reason": (
                        f"Chain linkage mismatch: expected prev_hash '{expected_prev_hash}', "
                        f"got '{row.prev_hash}'"
                    ),
                    "message": f"Audit chain linkage broken at record id {row.id}",
                    "genesis_hash": records[0].hash,
                    "latest_hash": records[-1].hash,
                }

        canonical_str = serialize_canonical_row(
            ts=row.ts,
            actor_id=row.actor_id,
            actor_role=row.actor_role,
            action=row.action,
            entity=row.entity,
            entity_id=row.entity_id,
            before_json=row.before_json,
            after_json=row.after_json,
            ip=row.ip,
        )
        recomputed_hash = compute_hash(row.prev_hash, canonical_str)

        if row.hash != recomputed_hash:
            return {
                "verified": False,
                "total_records": len(records),
                "first_broken_id": row.id,
                "broken_at_index": idx,
                "reason": (
                    f"Row content tampered: stored hash '{row.hash}' "
                    f"does not match recomputed hash '{recomputed_hash}'"
                ),
                "message": f"Audit chain integrity violation detected at record id {row.id}",
                "genesis_hash": records[0].hash,
                "latest_hash": records[-1].hash,
            }

        expected_prev_hash = row.hash

    return {
        "verified": True,
        "total_records": len(records),
        "first_broken_id": None,
        "broken_at_index": None,
        "reason": None,
        "message": "Audit log hash chain is intact and fully verified",
        "genesis_hash": records[0].hash,
        "latest_hash": records[-1].hash,
    }
