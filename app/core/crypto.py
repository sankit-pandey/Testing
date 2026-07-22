"""Symmetric encryption for `system_settings.setting_value` rows flagged
`is_encrypted` (e.g. per-tenant Lokalise/Figma API tokens). Design ref:
`Database_Schema.md` §14 comment ("Whether value is encrypted (e.g., API
keys)") and `Requirements_Document.md` §6.4.3 (encryption at rest is the
customer's responsibility for infra, but application-level secrets stored
in our own metadata table are still worth encrypting defensively).

Key is derived from `SECRET_KEY` — rotate `SECRET_KEY` only alongside
re-encrypting stored settings (rotation tooling is out of scope here).
"""
import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
