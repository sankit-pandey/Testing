"""ChromaDB-only tenant scoping: every vector is stamped with `tenant_id`
(from `CHROMADB_TENANT_ID`) and every query filters by it, on top of the
existing per-product scoping. Mocks the chromadb client — no live server
needed — since this only tests filter/metadata construction.
"""
import uuid

import pytest

from app.services import chromadb_service as chromadb_service_module
from app.services.chromadb_service import ChromaDBService


class _FakeCollection:
    def __init__(self):
        self.upserted = []
        self.last_query_where = None

    def upsert(self, ids, embeddings, metadatas):
        self.upserted.append({"ids": ids, "embeddings": embeddings, "metadatas": metadatas})

    def query(self, query_embeddings, n_results, where):
        self.last_query_where = where
        return {"ids": [[]], "distances": [[]], "metadatas": [[]]}


class _FakeClient:
    def __init__(self, collection):
        self._collection = collection

    def get_or_create_collection(self, name, metadata):
        return self._collection


@pytest.fixture()
def fake_chroma(monkeypatch):
    collection = _FakeCollection()
    monkeypatch.setattr(chromadb_service_module.chromadb, "HttpClient", lambda **kw: _FakeClient(collection))
    monkeypatch.setattr(
        chromadb_service_module,
        "get_image_embedder",
        lambda: type("E", (), {"embed": lambda self, b: [0.1, 0.2, 0.3]})(),
    )
    return collection


def test_add_image_stamps_configured_tenant_id(fake_chroma):
    service = ChromaDBService()
    service.tenant_id = "acme"  # simulates CHROMADB_TENANT_ID=acme without mutating shared Settings

    service.add_image(uuid.uuid4(), b"fake-bytes", metadata={"product_id": "p1"})

    assert fake_chroma.upserted[0]["metadatas"][0]["tenant_id"] == "acme"
    assert fake_chroma.upserted[0]["metadatas"][0]["product_id"] == "p1"


def test_find_matches_filters_by_product_and_tenant(fake_chroma):
    service = ChromaDBService()
    service.tenant_id = "acme"
    product_id = uuid.uuid4()

    service.find_matches(b"fake-bytes", product_id=product_id)

    where = fake_chroma.last_query_where
    assert where["$and"] == [
        {"product_id": {"$eq": str(product_id)}},
        {"tenant_id": {"$eq": "acme"}},
    ]
