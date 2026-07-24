"""ChromaDB image similarity matching — Design ref: `LOCKED_Design_v1.0.md`
§5 (≥ 90% match); `Technical_Design_Document.md` §2.1.4, §3.2;
`Requirements_Document.md` §4.3.1 (matching scoped **per product**, not
global — prevents cross-product false matches). Story 4.3.

ChromaDB is a **critical dependency**: per `Requirements_Document.md` §4.7.3,
if ChromaDB is unavailable the job fails outright (no silent skip).

`tenant_id` (config-driven via `CHROMADB_TENANT_ID`, default `"default"`) is
stamped on every vector and applied as an additional query filter, on top of
the existing per-product scoping. This is the only tenant concept in the
codebase — a ChromaDB-level namespace, not a relational multi-tenancy model.
"""
import uuid
from typing import Any

import chromadb

from app.core.config import get_settings
from app.services.embeddings import get_image_embedder
from app.utils.circuit_breaker import CircuitBreaker

COLLECTION_NAME = "ui_screenshots"


class ChromaDBUnavailableError(Exception):
    """Raised when ChromaDB cannot be reached — the job must fail (Requirements §4.7.3)."""


class ImageMatch:
    def __init__(self, chromadb_id: str, similarity: float, metadata: dict[str, Any]) -> None:
        self.chromadb_id = chromadb_id
        self.similarity = similarity
        self.metadata = metadata


class ChromaDBService:
    def __init__(self) -> None:
        settings = get_settings()
        self.threshold = settings.chromadb_image_match_threshold
        self.tenant_id = settings.chromadb_tenant_id
        self.breaker = CircuitBreaker("chromadb")
        self._embedder = get_image_embedder()
        try:
            self._client = chromadb.HttpClient(host=settings.chromadb_host, port=settings.chromadb_port)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine", "hnsw:construction_ef": 200, "hnsw:M": 16},
            )
        except Exception as exc:  # noqa: BLE001 — surfaced as the design-mandated hard failure
            raise ChromaDBUnavailableError(f"Cannot connect to ChromaDB: {exc}") from exc

    def add_image(
        self, image_id: uuid.UUID | str, image_bytes: bytes, metadata: dict[str, Any]
    ) -> str:
        """Embed and store an image (Figma-sourced reference screenshots). Story 4.4/5.1."""
        chromadb_id = str(image_id)
        embedding = self._embedder.embed(image_bytes)
        stamped_metadata = {**metadata, "tenant_id": self.tenant_id}

        def _call() -> None:
            self._collection.upsert(ids=[chromadb_id], embeddings=[embedding], metadatas=[stamped_metadata])

        try:
            self.breaker.call(_call)
        except Exception as exc:  # noqa: BLE001
            raise ChromaDBUnavailableError(f"ChromaDB add_image failed: {exc}") from exc
        return chromadb_id

    def find_matches(
        self, image_bytes: bytes, *, product_id: uuid.UUID | str, n_results: int = 5
    ) -> list[ImageMatch]:
        """Similarity search scoped to `product_id` (Requirements §4.3.1);
        returns only matches at/above the locked 90% threshold (LOCKED §5).
        """
        embedding = self._embedder.embed(image_bytes)

        def _call() -> dict[str, Any]:
            return self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where={
                    "$and": [
                        {"product_id": {"$eq": str(product_id)}},
                        {"tenant_id": {"$eq": self.tenant_id}},
                    ]
                },
            )

        try:
            results = self.breaker.call(_call)
        except Exception as exc:  # noqa: BLE001 — ChromaDB is a hard dependency (Requirements §4.7.3)
            raise ChromaDBUnavailableError(f"ChromaDB find_matches failed: {exc}") from exc

        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        matches: list[ImageMatch] = []
        for chromadb_id, distance, metadata in zip(ids, distances, metadatas, strict=False):
            # hnsw:space=cosine -> distance is (1 - cosine_similarity); similarity = 1 - distance.
            similarity = 1.0 - distance
            if similarity >= self.threshold:
                matches.append(ImageMatch(chromadb_id, similarity, metadata or {}))
        return matches
