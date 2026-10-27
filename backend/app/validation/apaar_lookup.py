"""APAAR batched lookup helper for validation rules.

Per SPEC.md Section 9.3 & 9.4:
- APAAR lookups are batched: one call per validation run across all rows.
- Cheap checks first: rows with format-invalid APAAR IDs are skipped before registry lookup.
- Results are cached in ValidationContext.apaar_cache across all APAAR rules.
"""

from __future__ import annotations

import re
from typing import Any

from app.integrations.interfaces import ApaarClient, ApaarRecord

APAAR_REGEX = re.compile(r"^\d{12}$")


def get_apaar_cache(context: Any) -> dict[str, ApaarRecord | None]:
    """Retrieve or populate APAAR registry records in a single batched lookup per run."""
    # Ensure context.apaar_cache is a dict
    if not hasattr(context, "apaar_cache") or context.apaar_cache is None:
        context.apaar_cache = {}

    # Collect distinct valid 12-digit APAAR IDs across all rows
    valid_ids: set[str] = set()
    rows = context.get_all_rows() if hasattr(context, "get_all_rows") else []
    for row in rows:
        val = (
            context.get_field_value(row, "apaar_id")
            if hasattr(context, "get_field_value")
            else (row.get("apaar_id") if isinstance(row, dict) else getattr(row, "apaar_id", None))
        )
        if val is not None:
            s_val = str(val).strip()
            if APAAR_REGEX.match(s_val):
                valid_ids.add(s_val)

    if not valid_ids:
        return context.apaar_cache

    # Determine which IDs are not yet in context.apaar_cache
    missing_ids = [aid for aid in valid_ids if aid not in context.apaar_cache]
    if not missing_ids:
        return context.apaar_cache

    # Resolve ApaarClient
    client: ApaarClient | None = getattr(context, "apaar_client", None)
    if client is None:
        extra = getattr(context, "extra", {}) or {}
        session = extra.get("db_session") or extra.get("session") or extra.get("db")
        try:
            from app.integrations.factory import get_apaar_client

            client = get_apaar_client(session=session)
        except Exception:
            client = None

    if client is not None:
        batch_results = client.lookup_batch(missing_ids)
        context.apaar_cache.update(batch_results)
    else:
        for aid in missing_ids:
            context.apaar_cache[aid] = None

    return context.apaar_cache
