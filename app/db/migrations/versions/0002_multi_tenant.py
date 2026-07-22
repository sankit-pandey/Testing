"""Multi-tenancy extension — adds `tenants` + `tenant_id` isolation columns.

User-directed extension beyond the original locked `Database_Schema.md`
(single-customer-deployment) schema. Assumes a fresh install with no
pre-existing rows (this platform has not shipped yet), so NOT NULL columns
are added directly without a backfill step.

Revision ID: 0002_multi_tenant
Revises: 0001_initial_schema
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_multi_tenant"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tenants
    op.execute(
        """
        CREATE TABLE tenants (
            tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_tenants_slug ON tenants(slug)")
    op.execute("CREATE INDEX idx_tenants_active ON tenants(is_active)")
    op.execute(
        "COMMENT ON TABLE tenants IS 'Customer organizations (multi-tenant isolation boundary)'"
    )

    # 2. users — tenant_id, is_superuser; email uniqueness becomes per-tenant
    op.execute("ALTER TABLE users ADD COLUMN tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE")
    op.execute(
        "ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE"
    )
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key")
    op.execute("CREATE INDEX idx_users_tenant_id ON users(tenant_id)")
    op.execute("CREATE UNIQUE INDEX idx_users_email_tenant_unique ON users(tenant_id, email)")
    op.execute(
        "COMMENT ON COLUMN users.tenant_id IS 'NULL only for platform superusers with no home tenant'"
    )
    op.execute(
        "COMMENT ON COLUMN users.is_superuser IS "
        "'Platform-level superuser (manages tenants); orthogonal to role'"
    )

    # 3. products — tenant_id NOT NULL; product_code uniqueness becomes per-tenant
    op.execute("ALTER TABLE products ADD COLUMN tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE")
    op.execute("ALTER TABLE products ALTER COLUMN tenant_id SET NOT NULL")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_product_code_key")
    op.execute("CREATE INDEX idx_products_tenant_id ON products(tenant_id)")
    op.execute(
        "CREATE UNIQUE INDEX idx_products_code_tenant_unique ON products(tenant_id, product_code)"
    )

    # 4. figma_images — tenant_id NOT NULL; (file_key, frame_id) uniqueness becomes per-tenant
    op.execute(
        "ALTER TABLE figma_images ADD COLUMN tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE figma_images ALTER COLUMN tenant_id SET NOT NULL")
    op.execute("DROP INDEX IF EXISTS idx_figma_images_unique")
    op.execute("CREATE INDEX idx_figma_images_tenant_id ON figma_images(tenant_id)")
    op.execute(
        "CREATE UNIQUE INDEX idx_figma_images_unique "
        "ON figma_images(tenant_id, figma_file_key, figma_frame_id)"
    )

    # 5. translation_cache — tenant_id NOT NULL; cache key becomes per-tenant
    op.execute(
        "ALTER TABLE translation_cache ADD COLUMN tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE translation_cache ALTER COLUMN tenant_id SET NOT NULL")
    op.execute("DROP INDEX IF EXISTS idx_cache_unique")
    op.execute("CREATE INDEX idx_cache_tenant_id ON translation_cache(tenant_id)")
    op.execute(
        "CREATE UNIQUE INDEX idx_cache_unique "
        "ON translation_cache(tenant_id, source_image_hash, target_language)"
    )

    # 6. audit_logs — tenant_id nullable (platform-level actions have no tenant)
    op.execute(
        "ALTER TABLE audit_logs ADD COLUMN tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE"
    )
    op.execute("CREATE INDEX idx_audit_tenant_id ON audit_logs(tenant_id)")

    # 7. system_settings — tenant_id nullable (NULL = platform-wide default)
    op.execute(
        "ALTER TABLE system_settings ADD COLUMN tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE system_settings DROP CONSTRAINT IF EXISTS system_settings_setting_key_key")
    op.execute("CREATE INDEX idx_settings_tenant_id ON system_settings(tenant_id)")
    op.execute(
        "CREATE UNIQUE INDEX idx_settings_key_global_unique "
        "ON system_settings(setting_key) WHERE tenant_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_settings_key_tenant_unique "
        "ON system_settings(tenant_id, setting_key) WHERE tenant_id IS NOT NULL"
    )
    op.execute(
        "COMMENT ON COLUMN system_settings.tenant_id IS "
        "'NULL = platform-wide default; set = per-tenant override'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_settings_key_tenant_unique")
    op.execute("DROP INDEX IF EXISTS idx_settings_key_global_unique")
    op.execute("DROP INDEX IF EXISTS idx_settings_tenant_id")
    op.execute("ALTER TABLE system_settings DROP COLUMN IF EXISTS tenant_id")
    op.execute(
        "ALTER TABLE system_settings ADD CONSTRAINT system_settings_setting_key_key UNIQUE (setting_key)"
    )

    op.execute("DROP INDEX IF EXISTS idx_audit_tenant_id")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS tenant_id")

    op.execute("DROP INDEX IF EXISTS idx_cache_unique")
    op.execute("DROP INDEX IF EXISTS idx_cache_tenant_id")
    op.execute("ALTER TABLE translation_cache DROP COLUMN IF EXISTS tenant_id")
    op.execute(
        "CREATE UNIQUE INDEX idx_cache_unique ON translation_cache(source_image_hash, target_language)"
    )

    op.execute("DROP INDEX IF EXISTS idx_figma_images_unique")
    op.execute("DROP INDEX IF EXISTS idx_figma_images_tenant_id")
    op.execute("ALTER TABLE figma_images DROP COLUMN IF EXISTS tenant_id")
    op.execute(
        "CREATE UNIQUE INDEX idx_figma_images_unique ON figma_images(figma_file_key, figma_frame_id)"
    )

    op.execute("DROP INDEX IF EXISTS idx_products_code_tenant_unique")
    op.execute("DROP INDEX IF EXISTS idx_products_tenant_id")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS tenant_id")
    op.execute("ALTER TABLE products ADD CONSTRAINT products_product_code_key UNIQUE (product_code)")

    op.execute("DROP INDEX IF EXISTS idx_users_email_tenant_unique")
    op.execute("DROP INDEX IF EXISTS idx_users_tenant_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_superuser")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS tenant_id")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email)")

    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
