"""Unit and integration tests for integration interfaces, mocks, and factories.

Covers:
- ApaarClient: MockApaarClient (single and batched lookups, in-memory and DB backed)
- AicteMasterClient: MockAicteMasterClient (30 colleges, 8 states, courses, intake)
- OtpSender: MockOtpSender (dev_outbox persistence, filtering, in-memory mode)
- IdentityVerifier: MockIdentityVerifier (signatory and individual verification)
- Storage: MockStorage and LocalStorage (CRUD, URLs, traversal prevention)
- HTTP Stubs: All methods raise NotImplementedError
- Factories: Config-driven client selection
- Dev API: /api/v1/dev/outbox listing, filtering, and production lock
"""

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.integrations.factory import (
    get_aicte_master_client,
    get_apaar_client,
    get_identity_verifier,
    get_otp_sender,
    get_storage,
)
from app.integrations.http import (
    HttpAicteMasterClient,
    HttpApaarClient,
    HttpIdentityVerifier,
    HttpOtpSender,
    HttpStorage,
)
from app.integrations.interfaces import (
    AicteMasterClient,
    ApaarClient,
    IdentityVerifier,
    OtpSender,
    Storage,
)
from app.integrations.mock import (
    LocalStorage,
    MockAicteMasterClient,
    MockApaarClient,
    MockIdentityVerifier,
    MockOtpSender,
    MockStorage,
)
from app.main import app
from app.models import DevOutbox, MockApaarRegistry

# ---------------------------------------------------------------------------
# ApaarClient Tests
# ---------------------------------------------------------------------------


def test_mock_apaar_client_in_memory():
    """Verify in-memory ApaarClient lookups without database session."""
    client = MockApaarClient()
    rec1 = client.add_record(
        "123456789012", "Aarav Sharma", date(2003, 5, 14), "Male", persist_to_db=False
    )
    rec2 = client.add_record(
        "987654321098", "Diya Patel", date(2004, 11, 23), "Female", persist_to_db=False
    )

    assert isinstance(client, ApaarClient)
    assert client.lookup("123456789012") == rec1
    assert client.lookup("987654321098") == rec2
    assert client.lookup("000000000000") is None


def test_mock_apaar_client_batch_lookup(db_session):
    """Verify batched lookup querying mock_apaar_registry in database."""
    client = MockApaarClient(session=db_session)
    client.add_record("111122223333", "Rohan Gupta", date(2002, 1, 10), "Male")
    client.add_record("444455556666", "Ananya Verma", date(2003, 7, 19), "Female")

    # Verify rows exist in DB table
    db_records = db_session.scalars(select(MockApaarRegistry)).all()
    assert len(db_records) >= 2

    # Batched lookup with both present and absent IDs
    requested_ids = ["111122223333", "444455556666", "999999999999", "000000000000"]
    batch_results = client.lookup_batch(requested_ids)

    assert len(batch_results) == 4
    assert batch_results["111122223333"] is not None
    assert batch_results["111122223333"].name == "Rohan Gupta"
    assert batch_results["444455556666"] is not None
    assert batch_results["444455556666"].name == "Ananya Verma"
    assert batch_results["999999999999"] is None
    assert batch_results["000000000000"] is None


def test_mock_apaar_client_empty_batch():
    """Verify empty batched lookup returns empty dict without errors."""
    client = MockApaarClient()
    assert client.lookup_batch([]) == {}


# ---------------------------------------------------------------------------
# AicteMasterClient Tests
# ---------------------------------------------------------------------------


def test_mock_aicte_master_client_30_colleges():
    """Verify MockAicteMasterClient provides exactly 30 colleges across 8 states."""
    client = MockAicteMasterClient()
    assert isinstance(client, AicteMasterClient)

    colleges = client.list_institutions()
    assert len(colleges) == 30

    states = {c.state for c in colleges}
    expected_states = {
        "Maharashtra",
        "Karnataka",
        "Tamil Nadu",
        "Uttar Pradesh",
        "Delhi",
        "Gujarat",
        "West Bengal",
        "Telangana",
    }
    assert states == expected_states

    for college in colleges:
        assert college.aicte_id.startswith("1-")
        assert len(college.name) > 0
        assert college.official_email.endswith((".edu.in", ".ac.in", ".gov.in"))
        assert 2 <= len(college.courses) <= 5
        for course in college.courses:
            assert course.approved_intake in (60, 120, 180)
            assert course.level in ("UG", "PG", "Diploma", "PGDM")
            if course.supernumerary_allowed:
                assert course.supernumerary_seats_allowed > 0


def test_mock_aicte_master_client_get_institution():
    """Verify single institution retrieval and course listing."""
    client = MockAicteMasterClient()
    inst = client.get_institution("1-10000001")
    assert inst is not None
    assert inst.name == "Pune Institute of Advanced Engineering & Technology"
    assert inst.state == "Maharashtra"
    assert inst.district == "Pune"
    assert inst.approval_status == "active"

    courses = client.get_courses("1-10000001")
    assert len(courses) == 4
    assert courses[0].name == "Computer Science and Engineering"

    # Non-existent institution
    assert client.get_institution("1-99999999") is None
    assert client.get_courses("1-99999999") == []


def test_mock_aicte_master_client_approval_statuses():
    """Verify presence of suspended and expired colleges for testing edge cases."""
    client = MockAicteMasterClient()
    colleges = client.list_institutions()
    statuses = {c.approval_status for c in colleges}
    assert "active" in statuses
    assert "suspended" in statuses
    assert "expired" in statuses


# ---------------------------------------------------------------------------
# OtpSender Tests
# ---------------------------------------------------------------------------


def test_mock_otp_sender_writes_to_dev_outbox(db_session):
    """Verify MockOtpSender writes to dev_outbox table in PostgreSQL."""
    sender = MockOtpSender(session=db_session)
    assert isinstance(sender, OtpSender)

    # Send OTP
    success = sender.send_otp(
        channel="otp",
        recipient="principal@piaet-pune.edu.in",
        code="784920",
        context="Activation claim",
    )
    assert success is True

    # Send Notification
    sender.send_notification(
        channel="email",
        recipient="registrar@bnits-blr.edu.in",
        body="Intake updated for 2026-27.",
    )

    # Query outbox
    messages = sender.get_messages()
    assert len(messages) == 2
    assert "784920" in messages[0].body
    assert messages[0].recipient == "principal@piaet-pune.edu.in"
    assert messages[1].recipient == "registrar@bnits-blr.edu.in"

    # Filter by recipient
    filtered = sender.get_messages(recipient="principal@piaet-pune.edu.in")
    assert len(filtered) == 1
    assert filtered[0].channel == "otp"

    # Verify persistence in actual database table
    db_rows = db_session.scalars(select(DevOutbox)).all()
    assert len(db_rows) == 2

    # Clear outbox
    sender.clear()
    assert len(sender.get_messages()) == 0
    assert len(db_session.scalars(select(DevOutbox)).all()) == 0


def test_mock_otp_sender_in_memory():
    """Verify in-memory outbox when session is None."""
    sender = MockOtpSender(session=None)
    sender.send_otp("sms", "9876543210", "123456")
    messages = sender.get_messages()
    assert len(messages) == 1
    assert "123456" in messages[0].body


# ---------------------------------------------------------------------------
# IdentityVerifier Tests
# ---------------------------------------------------------------------------


def test_mock_identity_verifier():
    """Verify MockIdentityVerifier for valid and invalid credentials."""
    verifier = MockIdentityVerifier()
    assert isinstance(verifier, IdentityVerifier)

    # Valid signatory
    result = verifier.verify_signatory(
        name="Dr. Rajesh Deshmukh",
        signatory_ref="AUTH-DOC-2026-001",
        institution_aicte_id="1-10000001",
    )
    assert result.verified is True
    assert result.confidence >= 0.9
    assert result.reference_id.startswith("MOCK-SIG-VERIF-")

    # Invalid / reject signatory
    reject_result = verifier.verify_signatory(
        name="Dr. Rajesh Deshmukh",
        signatory_ref="INVALID-DOC-REF",
        institution_aicte_id="1-10000001",
    )
    assert reject_result.verified is False
    assert reject_result.confidence < 0.5

    # Empty signatory details
    empty_result = verifier.verify_signatory("", "", "1-10000001")
    assert empty_result.verified is False

    # Individual identity verification
    id_result = verifier.verify_identity("Aarav Sharma", "APAAR-REF-100")
    assert id_result.verified is True
    assert id_result.reference_id.startswith("MOCK-ID-VERIF-")


# ---------------------------------------------------------------------------
# Storage Tests
# ---------------------------------------------------------------------------


def test_mock_storage():
    """Verify in-memory MockStorage."""
    storage = MockStorage()
    assert isinstance(storage, Storage)

    sample_bytes = b"%PDF-1.4 Mock document bytes"
    path = "authorisation_letters/1-10000001_auth.pdf"

    saved_ref = storage.save(path, sample_bytes, "application/pdf")
    assert storage.exists(saved_ref) is True
    assert storage.get(saved_ref) == sample_bytes
    assert storage.get_url(saved_ref) == f"/api/v1/storage/{path}"

    assert storage.delete(saved_ref) is True
    assert storage.exists(saved_ref) is False

    with pytest.raises(FileNotFoundError):
        storage.get(saved_ref)


def test_local_storage(tmp_path: Path):
    """Verify LocalStorage saving to local disk volume."""
    storage = LocalStorage(base_dir=str(tmp_path))
    assert isinstance(storage, Storage)

    content = b"sample justification attachment"
    path = "justifications/flag_42.txt"

    saved_ref = storage.save(path, content, "text/plain")
    assert storage.exists(saved_ref) is True
    assert storage.get(saved_ref) == content

    # Check physical file exists on disk
    assert (tmp_path / "justifications" / "flag_42.txt").is_file()

    assert storage.delete(saved_ref) is True
    assert storage.exists(saved_ref) is False

    # Path traversal attack protection
    with pytest.raises(ValueError, match="Path traversal detected"):
        storage.save("../../etc/passwd", b"evil")


# ---------------------------------------------------------------------------
# HTTP Stub Tests (NotImplementedError)
# ---------------------------------------------------------------------------


def test_http_stubs_raise_not_implemented():
    """Verify all real HTTP stubs raise NotImplementedError with clear instructions."""
    apaar_http = HttpApaarClient()
    with pytest.raises(
        NotImplementedError, match="Real ApaarClient HTTP client is not implemented"
    ):
        apaar_http.lookup("123456789012")
    with pytest.raises(
        NotImplementedError, match="Real ApaarClient HTTP client is not implemented"
    ):
        apaar_http.lookup_batch(["123456789012"])

    aicte_http = HttpAicteMasterClient()
    with pytest.raises(
        NotImplementedError, match="Real AicteMasterClient HTTP client is not implemented"
    ):
        aicte_http.get_institution("1-10000001")
    with pytest.raises(
        NotImplementedError, match="Real AicteMasterClient HTTP client is not implemented"
    ):
        aicte_http.list_institutions()
    with pytest.raises(
        NotImplementedError, match="Real AicteMasterClient HTTP client is not implemented"
    ):
        aicte_http.get_courses("1-10000001")

    otp_http = HttpOtpSender()
    with pytest.raises(NotImplementedError, match="Real OtpSender HTTP gateway is not implemented"):
        otp_http.send_otp("otp", "test@example.com", "123456")
    with pytest.raises(NotImplementedError, match="Real OtpSender HTTP gateway is not implemented"):
        otp_http.send_notification("email", "test@example.com", "hello")

    id_http = HttpIdentityVerifier()
    with pytest.raises(
        NotImplementedError, match="Real IdentityVerifier HTTP gateway is not implemented"
    ):
        id_http.verify_signatory("Name", "REF", "1-10000001")
    with pytest.raises(
        NotImplementedError, match="Real IdentityVerifier HTTP gateway is not implemented"
    ):
        id_http.verify_identity("Name", "REF")

    storage_http = HttpStorage()
    with pytest.raises(
        NotImplementedError, match="Real S3/Cloud Storage client is not implemented"
    ):
        storage_http.save("file.txt", b"data")


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------


def test_factory_switches(monkeypatch):
    """Verify factories switch between Mock and HTTP implementations based on config."""
    # Test Mock defaults
    assert isinstance(get_apaar_client(), MockApaarClient)
    assert isinstance(get_aicte_master_client(), MockAicteMasterClient)
    assert isinstance(get_otp_sender(), MockOtpSender)
    assert isinstance(get_identity_verifier(), MockIdentityVerifier)
    assert isinstance(get_storage(), MockStorage)

    # Test HTTP switches via settings overrides
    monkeypatch.setattr(
        "app.integrations.factory.get_settings",
        lambda: Settings(
            APAAR_CLIENT_TYPE="http",
            AICTE_MASTER_CLIENT_TYPE="http",
            OTP_SENDER_TYPE="http",
            IDENTITY_VERIFIER_TYPE="http",
            STORAGE_TYPE="http",
        ),
    )
    assert isinstance(get_apaar_client(), HttpApaarClient)
    assert isinstance(get_aicte_master_client(), HttpAicteMasterClient)
    assert isinstance(get_otp_sender(), HttpOtpSender)
    assert isinstance(get_identity_verifier(), HttpIdentityVerifier)
    assert isinstance(get_storage(), HttpStorage)


# ---------------------------------------------------------------------------
# Dev Route API Tests (/api/v1/dev/outbox)
# ---------------------------------------------------------------------------


def test_dev_outbox_api_endpoint(client: TestClient, db_session):
    """Verify GET /api/v1/dev/outbox lists messages and supports filtering."""
    sender = MockOtpSender(session=db_session)
    sender.clear()
    sender.send_otp("otp", "applicant@college.edu", "654321", "Signatory verify")
    sender.send_notification("email", "admin@college.edu", "Account approved")
    db_session.commit()

    # Query all
    response = client.get("/api/v1/dev/outbox")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    recipients = {i["recipient"] for i in items}
    assert "applicant@college.edu" in recipients
    assert "admin@college.edu" in recipients

    # Filter by channel
    otp_resp = client.get("/api/v1/dev/outbox?channel=otp")
    assert otp_resp.status_code == 200
    otp_items = otp_resp.json()
    assert len(otp_items) == 1
    assert otp_items[0]["recipient"] == "applicant@college.edu"

    # Send helper endpoint
    send_resp = client.post(
        "/api/v1/dev/otp/send",
        json={
            "channel": "sms",
            "recipient": "9811122233",
            "code": "998877",
            "context": "Phone verify",
        },
    )
    assert send_resp.status_code == 201

    # Check that new message is listed
    sms_resp = client.get("/api/v1/dev/outbox?recipient=9811122233")
    assert sms_resp.status_code == 200
    sms_items = sms_resp.json()
    assert len(sms_items) == 1
    assert "998877" in sms_items[0]["body"]

    # Clear endpoint
    del_resp = client.delete("/api/v1/dev/outbox")
    assert del_resp.status_code == 200
    assert del_resp.json()["cleared"] >= 3

    empty_resp = client.get("/api/v1/dev/outbox")
    assert empty_resp.status_code == 200
    assert len(empty_resp.json()) == 0


def test_dev_outbox_api_blocked_in_production(monkeypatch):
    """Verify dev outbox returns 403 Forbidden in production environment."""
    monkeypatch.setattr(
        "app.api_v1.dev.get_settings",
        lambda: Settings(ENV="production", DEMO_MODE=False),
    )
    test_client = TestClient(app)
    response = test_client.get("/api/v1/dev/outbox")
    assert response.status_code == 403
    assert "Dev endpoints are disabled in production" in response.json()["detail"]
