"""HTTP stub for external APAAR Registry API."""

from app.integrations.interfaces import ApaarClient, ApaarRecord


class HttpApaarClient(ApaarClient):
    """Production HTTP client for the official national APAAR ID registry.

    Stub raising NotImplementedError per SPEC.md section 2.5 and 18.
    """

    def __init__(self, endpoint_url: str | None = None, api_key: str | None = None) -> None:
        self.endpoint_url = endpoint_url
        self.api_key = api_key

    def lookup(self, apaar_id: str) -> ApaarRecord | None:
        raise NotImplementedError(
            "Real ApaarClient HTTP client is not implemented in demo mode. "
            "Set APAAR_CLIENT_TYPE='mock' in configuration or environment."
        )

    def lookup_batch(self, apaar_ids: list[str]) -> dict[str, ApaarRecord | None]:
        raise NotImplementedError(
            "Real ApaarClient HTTP client is not implemented in demo mode. "
            "Set APAAR_CLIENT_TYPE='mock' in configuration or environment."
        )
