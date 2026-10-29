"""Tests for system documentation, mock vs real interface parity, and architecture specifications.

Spec: Section 4 & TASKS.md T41:
- README (run steps, demo accounts, mock vs real table)
- docs/ARCHITECTURE.md with mermaid diagrams and API overview
- docs/RULES.md generated from make rules-doc
"""

from pathlib import Path

from app.integrations.http.aicte_master import HttpAicteMasterClient
from app.integrations.http.apaar import HttpApaarClient
from app.integrations.http.identity import HttpIdentityVerifier
from app.integrations.http.otp import HttpOtpSender
from app.integrations.http.storage import HttpStorage
from app.integrations.interfaces import (
    AicteMasterClient,
    ApaarClient,
    IdentityVerifier,
    OtpSender,
    Storage,
)
from app.integrations.mock.aicte_master import MockAicteMasterClient
from app.integrations.mock.apaar import MockApaarClient
from app.integrations.mock.identity import MockIdentityVerifier
from app.integrations.mock.otp import MockOtpSender
from app.integrations.mock.storage import LocalStorage
from app.validation.codes import RULE_CATALOGUE

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_readme_exists_and_covers_required_sections() -> None:
    """Verify README.md exists and covers run steps, demo accounts, mock vs real table."""
    readme_path = REPO_ROOT / "README.md"
    assert readme_path.exists(), "README.md must exist in repo root"

    content = readme_path.read_text(encoding="utf-8")

    # Demo mode notice (Hard Rule 10)
    assert "Demo mode notice" in content
    assert "simulated" in content

    # Run steps
    assert "make up" in content
    assert "make down" in content
    assert "make seed" in content
    assert "make demo" in content
    assert "make test" in content
    assert "make lint" in content
    assert "make rules-doc" in content
    assert "Docker Compose" in content
    assert "http://localhost:8000" in content
    assert "http://localhost:5173" in content

    # Demo accounts
    assert "Demo@12345" in content
    assert "aicte_admin@aicte-india.org" in content
    assert "aicte_officer@aicte-india.org" in content
    assert "admin@piaet-pune.edu.in" in content
    assert "admin@mmit-mumbai.ac.in" in content
    assert "admin@ngec-nagpur.gov.in" in content
    assert "verifier@tcs-verifications.com" in content
    assert "111122223333" in content

    # Mock vs real table
    assert "Mock vs Real" in content
    assert "ApaarClient" in content
    assert "AicteMasterClient" in content
    assert "OtpSender" in content
    assert "IdentityVerifier" in content
    assert "Storage" in content

    # Documentation links
    assert "docs/ARCHITECTURE.md" in content
    assert "docs/RULES.md" in content
    assert "demo/DEMO.md" in content


def test_architecture_doc_exists_and_covers_specs() -> None:
    """Verify docs/ARCHITECTURE.md has system mermaid diagrams, API overview, and DPDP."""
    arch_path = REPO_ROOT / "docs" / "ARCHITECTURE.md"
    assert arch_path.exists(), "docs/ARCHITECTURE.md must exist"

    content = arch_path.read_text(encoding="utf-8")

    # Mermaid diagrams
    assert "```mermaid" in content
    assert "flowchart TD" in content
    assert "sequenceDiagram" in content

    # Validation Engine Pipeline
    assert "Validation Engine Architecture" in content
    assert "cheap-checks-first" in content

    # Anomaly Detection Subsystem
    assert "Intelligent Anomaly Detection" in content
    assert "IsolationForest" in content
    assert "ANOM_MODEL_SCORE" in content
    assert "ANOM_ENROLMENT_JUMP" in content

    # API Architecture & Endpoint Reference
    assert "REST API Architecture & Endpoint Reference" in content
    assert "/api/v1/health" in content
    assert "/api/v1/auth/login" in content
    assert "/api/v1/students/upload" in content
    assert "/api/v1/submissions/{id}/submit" in content
    assert "/api/v1/analytics/stream" in content
    assert "/api/v1/verification/verify" in content
    assert "/api/v1/audit/verify-chain" in content

    # DPDP Privacy Architecture
    assert "Digital Personal Data Protection" in content
    assert "Data Fiduciary" in content
    assert "Data Principal" in content
    assert "Data Minimisation" in content
    assert "dpo@aicte-india.org" in content


def test_rules_doc_covers_all_registered_rules() -> None:
    """Verify docs/RULES.md contains every rule from RULE_CATALOGUE."""
    rules_path = REPO_ROOT / "docs" / "RULES.md"
    assert rules_path.exists(), "docs/RULES.md must exist"

    content = rules_path.read_text(encoding="utf-8")

    assert "# APAAR Validation Rules Catalogue" in content
    assert "cheap-checks-first" in content

    for rule_code in RULE_CATALOGUE:
        assert f"`{rule_code}`" in content, f"Rule {rule_code} must appear in docs/RULES.md"


def test_mock_and_http_implementations_match_interfaces() -> None:
    """Verify all mock and http classes implement the defined integration interfaces."""
    # ApaarClient
    assert issubclass(MockApaarClient, ApaarClient)
    assert issubclass(HttpApaarClient, ApaarClient)

    # AicteMasterClient
    assert issubclass(MockAicteMasterClient, AicteMasterClient)
    assert issubclass(HttpAicteMasterClient, AicteMasterClient)

    # OtpSender
    assert issubclass(MockOtpSender, OtpSender)
    assert issubclass(HttpOtpSender, OtpSender)

    # IdentityVerifier
    assert issubclass(MockIdentityVerifier, IdentityVerifier)
    assert issubclass(HttpIdentityVerifier, IdentityVerifier)

    # Storage
    assert issubclass(LocalStorage, Storage)
    assert issubclass(HttpStorage, Storage)
