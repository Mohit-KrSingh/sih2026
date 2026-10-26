"""Mock and local disk implementations of Storage interface.

SPEC.md section 3, 4, 18:
Files sit behind a Storage interface (local volume or in-memory mock).
"""

from pathlib import Path

from app.integrations.interfaces import Storage


class MockStorage(Storage):
    """In-memory mock storage for tests and simulations."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, str]] = {}

    def save(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store content in-memory."""
        normalized_path = path.replace("\\", "/").lstrip("/")
        self._store[normalized_path] = (content, content_type)
        return normalized_path

    def get(self, path: str) -> bytes:
        """Retrieve stored bytes."""
        normalized_path = path.replace("\\", "/").lstrip("/")
        if normalized_path not in self._store:
            raise FileNotFoundError(f"File not found in storage: {path}")
        return self._store[normalized_path][0]

    def exists(self, path: str) -> bool:
        """Check if file exists."""
        normalized_path = path.replace("\\", "/").lstrip("/")
        return normalized_path in self._store

    def delete(self, path: str) -> bool:
        """Remove file from storage."""
        normalized_path = path.replace("\\", "/").lstrip("/")
        if normalized_path in self._store:
            del self._store[normalized_path]
            return True
        return False

    def get_url(self, path: str) -> str:
        """Generate storage reference URL."""
        normalized_path = path.replace("\\", "/").lstrip("/")
        return f"/api/v1/storage/{normalized_path}"


class LocalStorage(Storage):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: str = "./storage/uploads") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        normalized = Path(path.replace("\\", "/").lstrip("/"))
        resolved = (self.base_dir / normalized).resolve()
        if not str(resolved).startswith(str(self.base_dir)):
            raise ValueError(f"Path traversal detected: {path}")
        return resolved

    def save(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Save file to local disk volume."""
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        normalized_path = path.replace("\\", "/").lstrip("/")
        return normalized_path

    def get(self, path: str) -> bytes:
        """Read bytes from local disk."""
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found in storage: {path}")
        return target.read_bytes()

    def exists(self, path: str) -> bool:
        """Check if local file exists."""
        try:
            target = self._resolve(path)
            return target.is_file()
        except ValueError:
            return False

    def delete(self, path: str) -> bool:
        """Delete local file."""
        target = self._resolve(path)
        if target.is_file():
            target.unlink()
            return True
        return False

    def get_url(self, path: str) -> str:
        """Return local file URL."""
        normalized_path = path.replace("\\", "/").lstrip("/")
        return f"/api/v1/storage/{normalized_path}"
