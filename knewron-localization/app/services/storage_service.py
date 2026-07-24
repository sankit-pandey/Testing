"""Object storage abstraction — AWS S3, Google Cloud Storage, or a local
filesystem fallback, selected at runtime via `STORAGE_BACKEND` in `.env`.

Design ref: `LOCKED_Design_v1.0.md` §9 (S3/GCS for source files, extracted/
translated images, final artifacts); `Technical_Design_Document.md` §7
(storage). Story 4.1.

All backends expose the same interface so callers (artifact upload,
document/image processors, assembler) never branch on backend. `presign_put`/
`presign_get` return URLs the client/browser can call directly:
- **S3 backend** (`STORAGE_BACKEND=s3`) — real S3 presigned URLs (`boto3`).
- **GCS backend** (`STORAGE_BACKEND=gcs`) — V4 signed URLs (`google-cloud-storage`;
  install the `gcp` extra — `poetry install -E gcp`).
- **Local backend** (`STORAGE_BACKEND=local`, dev without S3/GCS) — signed URLs
  pointing back at this app's own upload/download endpoints
  (`/api/v1/storage/*`), keeping the API contract (`uploadUrl` in the
  artifact-creation response) identical.
"""
import abc
import mimetypes
import time
import uuid
from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig
from jose import jwt

from app.core.config import get_settings

STORAGE_TOKEN_TYPE = "storage"


class StorageBackend(abc.ABC):
    """Common interface for object storage backends."""

    @abc.abstractmethod
    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None: ...

    @abc.abstractmethod
    def get_bytes(self, key: str) -> bytes: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool: ...

    @abc.abstractmethod
    def presign_put(self, key: str, content_type: str | None, expires_in: int) -> str: ...

    @abc.abstractmethod
    def presign_get(self, key: str, expires_in: int) -> str: ...


class S3StorageBackend(StorageBackend):
    """AWS S3 / GCS (S3-compatible) backend via boto3."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.storage_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url or None,
            region_name=settings.storage_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            config=BotoConfig(signature_version="s3v4"),
        )

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001 — boto3 raises ClientError with 404 code
            return False

    def presign_put(self, key: str, content_type: str | None, expires_in: int) -> str:
        params = {"Bucket": self.bucket, "Key": key}
        if content_type:
            params["ContentType"] = content_type
        return self._client.generate_presigned_url("put_object", Params=params, ExpiresIn=expires_in)

    def presign_get(self, key: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires_in
        )


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend via `google-cloud-storage` (`gcp` extra)."""

    def __init__(self) -> None:
        try:
            from google.cloud import storage as gcs_storage
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "STORAGE_BACKEND=gcs requires the 'gcp' extra: poetry install -E gcp"
            ) from exc

        settings = get_settings()
        self.bucket_name = settings.storage_bucket
        if settings.gcs_credentials_path:
            self._client = gcs_storage.Client.from_service_account_json(
                settings.gcs_credentials_path, project=settings.gcs_project_id
            )
        else:
            # Falls back to Application Default Credentials (workload
            # identity, GOOGLE_APPLICATION_CREDENTIALS, or `gcloud auth
            # application-default login`).
            self._client = gcs_storage.Client(project=settings.gcs_project_id)
        self._bucket = self._client.bucket(self.bucket_name)

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None:
        self._bucket.blob(key).upload_from_string(
            data, content_type=content_type or "application/octet-stream"
        )

    def get_bytes(self, key: str) -> bytes:
        return self._bucket.blob(key).download_as_bytes()

    def delete(self, key: str) -> None:
        blob = self._bucket.blob(key)
        if blob.exists():
            blob.delete()

    def exists(self, key: str) -> bool:
        return self._bucket.blob(key).exists()

    def presign_put(self, key: str, content_type: str | None, expires_in: int) -> str:
        from datetime import timedelta

        return self._bucket.blob(key).generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires_in),
            method="PUT",
            content_type=content_type or "application/octet-stream",
        )

    def presign_get(self, key: str, expires_in: int) -> str:
        from datetime import timedelta

        return self._bucket.blob(key).generate_signed_url(
            version="v4", expiration=timedelta(seconds=expires_in), method="GET"
        )


class LocalStorageBackend(StorageBackend):
    """Filesystem fallback for local development (no S3/MinIO required)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.storage_local_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._secret = settings.secret_key
        self._algorithm = settings.jwt_algorithm

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise ValueError("Invalid storage key (path traversal)")
        return path

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def _sign(self, key: str, action: str, expires_in: int, content_type: str | None = None) -> str:
        payload = {
            "type": STORAGE_TOKEN_TYPE,
            "key": key,
            "action": action,
            "content_type": content_type,
            "exp": int(time.time()) + expires_in,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def presign_put(self, key: str, content_type: str | None, expires_in: int) -> str:
        token = self._sign(key, "put", expires_in, content_type)
        return f"/api/v1/storage/local/{token}"

    def presign_get(self, key: str, expires_in: int) -> str:
        token = self._sign(key, "get", expires_in)
        return f"/api/v1/storage/local/{token}"


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3StorageBackend()
    if settings.storage_backend == "gcs":
        return GCSStorageBackend()
    return LocalStorageBackend()


class StorageService:
    """High-level facade used by services/tasks — key naming + backend delegation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend = get_storage_backend()

    @staticmethod
    def build_key(*parts: str) -> str:
        return "/".join(p.strip("/") for p in parts if p)

    @staticmethod
    def guess_content_type(filename: str) -> str | None:
        return mimetypes.guess_type(filename)[0]

    def new_source_key(self, project_id: uuid.UUID, artifact_id: uuid.UUID, filename: str) -> str:
        return self.build_key("sources", str(project_id), str(artifact_id), filename)

    def new_output_key(self, project_id: uuid.UUID, artifact_id: uuid.UUID, filename: str) -> str:
        return self.build_key("outputs", str(project_id), str(artifact_id), filename)

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None:
        self.backend.put_bytes(key, data, content_type)

    def get_bytes(self, key: str) -> bytes:
        return self.backend.get_bytes(key)

    def delete(self, key: str) -> None:
        self.backend.delete(key)

    def exists(self, key: str) -> bool:
        return self.backend.exists(key)

    def presign_upload(self, key: str, content_type: str | None = None) -> str:
        return self.backend.presign_put(
            key, content_type, self.settings.storage_presign_expiry_seconds
        )

    def presign_download(self, key: str) -> str:
        return self.backend.presign_get(key, self.settings.storage_presign_expiry_seconds)
