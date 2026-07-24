"""Application configuration loaded from environment variables.

See `Design/LOCKED_Design_v1.0.md` §2, §8 and `.env.example` for the
authoritative list of settings and their defaults.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings (env-driven, never hardcode secrets)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_name: str = "Knewron AI Localization Platform"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_retention_days: int = 30
    secret_key: str = "change-me-in-every-environment"

    # Database
    database_url: str = "postgresql+asyncpg://localization:password@localhost:5432/localization"
    database_url_sync: str = "postgresql+psycopg2://localization:password@localhost:5432/localization"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_worker_concurrency: int = 3
    lokalise_poll_interval_minutes: int = 15

    # ChromaDB
    chromadb_host: str = "localhost"
    chromadb_port: int = 8001
    chromadb_image_match_threshold: float = 0.90
    # Logical partition key stamped on every vector's metadata and applied as
    # an extra `where` filter on every query, on top of the existing
    # per-product scoping (Requirements §4.3.1). This is the only place in
    # the codebase with a "tenant" concept — deliberately not a relational
    # multi-tenancy model (no `tenants` table, no tenant-scoped auth/users);
    # just a ChromaDB-level namespace, e.g. for separating environments or
    # customer deployments that share one ChromaDB instance.
    chromadb_tenant_id: str = "default"

    # AI classifier / embeddings
    ai_image_confidence_threshold: float = 0.70
    # "clip" (local, sentence-transformers) | "phash" (dependency-light
    # fallback) | "aws" (Bedrock Titan multimodal) | "gcp" (Vertex AI
    # multimodal embeddings) — see app/services/embeddings.py.
    ai_embedding_backend: str = "clip"

    # --- AWS Bedrock embeddings (ai_embedding_backend=aws) ---
    embedding_aws_region: str = "us-east-1"
    embedding_aws_model_id: str = "amazon.titan-embed-image-v1"

    # --- GCP Vertex AI embeddings (ai_embedding_backend=gcp) ---
    embedding_gcp_project_id: str | None = None
    embedding_gcp_location: str = "us-central1"
    embedding_gcp_model: str = "multimodalembedding@001"

    # Storage — selectable per environment via STORAGE_BACKEND.
    storage_backend: str = "local"  # "local" | "s3" | "gcs"
    storage_bucket: str = "knewron-localization"
    storage_presign_expiry_seconds: int = 3600
    storage_local_root: str = "./data/storage"

    # --- S3 (storage_backend=s3) ---
    storage_endpoint_url: str | None = None
    storage_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # --- GCS (storage_backend=gcs) ---
    gcs_project_id: str | None = None
    # Path to a service-account JSON key file. If unset, falls back to
    # Application Default Credentials (e.g. GOOGLE_APPLICATION_CREDENTIALS,
    # workload identity, or `gcloud auth application-default login`).
    gcs_credentials_path: str | None = None

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30
    sso_issuer: str | None = None
    sso_authorize_url: str | None = None
    sso_token_url: str | None = None
    sso_jwks_url: str | None = None
    sso_client_id: str | None = None
    sso_client_secret: str | None = None
    sso_redirect_uri: str | None = None

    # Lokalise
    lokalise_api_token: str | None = None
    lokalise_project_id: str | None = None
    lokalise_base_url: str = "https://api.lokalise.com/api2"
    lokalise_webhook_secret: str | None = None

    # Figma
    figma_access_token: str | None = None
    figma_base_url: str = "https://api.figma.com/v1"
    figma_max_concurrent_requests: int = 8
    figma_max_retries: int = 5

    # Circuit breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_seconds: int = 60

    # Audit
    audit_log_retention_days: int = 365

    # Notifications (Technical_Design §2.2.1 — email + in-app; in-app is the
    # existing Redis Pub/Sub -> WebSocket event bus, Story 3.1)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "no-reply@knewron.local"


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""
    return Settings()
