"""Multi-tenancy extension: per-tenant integration credential overrides
(`system_settings.tenant_id`) with platform-wide fallback, and at-rest
encryption for values flagged `is_encrypted`.
"""
import uuid

from app.core.crypto import decrypt_value, encrypt_value
from app.models.system_settings import SystemSetting
from app.services.tenant_service import get_tenant_setting_sync


def test_encrypt_round_trip():
    ciphertext = encrypt_value("super-secret-token")
    assert ciphertext != "super-secret-token"
    assert decrypt_value(ciphertext) == "super-secret-token"


def test_tenant_setting_override_falls_back_to_none_when_unset(db_session, tenant_id, monkeypatch):
    monkeypatch.setattr("app.services.tenant_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    assert get_tenant_setting_sync(tenant_id, "lokalise_api_token") is None
    assert get_tenant_setting_sync(None, "lokalise_api_token") is None


def test_tenant_setting_override_resolves_plaintext(db_session, tenant_id, monkeypatch):
    monkeypatch.setattr("app.services.tenant_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    db_session.add(
        SystemSetting(
            tenant_id=tenant_id, setting_key="lokalise_project_id", setting_value="proj-123", is_encrypted=False
        )
    )
    db_session.commit()

    assert get_tenant_setting_sync(tenant_id, "lokalise_project_id") == "proj-123"


def test_tenant_setting_override_resolves_encrypted(db_session, tenant_id, monkeypatch):
    monkeypatch.setattr("app.services.tenant_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    db_session.add(
        SystemSetting(
            tenant_id=tenant_id,
            setting_key="lokalise_api_token",
            setting_value=encrypt_value("tenant-a-token"),
            is_encrypted=True,
        )
    )
    db_session.commit()

    assert get_tenant_setting_sync(tenant_id, "lokalise_api_token") == "tenant-a-token"


def test_two_tenants_have_independent_overrides(db_session, tenant_id, monkeypatch):
    monkeypatch.setattr("app.services.tenant_service.SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    from app.models.tenants import Tenant

    other_tenant = Tenant(name="Other", slug=f"other-{uuid.uuid4().hex[:8]}")
    db_session.add(other_tenant)
    db_session.flush()

    db_session.add(
        SystemSetting(tenant_id=tenant_id, setting_key="figma_access_token", setting_value="token-a")
    )
    db_session.add(
        SystemSetting(
            tenant_id=other_tenant.tenant_id, setting_key="figma_access_token", setting_value="token-b"
        )
    )
    db_session.commit()

    assert get_tenant_setting_sync(tenant_id, "figma_access_token") == "token-a"
    assert get_tenant_setting_sync(other_tenant.tenant_id, "figma_access_token") == "token-b"
