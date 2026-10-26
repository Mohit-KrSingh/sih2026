"""Mock implementation of IdentityVerifier.

SPEC.md section 11 & 18:
Mock signatory identity check and institutional authority verification.
"""

import uuid

from app.integrations.interfaces import IdentityVerificationResult, IdentityVerifier


class MockIdentityVerifier(IdentityVerifier):
    """Simulated identity verifier for college signatories and heads."""

    def verify_signatory(
        self,
        name: str,
        signatory_ref: str,
        institution_aicte_id: str,
    ) -> IdentityVerificationResult:
        """Verify the legal authority of an institutional signatory."""
        normalized_name = name.strip()
        normalized_ref = signatory_ref.strip()

        if not normalized_name or not normalized_ref:
            return IdentityVerificationResult(
                verified=False,
                confidence=0.0,
                details="Signatory name and reference document are required.",
                reference_id="",
            )

        if "INVALID" in normalized_ref.upper() or "REJECT" in normalized_name.upper():
            return IdentityVerificationResult(
                verified=False,
                confidence=0.1,
                details=(
                    "Identity verification failed: document reference could "
                    "not be validated against official records."
                ),
                reference_id="",
            )

        ref_id = f"MOCK-SIG-VERIF-{uuid.uuid4().hex[:10].upper()}"
        return IdentityVerificationResult(
            verified=True,
            confidence=0.98,
            details=(
                f"Signatory '{normalized_name}' successfully verified for "
                f"institution '{institution_aicte_id}'."
            ),
            reference_id=ref_id,
        )

    def verify_identity(self, name: str, id_reference: str) -> IdentityVerificationResult:
        """Verify identity of an individual using reference credentials."""
        normalized_name = name.strip()
        normalized_ref = id_reference.strip()

        if not normalized_name or not normalized_ref:
            return IdentityVerificationResult(
                verified=False,
                confidence=0.0,
                details="Name and ID reference are required.",
                reference_id="",
            )

        if "INVALID" in normalized_ref.upper() or "REJECT" in normalized_name.upper():
            return IdentityVerificationResult(
                verified=False,
                confidence=0.1,
                details="Identity verification rejected: invalid credentials.",
                reference_id="",
            )

        ref_id = f"MOCK-ID-VERIF-{uuid.uuid4().hex[:10].upper()}"
        return IdentityVerificationResult(
            verified=True,
            confidence=0.99,
            details=f"Individual '{normalized_name}' successfully verified.",
            reference_id=ref_id,
        )
