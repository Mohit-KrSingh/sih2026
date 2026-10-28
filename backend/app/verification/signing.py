"""Ed25519 cryptographic signing and canonical payload engine for student credentials.

SPEC.md section 14:
- Signed proof: each accepted or clean record gets a verification_id and an Ed25519
  signature over a canonical payload (verification_id, apaar_id hash, institution,
  course, years, status, issued_at).
- PyNaCl implementation with private key loaded from environment.
- Canonical payload deterministic serialization.
- Tamper detection: any field change in payload causes verification to fail.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

import nacl.exceptions
import nacl.signing

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_signing_key(override_key: str | bytes | None = None) -> nacl.signing.SigningKey:
    """Derive an Ed25519 SigningKey from environment or explicit key parameter.

    Handles:
    - Raw 32-byte seeds
    - 64-character hex strings
    - Arbitrary string passphrases hashed to 32 bytes via SHA-256
    """
    settings = get_settings()
    raw_key = override_key if override_key is not None else settings.ED25519_PRIVATE_KEY

    if isinstance(raw_key, bytes):
        if len(raw_key) == 32:
            return nacl.signing.SigningKey(raw_key)
        seed = hashlib.sha256(raw_key).digest()
        return nacl.signing.SigningKey(seed)

    key_str = str(raw_key).strip() if raw_key else "apaar-default-ed25519-seed"

    # Hex-encoded 32-byte seed (64 chars)
    if len(key_str) == 64:
        try:
            return nacl.signing.SigningKey(bytes.fromhex(key_str))
        except ValueError:
            pass

    # Exact 32-byte UTF-8 string
    encoded = key_str.encode("utf-8")
    if len(encoded) == 32:
        return nacl.signing.SigningKey(encoded)

    # Hash passphrase to 32-byte digest
    seed = hashlib.sha256(encoded).digest()
    return nacl.signing.SigningKey(seed)


def get_verify_key(signing_key: nacl.signing.SigningKey | None = None) -> nacl.signing.VerifyKey:
    """Return the Ed25519 VerifyKey (public key) corresponding to the signing key."""
    sk = signing_key or get_signing_key()
    return sk.verify_key


def get_public_key_hex(signing_key: nacl.signing.SigningKey | None = None) -> str:
    """Return the Ed25519 public key as a hex string."""
    return get_verify_key(signing_key).encode().hex()


def format_canonical_issued_at(ts: datetime) -> str:
    """Format a datetime to canonical UTC ISO-8601 string without microsecond jitter."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    # Strip microseconds for deterministic canonical representation
    canonical_ts = ts.astimezone(UTC).replace(microsecond=0)
    return canonical_ts.isoformat()


def build_canonical_payload(
    verification_id: str,
    apaar_id: str,
    institution: str,
    course: str,
    years: str,
    status: str,
    issued_at: datetime | str,
) -> dict[str, str]:
    """Construct the canonical credential dictionary per SPEC.md Section 14.

    Canonical payload tuple:
    (verification_id, apaar_id hash, institution, course, years, status, issued_at)

    Note:
    - Never contains raw APAAR ID; uses SHA-256 hash.
    - Fields are strictly mapped to string representations.
    """
    clean_apaar = str(apaar_id).strip()
    apaar_id_hash = hashlib.sha256(clean_apaar.encode("utf-8")).hexdigest()

    if isinstance(issued_at, datetime):
        issued_at_str = format_canonical_issued_at(issued_at)
    else:
        issued_at_str = str(issued_at).strip()

    return {
        "apaar_id_hash": apaar_id_hash,
        "course": str(course).strip(),
        "institution": str(institution).strip(),
        "issued_at": issued_at_str,
        "status": str(status).strip(),
        "verification_id": str(verification_id).strip(),
        "years": str(years).strip(),
    }


def serialize_canonical_payload(payload: dict[str, str]) -> bytes:
    """Serialize the canonical payload dictionary into deterministic bytes.

    Uses sorted keys, no whitespace separators, and ensure_ascii=True to guarantee
    exact byte-level reproducibility across platforms.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def sign_payload(
    payload: dict[str, str],
    signing_key: nacl.signing.SigningKey | None = None,
) -> str:
    """Sign the canonical payload with Ed25519 and return signature as a hex string (128 chars)."""
    sk = signing_key or get_signing_key()
    serialized = serialize_canonical_payload(payload)
    signed = sk.sign(serialized)
    return signed.signature.hex()


def verify_signature(
    payload: dict[str, str],
    signature_hex: str,
    verify_key: nacl.signing.VerifyKey | None = None,
) -> bool:
    """Verify an Ed25519 signature against the canonical payload.

    Returns:
    - True if signature is cryptographically valid and matches canonical payload.
    - False if signature is invalid or any field in payload has been modified/tampered.
    """
    vk = verify_key or get_verify_key()
    try:
        sig_bytes = bytes.fromhex(signature_hex.strip())
        serialized = serialize_canonical_payload(payload)
        vk.verify(serialized, sig_bytes)
        return True
    except (nacl.exceptions.BadSignatureError, ValueError, TypeError) as e:
        logger.warning("Cryptographic signature verification failed: %s", e)
        return False
