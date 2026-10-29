"""External integration interfaces, mock implementations, and factories."""

from app.integrations.factory import (
    get_aicte_master_client,
    get_apaar_client,
    get_identity_verifier,
    get_otp_sender,
    get_storage,
)
from app.integrations.interfaces import (
    AicteCourseInfo,
    AicteInstitutionInfo,
    AicteMasterClient,
    ApaarClient,
    ApaarRecord,
    IdentityVerificationResult,
    IdentityVerifier,
    OtpSender,
    OutboxMessage,
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

__all__ = [
    # Interfaces & data classes
    "ApaarClient",
    "ApaarRecord",
    "AicteMasterClient",
    "AicteInstitutionInfo",
    "AicteCourseInfo",
    "OtpSender",
    "OutboxMessage",
    "IdentityVerifier",
    "IdentityVerificationResult",
    "Storage",
    # Mocks
    "MockApaarClient",
    "MockAicteMasterClient",
    "MockOtpSender",
    "MockIdentityVerifier",
    "MockStorage",
    "LocalStorage",
    # Factories
    "get_apaar_client",
    "get_aicte_master_client",
    "get_otp_sender",
    "get_identity_verifier",
    "get_storage",
]
