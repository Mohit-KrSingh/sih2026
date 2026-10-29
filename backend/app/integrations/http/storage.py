"""HTTP stub for remote Cloud/MinIO/S3 object storage."""

from app.integrations.interfaces import Storage


class HttpStorage(Storage):
    """Production client for S3/MinIO cloud object storage.

    Stub raising NotImplementedError per SPEC.md section 2.5 and 18.
    """

    def __init__(self, endpoint_url: str | None = None, bucket_name: str | None = None) -> None:
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name

    def save(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        raise NotImplementedError(
            "Real S3/Cloud Storage client is not implemented in demo mode. "
            "Set STORAGE_TYPE='mock' or 'local' in configuration or environment."
        )

    def get(self, path: str) -> bytes:
        raise NotImplementedError(
            "Real S3/Cloud Storage client is not implemented in demo mode. "
            "Set STORAGE_TYPE='mock' or 'local' in configuration or environment."
        )

    def exists(self, path: str) -> bool:
        raise NotImplementedError(
            "Real S3/Cloud Storage client is not implemented in demo mode. "
            "Set STORAGE_TYPE='mock' or 'local' in configuration or environment."
        )

    def delete(self, path: str) -> bool:
        raise NotImplementedError(
            "Real S3/Cloud Storage client is not implemented in demo mode. "
            "Set STORAGE_TYPE='mock' or 'local' in configuration or environment."
        )

    def get_url(self, path: str) -> str:
        raise NotImplementedError(
            "Real S3/Cloud Storage client is not implemented in demo mode. "
            "Set STORAGE_TYPE='mock' or 'local' in configuration or environment."
        )
