"""HTTP stub integration implementations."""

from app.integrations.http.aicte_master import HttpAicteMasterClient
from app.integrations.http.apaar import HttpApaarClient
from app.integrations.http.identity import HttpIdentityVerifier
from app.integrations.http.otp import HttpOtpSender
from app.integrations.http.storage import HttpStorage

__all__ = [
    "HttpApaarClient",
    "HttpAicteMasterClient",
    "HttpOtpSender",
    "HttpIdentityVerifier",
    "HttpStorage",
]
