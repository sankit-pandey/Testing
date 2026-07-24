"""Initial schema — all 14 tables from Design/Database_Schema.md.

DDL below is copied verbatim (table/column/index/comment definitions) from the
locked `Database_Schema.md` document to guarantee exact conformance with the
canonical design. Table creation order follows FK dependency order.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.execute(
        """
        CREATE TABLE users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            sso_id VARCHAR(255) UNIQUE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_users_email ON users(email)")
    op.execute("CREATE INDEX idx_users_sso_id ON users(sso_id)")
    op.execute("CREATE INDEX idx_users_role ON users(role)")
    op.execute("COMMENT ON TABLE users IS 'User accounts integrated with DeepHealth SSO'")
    op.execute("COMMENT ON COLUMN users.role IS 'User role: admin, localization_manager, viewer'")
    op.execute("COMMENT ON COLUMN users.metadata IS 'Additional user preferences and settings'")

    # 2. products
    op.execute(
        """
        CREATE TABLE products (
            product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_name VARCHAR(255) NOT NULL,
            product_code VARCHAR(100) UNIQUE,
            description TEXT,
            created_by UUID REFERENCES users(user_id),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_products_code ON products(product_code)")
    op.execute("CREATE INDEX idx_products_created_by ON products(created_by)")
    op.execute("CREATE INDEX idx_products_active ON products(is_active)")
    op.execute("COMMENT ON TABLE products IS 'Products that require localization'")
    op.execute("COMMENT ON COLUMN products.product_code IS 'Unique product identifier/SKU'")
    op.execute(
        "COMMENT ON COLUMN products.metadata IS 'Product-specific configuration and settings'"
    )

    # 3. projects
    op.execute(
        """
        CREATE TABLE projects (
            project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
            project_name VARCHAR(255) NOT NULL,
            target_language VARCHAR(10) NOT NULL,
            target_market VARCHAR(10),
            status VARCHAR(50) DEFAULT 'pending',
            progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
            created_by UUID REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_projects_product_id ON projects(product_id)")
    op.execute("CREATE INDEX idx_projects_status ON projects(status)")
    op.execute("CREATE INDEX idx_projects_target_language ON projects(target_language)")
    op.execute("CREATE INDEX idx_projects_created_by ON projects(created_by)")
    op.execute(
        "CREATE UNIQUE INDEX idx_projects_unique ON projects(product_id, target_language) "
        "WHERE status != 'cancelled'"
    )
    op.execute(
        "COMMENT ON TABLE projects IS 'Localization projects - one per product per target language'"
    )
    op.execute(
        "COMMENT ON COLUMN projects.status IS 'pending, in_progress, partial_complete, complete, cancelled'"
    )
    op.execute("COMMENT ON COLUMN projects.target_language IS 'ISO 639-1 language code'")
    op.execute("COMMENT ON COLUMN projects.target_market IS 'ISO 3166-1 alpha-2 country code'")

    # 4. project_artifacts
    op.execute(
        """
        CREATE TABLE project_artifacts (
            artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            artifact_type VARCHAR(50) NOT NULL,
            artifact_name VARCHAR(255) NOT NULL,
            source_path VARCHAR(500),
            source_filename VARCHAR(255),
            source_file_size BIGINT,
            source_file_hash VARCHAR(64),
            status VARCHAR(50) DEFAULT 'pending',
            progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
            output_path VARCHAR(500),
            download_url VARCHAR(1000),
            download_url_expires_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_artifacts_project_id ON project_artifacts(project_id)")
    op.execute("CREATE INDEX idx_artifacts_type ON project_artifacts(artifact_type)")
    op.execute("CREATE INDEX idx_artifacts_status ON project_artifacts(status)")
    op.execute("CREATE INDEX idx_artifacts_created_at ON project_artifacts(created_at DESC)")
    op.execute(
        "COMMENT ON TABLE project_artifacts IS 'Artifacts to be localized within a project'"
    )
    op.execute("COMMENT ON COLUMN project_artifacts.artifact_type IS 'IFU, VIDEO, UI_RESOURCE'")
    op.execute(
        "COMMENT ON COLUMN project_artifacts.status IS "
        "'pending, processing, in_progress, complete, failed, cancelled'"
    )
    op.execute(
        "COMMENT ON COLUMN project_artifacts.metadata IS "
        "'Artifact-specific data (e.g., page count, duration, etc.)'"
    )

    # 5. artifact_stages
    op.execute(
        """
        CREATE TABLE artifact_stages (
            stage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
            stage_name VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            retry_count INT DEFAULT 0,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX idx_stages_artifact_id ON artifact_stages(artifact_id)")
    op.execute("CREATE INDEX idx_stages_status ON artifact_stages(status)")
    op.execute("CREATE INDEX idx_stages_name ON artifact_stages(stage_name)")
    op.execute(
        "CREATE UNIQUE INDEX idx_stages_unique ON artifact_stages(artifact_id, stage_name)"
    )
    op.execute("COMMENT ON TABLE artifact_stages IS 'Pipeline stages for each artifact'")
    op.execute(
        "COMMENT ON COLUMN artifact_stages.stage_name IS "
        "'process, orchestrate, assemble, review, signoff, download'"
    )
    op.execute(
        "COMMENT ON COLUMN artifact_stages.metadata IS 'Stage-specific data and results'"
    )

    # 6. artifact_subtasks
    op.execute(
        """
        CREATE TABLE artifact_subtasks (
            subtask_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
            parent_stage_id UUID REFERENCES artifact_stages(stage_id) ON DELETE CASCADE,
            task_type VARCHAR(50) NOT NULL,
            task_name VARCHAR(255),
            status VARCHAR(20) DEFAULT 'pending',
            progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            retry_count INT DEFAULT 0,
            result JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX idx_subtasks_artifact_id ON artifact_subtasks(artifact_id)")
    op.execute("CREATE INDEX idx_subtasks_parent_stage ON artifact_subtasks(parent_stage_id)")
    op.execute("CREATE INDEX idx_subtasks_status ON artifact_subtasks(status)")
    op.execute("CREATE INDEX idx_subtasks_type ON artifact_subtasks(task_type)")
    op.execute(
        "COMMENT ON TABLE artifact_subtasks IS "
        "'Sub-tasks within orchestration (parallel processing)'"
    )
    op.execute(
        "COMMENT ON COLUMN artifact_subtasks.task_type IS "
        "'image_pipeline, audio_pipeline, subtitle_pipeline, document_lokalise, assembly'"
    )
    op.execute("COMMENT ON COLUMN artifact_subtasks.result IS 'Task execution results'")

    # 7. image_processing
    op.execute(
        """
        CREATE TABLE image_processing (
            processing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
            image_id UUID NOT NULL,
            image_hash VARCHAR(64) NOT NULL,
            image_path VARCHAR(500),
            image_position JSONB,
            classification VARCHAR(50),
            classification_confidence DECIMAL(5,4),
            chromadb_match_id UUID,
            chromadb_similarity DECIMAL(5,4),
            figma_frame_id VARCHAR(255),
            figma_file_key VARCHAR(255),
            lokalise_task_id VARCHAR(255),
            status VARCHAR(50) DEFAULT 'pending',
            translated_image_path VARCHAR(500),
            cache_hit BOOLEAN DEFAULT FALSE,
            requires_manual_translation BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_image_proc_artifact_id ON image_processing(artifact_id)")
    op.execute("CREATE INDEX idx_image_proc_hash ON image_processing(image_hash)")
    op.execute("CREATE INDEX idx_image_proc_status ON image_processing(status)")
    op.execute("CREATE INDEX idx_image_proc_classification ON image_processing(classification)")
    op.execute(
        "CREATE INDEX idx_image_proc_chromadb_match ON image_processing(chromadb_match_id)"
    )
    op.execute("COMMENT ON TABLE image_processing IS 'Individual image processing tracking'")
    op.execute(
        "COMMENT ON COLUMN image_processing.classification IS "
        "'AI classification: ui_screenshot, diagram, photo, chart, other'"
    )
    op.execute(
        "COMMENT ON COLUMN image_processing.cache_hit IS "
        "'Whether translation was retrieved from cache'"
    )

    # 8. figma_images
    op.execute(
        """
        CREATE TABLE figma_images (
            figma_image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID REFERENCES products(product_id) ON DELETE CASCADE,
            figma_file_key VARCHAR(255) NOT NULL,
            figma_frame_id VARCHAR(255) NOT NULL,
            frame_name VARCHAR(255),
            image_hash VARCHAR(64) NOT NULL,
            chromadb_id UUID,
            text_elements JSONB,
            variable_mapping JSONB,
            original_language VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_figma_images_product_id ON figma_images(product_id)")
    op.execute("CREATE INDEX idx_figma_images_file_key ON figma_images(figma_file_key)")
    op.execute("CREATE INDEX idx_figma_images_frame_id ON figma_images(figma_frame_id)")
    op.execute("CREATE INDEX idx_figma_images_hash ON figma_images(image_hash)")
    op.execute("CREATE INDEX idx_figma_images_chromadb ON figma_images(chromadb_id)")
    op.execute(
        "CREATE UNIQUE INDEX idx_figma_images_unique ON figma_images(figma_file_key, figma_frame_id)"
    )
    op.execute(
        "COMMENT ON TABLE figma_images IS 'Figma image metadata for ChromaDB matching and reuse'"
    )
    op.execute(
        "COMMENT ON COLUMN figma_images.text_elements IS 'Extracted text nodes from Figma frame'"
    )
    op.execute(
        "COMMENT ON COLUMN figma_images.variable_mapping IS "
        "'Figma variable IDs mapped to text elements'"
    )

    # 9. translation_cache
    op.execute(
        """
        CREATE TABLE translation_cache (
            cache_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_image_hash VARCHAR(64) NOT NULL,
            target_language VARCHAR(10) NOT NULL,
            figma_frame_id VARCHAR(255),
            translated_image_path VARCHAR(500) NOT NULL,
            translation_quality_score DECIMAL(5,4),
            usage_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_cache_source_hash ON translation_cache(source_image_hash)")
    op.execute("CREATE INDEX idx_cache_target_lang ON translation_cache(target_language)")
    op.execute("CREATE INDEX idx_cache_figma_frame ON translation_cache(figma_frame_id)")
    op.execute("CREATE INDEX idx_cache_expires_at ON translation_cache(expires_at)")
    op.execute(
        "CREATE UNIQUE INDEX idx_cache_unique ON translation_cache(source_image_hash, target_language)"
    )
    op.execute(
        "COMMENT ON TABLE translation_cache IS "
        "'Cache of translated images for reuse across projects'"
    )
    op.execute(
        "COMMENT ON COLUMN translation_cache.usage_count IS "
        "'Number of times this cached translation was reused'"
    )

    # 10. lokalise_tasks
    op.execute(
        """
        CREATE TABLE lokalise_tasks (
            lokalise_task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
            subtask_id UUID REFERENCES artifact_subtasks(subtask_id) ON DELETE CASCADE,
            lokalise_project_id VARCHAR(255) NOT NULL,
            lokalise_task_external_id VARCHAR(255),
            task_type VARCHAR(50) NOT NULL,
            source_language VARCHAR(10) NOT NULL,
            target_language VARCHAR(10) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            uploaded_at TIMESTAMP,
            completed_at TIMESTAMP,
            download_url VARCHAR(1000),
            webhook_received_at TIMESTAMP,
            polling_count INT DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_lokalise_artifact_id ON lokalise_tasks(artifact_id)")
    op.execute("CREATE INDEX idx_lokalise_subtask_id ON lokalise_tasks(subtask_id)")
    op.execute("CREATE INDEX idx_lokalise_status ON lokalise_tasks(status)")
    op.execute(
        "CREATE INDEX idx_lokalise_external_id ON lokalise_tasks(lokalise_task_external_id)"
    )
    op.execute("COMMENT ON TABLE lokalise_tasks IS 'Tracks Lokalise translation tasks'")
    op.execute(
        "COMMENT ON COLUMN lokalise_tasks.task_type IS "
        "'document, subtitles, transcript, ui_strings, image_text'"
    )
    op.execute(
        "COMMENT ON COLUMN lokalise_tasks.polling_count IS 'Number of times status was polled'"
    )

    # 11. review_findings
    op.execute(
        """
        CREATE TABLE review_findings (
            finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
            finding_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            category VARCHAR(50),
            description TEXT NOT NULL,
            location JSONB,
            status VARCHAR(20) DEFAULT 'open',
            reviewed_by UUID REFERENCES users(user_id),
            resolved_by UUID REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_findings_artifact_id ON review_findings(artifact_id)")
    op.execute("CREATE INDEX idx_findings_type ON review_findings(finding_type)")
    op.execute("CREATE INDEX idx_findings_severity ON review_findings(severity)")
    op.execute("CREATE INDEX idx_findings_status ON review_findings(status)")
    op.execute("CREATE INDEX idx_findings_reviewed_by ON review_findings(reviewed_by)")
    op.execute("COMMENT ON TABLE review_findings IS 'AI and human review findings'")
    op.execute("COMMENT ON COLUMN review_findings.finding_type IS 'ai_review, human_review'")
    op.execute("COMMENT ON COLUMN review_findings.severity IS 'critical, major, minor, info'")

    # 12. approvals
    op.execute(
        """
        CREATE TABLE approvals (
            approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
            approved_by UUID NOT NULL REFERENCES users(user_id),
            approval_status VARCHAR(20) NOT NULL,
            comments TEXT,
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_approvals_artifact_id ON approvals(artifact_id)")
    op.execute("CREATE INDEX idx_approvals_approved_by ON approvals(approved_by)")
    op.execute("CREATE INDEX idx_approvals_status ON approvals(approval_status)")
    op.execute("COMMENT ON TABLE approvals IS 'Artifact sign-off approvals'")

    # 13. audit_logs
    op.execute(
        """
        CREATE TABLE audit_logs (
            log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(user_id),
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50),
            entity_id UUID,
            ip_address INET,
            user_agent TEXT,
            changes JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_audit_user_id ON audit_logs(user_id)")
    op.execute("CREATE INDEX idx_audit_action ON audit_logs(action)")
    op.execute("CREATE INDEX idx_audit_entity_type ON audit_logs(entity_type)")
    op.execute("CREATE INDEX idx_audit_entity_id ON audit_logs(entity_id)")
    op.execute("CREATE INDEX idx_audit_created_at ON audit_logs(created_at DESC)")
    op.execute(
        "COMMENT ON TABLE audit_logs IS "
        "'Comprehensive audit trail for all user and system actions'"
    )
    op.execute(
        "COMMENT ON COLUMN audit_logs.changes IS 'Before/after values for update operations'"
    )

    # 14. system_settings
    op.execute(
        """
        CREATE TABLE system_settings (
            setting_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            setting_type VARCHAR(20) DEFAULT 'string',
            description TEXT,
            is_encrypted BOOLEAN DEFAULT FALSE,
            updated_by UUID REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX idx_settings_key ON system_settings(setting_key)")
    op.execute(
        "COMMENT ON TABLE system_settings IS 'Application-wide configuration settings'"
    )
    op.execute(
        "COMMENT ON COLUMN system_settings.is_encrypted IS "
        "'Whether value is encrypted (e.g., API keys)'"
    )


def downgrade() -> None:
    for table in (
        "system_settings",
        "audit_logs",
        "approvals",
        "review_findings",
        "lokalise_tasks",
        "translation_cache",
        "figma_images",
        "image_processing",
        "artifact_subtasks",
        "artifact_stages",
        "project_artifacts",
        "projects",
        "products",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
