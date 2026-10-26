"""HTTP stub for official AICTE Master Registry API."""

from app.integrations.interfaces import (
    AicteCourseInfo,
    AicteInstitutionInfo,
    AicteMasterClient,
)


class HttpAicteMasterClient(AicteMasterClient):
    """Production HTTP client for the official AICTE Master List API.

    Stub raising NotImplementedError per SPEC.md section 2.5 and 18.
    """

    def __init__(self, endpoint_url: str | None = None, api_key: str | None = None) -> None:
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    def get_institution(self, aicte_id: str) -> AicteInstitutionInfo | None:
        raise NotImplementedError(
            "Real AicteMasterClient HTTP client is not implemented in demo mode. "
            "Set AICTE_MASTER_CLIENT_TYPE='mock' in configuration or environment."
        )

    def list_institutions(self) -> list[AicteInstitutionInfo]:
        raise NotImplementedError(
            "Real AicteMasterClient HTTP client is not implemented in demo mode. "
            "Set AICTE_MASTER_CLIENT_TYPE='mock' in configuration or environment."
        )

    def get_courses(self, aicte_id: str) -> list[AicteCourseInfo]:
        raise NotImplementedError(
            "Real AicteMasterClient HTTP client is not implemented in demo mode. "
            "Set AICTE_MASTER_CLIENT_TYPE='mock' in configuration or environment."
        )
