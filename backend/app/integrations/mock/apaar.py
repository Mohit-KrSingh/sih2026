"""Mock implementation of ApaarClient.

SPEC.md section 18:
MockApaarClient reads mock_apaar_registry table. Supports single and batched lookups.
"""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.interfaces import ApaarClient, ApaarRecord
from app.models import MockApaarRegistry


class MockApaarClient(ApaarClient):
    """Simulated APAAR client backed by mock_apaar_registry table with in-memory fallback."""

    def __init__(
        self,
        session: Session | None = None,
        initial_records: Sequence[ApaarRecord] | None = None,
    ) -> None:
        self.session = session
        self._in_memory_records: dict[str, ApaarRecord] = {}
        if initial_records:
            for rec in initial_records:
                self._in_memory_records[rec.apaar_id] = rec

    def add_record(
        self,
        apaar_id: str,
        name: str,
        dob: date,
        gender: str,
        persist_to_db: bool = True,
    ) -> ApaarRecord:
        """Register an APAAR identity in the mock registry."""
        record = ApaarRecord(apaar_id=apaar_id, name=name, dob=dob, gender=gender)
        self._in_memory_records[apaar_id] = record

        if persist_to_db and self.session is not None:
            existing = self.session.scalar(
                select(MockApaarRegistry).where(MockApaarRegistry.apaar_id == apaar_id)
            )
            if existing:
                existing.name = name
                existing.dob = dob
                existing.gender = gender
            else:
                db_entry = MockApaarRegistry(
                    apaar_id=apaar_id,
                    name=name,
                    dob=dob,
                    gender=gender,
                )
                self.session.add(db_entry)
            self.session.flush()

        return record

    def lookup(self, apaar_id: str) -> ApaarRecord | None:
        """Fetch a single record by 12-digit APAAR ID."""
        if self.session is not None:
            db_entry = self.session.scalar(
                select(MockApaarRegistry).where(MockApaarRegistry.apaar_id == apaar_id)
            )
            if db_entry is not None:
                return ApaarRecord(
                    apaar_id=db_entry.apaar_id,
                    name=db_entry.name,
                    dob=db_entry.dob,
                    gender=db_entry.gender,
                )

        return self._in_memory_records.get(apaar_id)

    def lookup_batch(self, apaar_ids: list[str]) -> dict[str, ApaarRecord | None]:
        """Fetch multiple APAAR records in a single query."""
        results: dict[str, ApaarRecord | None] = {aid: None for aid in apaar_ids}
        if not apaar_ids:
            return results

        if self.session is not None:
            # Query in batches or all together
            stmt = select(MockApaarRegistry).where(MockApaarRegistry.apaar_id.in_(apaar_ids))
            db_entries = self.session.scalars(stmt).all()
            for entry in db_entries:
                results[entry.apaar_id] = ApaarRecord(
                    apaar_id=entry.apaar_id,
                    name=entry.name,
                    dob=entry.dob,
                    gender=entry.gender,
                )

        # Check in-memory for any unresolved
        for aid in apaar_ids:
            if results[aid] is None and aid in self._in_memory_records:
                results[aid] = self._in_memory_records[aid]

        return results
