"""Reset database to the scripted demo state for make demo.

TASKS.md T40 / SPEC.md Section 18:
- Truncates ALL transactional tables in dependency order.
- Preserves the Alembic migration version table.
- Re-runs the idempotent seed script to rebuild demo data.
- Clears Redis caches (OTP, rate limits, idempotency keys).
- Generates demo CSVs in demo/.

Usage:
    PYTHONPATH=backend python scripts/demo_reset.py
"""

import sys

sys.path.insert(0, "backend")

from sqlalchemy import text

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_redis
from app.seed import seed_all

# Tables in safe truncation order (children before parents).
# We TRUNCATE CASCADE to handle FK dependencies cleanly.
TABLES_TO_TRUNCATE = [
    # Leaf tables first
    "dev_outbox",
    "anomaly_scores",
    "rule_config",
    "api_keys",
    "audit_log",
    "consent_requests",
    "verified_records",
    "notifications",
    "change_requests",
    "queries",
    "review_items",
    "justifications",
    "validation_flags",
    "uploads",
    "students",
    "submissions",
    "seat_declarations",
    "correction_requests",
    "activation_requests",
    "course_intake_history",
    "course_intake",
    "courses",
    "verifiers",
    "users",
    "mock_apaar_registry",
    "institutions",
]


def reset_database(session: Session | None = None) -> None:
    """Truncate all application tables and flush Redis."""
    settings = get_settings()
    close_db = False
    if session is None:
        db = SessionLocal()
        close_db = True
    else:
        db = session

    print("=== EduTrace Demo Reset ===")
    print()
    print("-> Truncating all application tables...")
    try:
        # Use a single TRUNCATE CASCADE statement for speed and atomicity
        table_list = ", ".join(TABLES_TO_TRUNCATE)
        db.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
        db.commit()
        print(f"   Truncated {len(TABLES_TO_TRUNCATE)} tables.")
    except Exception as e:
        db.rollback()
        print(f"   TRUNCATE failed ({e}), falling back to individual DELETEs...")
        for table in TABLES_TO_TRUNCATE:
            try:
                db.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass
        db.commit()
    finally:
        if close_db:
            db.close()

    # Flush Redis completely
    print("-> Flushing Redis (OTP, rate limits, idempotency keys)...")
    try:
        r = next(get_redis())
        r.flushdb()
        print("   Redis flushed.")
    except Exception as e:
        print(f"   Redis flush warning: {e}")

    print()


def main() -> None:
    """Full demo reset: truncate -> seed -> done."""
    reset_database()

    print("-> Re-seeding database with demo data...")
    print()
    summary = seed_all()
    print()
    print("=== Demo state ready ===")
    print()
    print("Demo accounts (all passwords: Demo@12345):")
    print("  AICTE Admin:    aicte_admin@aicte-india.org")
    print("  AICTE Officer:  aicte_officer@aicte-india.org")
    print("  College 1:      admin@piaet-pune.edu.in      (Clean submitted)")
    print("  College 2:      admin@mmit-mumbai.ac.in       (Exceptions: over-intake)")
    print("  College 3:      admin@ngec-nagpur.gov.in      (Draft)")
    print("  Verifier:       verifier@tcs-verifications.com")
    print("  Student APAAR:  111122223333  (Aarav Sharma)")
    print("  Dupe Student:   555566667777  (Priya Patel)")
    print("  Valid VID:      VR-2025-111122223333")
    print("  Tampered VID:   VR-TAMPERED-DEMO")
    print()
    print("Follow demo/DEMO.md for the click-by-click walkthrough.")


if __name__ == "__main__":
    main()
