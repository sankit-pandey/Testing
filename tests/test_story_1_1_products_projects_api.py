"""Stories 1.1/1.3 acceptance: create/list/get product & project; a project
enforces a single `target_language`; unauthorized requests are blocked;
`viewer` cannot mutate. Users are persisted (not just constructed in
Python) since `created_by` is a real foreign key to `users.user_id`.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.core.roles import Role
from app.db.session import get_db
from app.main import app
from app.models.users import User


@pytest.fixture()
def override_db(async_db_session):
    async def _get_db():
        yield async_db_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


async def _persisted_user(async_db_session, role: str) -> User:
    user = User(
        email=f"{role}-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Test User",
        role=role,
    )
    async_db_session.add(user)
    await async_db_session.commit()
    return user


@pytest_asyncio.fixture()
async def as_manager(override_db, async_db_session):
    user = await _persisted_user(async_db_session, Role.LOCALIZATION_MANAGER.value)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture()
async def as_viewer(override_db, async_db_session):
    user = await _persisted_user(async_db_session, Role.VIEWER.value)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_unauthorized_request_is_blocked(override_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/products")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_manager_can_create_product_and_project(as_manager):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        product_resp = await client.post("/api/v1/products", json={"productName": "Diagnostic Suite"})
        assert product_resp.status_code == 201
        product_id = product_resp.json()["productId"]

        project_resp = await client.post(
            "/api/v1/projects",
            json={"productId": product_id, "projectName": "German IFU", "targetLanguage": "de"},
        )
        assert project_resp.status_code == 201
        assert project_resp.json()["status"] == "pending"

        list_resp = await client.get("/api/v1/products")
        assert list_resp.status_code == 200
        assert list_resp.json()["pagination"]["total"] == 1


@pytest.mark.asyncio
async def test_duplicate_project_for_same_product_and_language_rejected(as_manager):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        product_resp = await client.post("/api/v1/products", json={"productName": "Diagnostic Suite"})
        product_id = product_resp.json()["productId"]

        body = {"productId": product_id, "projectName": "German IFU", "targetLanguage": "de"}
        first = await client.post("/api/v1/projects", json=body)
        second = await client.post("/api/v1/projects", json=body)

        assert first.status_code == 201
        assert second.status_code == 409


@pytest.mark.asyncio
async def test_viewer_cannot_create_product(as_viewer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/products", json={"productName": "Blocked"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_list_products(as_viewer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/products")
    assert response.status_code == 200
