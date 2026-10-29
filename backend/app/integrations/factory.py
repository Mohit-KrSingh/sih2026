"""Factories for external integration clients.

Switches between mock implementations and HTTP stubs based on configuration.
"""

from sqlalchemy.orm import Session

from app.config import get_settings
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


def get_apaar_client(session: Session | None = None) -> ApaarClient:
    """Resolve ApaarClient based on APAAR_CLIENT_TYPE config."""
    client_type = get_settings().APAAR_CLIENT_TYPE.lower()
    if client_type == "mock":
        return MockApaarClient(session=session)
    if client_type == "http":
        return HttpApaarClient()
    raise ValueError(f"Unknown APAAR_CLIENT_TYPE: {client_type}")


def get_aicte_master_client() -> AicteMasterClient:
    """Resolve AicteMasterClient based on AICTE_MASTER_CLIENT_TYPE config."""
    client_type = get_settings().AICTE_MASTER_CLIENT_TYPE.lower()
    if client_type == "mock":
        return MockAicteMasterClient()
    if client_type == "http":
        return HttpAicteMasterClient()
    raise ValueError(f"Unknown AICTE_MASTER_CLIENT_TYPE: {client_type}")


def get_otp_sender(session: Session | None = None) -> OtpSender:
    """Resolve OtpSender based on OTP_SENDER_TYPE config."""
    client_type = get_settings().OTP_SENDER_TYPE.lower()
    if client_type == "mock":
        return MockOtpSender(session=session)
    if client_type == "http":
        return HttpOtpSender()
    raise ValueError(f"Unknown OTP_SENDER_TYPE: {client_type}")


def get_identity_verifier() -> IdentityVerifier:
    """Resolve IdentityVerifier based on IDENTITY_VERIFIER_TYPE config."""
    client_type = get_settings().IDENTITY_VERIFIER_TYPE.lower()
    if client_type == "mock":
        return MockIdentityVerifier()
    if client_type == "http":
        return HttpIdentityVerifier()
    raise ValueError(f"Unknown IDENTITY_VERIFIER_TYPE: {client_type}")


_mock_storage_instance = MockStorage()


def get_storage() -> Storage:
    """Resolve Storage based on STORAGE_TYPE config."""
    client_type = get_settings().STORAGE_TYPE.lower()
    if client_type == "mock":
        return _mock_storage_instance
    if client_type == "local":
        return LocalStorage(get_settings().STORAGE_DIR)
    if client_type == "http":
        return HttpStorage()
    raise ValueError(f"Unknown STORAGE_TYPE: {client_type}")
