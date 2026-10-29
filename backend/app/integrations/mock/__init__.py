"""Mock integration implementations."""

from app.integrations.mock.aicte_master import MockAicteMasterClient
from app.integrations.mock.apaar import MockApaarClient
from app.integrations.mock.identity import MockIdentityVerifier
from app.integrations.mock.otp import MockOtpSender
from app.integrations.mock.storage import LocalStorage, MockStorage

__all__ = [
    "MockApaarClient",
    "MockAicteMasterClient",
    "MockOtpSender",
    "MockIdentityVerifier",
    "MockStorage",
    "LocalStorage",
]
