"""HTTP stub for external National Identity & Signatory Verification API."""

from app.integrations.interfaces import IdentityVerificationResult, IdentityVerifier


class HttpIdentityVerifier(IdentityVerifier):
    """Production HTTP client for the official signatory identity verification gateway.

    Stub raising NotImplementedError per SPEC.md section 2.5 and 18.
    """

    def __init__(self, endpoint_url: str | None = None, api_key: str | None = None) -> None:
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    def verify_signatory(
        self,
        name: str,
        signatory_ref: str,
        institution_aicte_id: str,
    ) -> IdentityVerificationResult:
        raise NotImplementedError(
            "Real IdentityVerifier HTTP gateway is not implemented in demo mode. "
            "Set IDENTITY_VERIFIER_TYPE='mock' in configuration or environment."
        )

    def verify_identity(self, name: str, id_reference: str) -> IdentityVerificationResult:
        raise NotImplementedError(
            "Real IdentityVerifier HTTP gateway is not implemented in demo mode. "
            "Set IDENTITY_VERIFIER_TYPE='mock' in configuration or environment."
        )
