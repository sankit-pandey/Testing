# 🗄️ Database Schema Design

**Project:** AI Localization Platform  
**Date:** July 20, 2026 (unchanged — see note below)  
**Version:** 1.0  
**Status:** ✅ Locked

> **Note (July 24, 2026):** This PostgreSQL schema is implemented **verbatim**
> at `knewron-localization/` — all 14 tables below, unmodified, including
> through the post-implementation extensions described in
> `Technical_Design_Document.md` §11. None of those extensions (multi-cloud
> storage/embedding providers, Poetry, Redis externalization, or the
> ChromaDB-only `tenant_id` partition key in §11.3) add, remove, or rename a
> table, column, index, or constraint here. §11.3's `tenant_id` lives in
> ChromaDB's own vector metadata (see Technical_Design §3.2) — a different
> data store from the one this document governs — not in any table below.

---

## **📋 Overview**

### **Database Technology:**
- **Primary Database:** PostgreSQL 15+
- **Vector Database:** ChromaDB (separate service)
- **Cache:** Redis

### **Design Principles:**
- ✅ Normalized schema (3NF)
- ✅ Clear foreign key relationships
- ✅ Audit trail for all entities
- ✅ JSONB for flexible metadata
- ✅ Indexes for performance
- ✅ Soft deletes where appropriate

---

## **🏗️ Schema Diagram**

```
┌─────────────┐
│   users     │
└──────┬──────┘
       │
       │ created_by
       ▼
┌─────────────┐
│  products   │
└──────┬──────┘
       │
       │ product_id
       ▼
┌─────────────┐       ┌──────────────────┐
│  projects   │◄──────│ project_artifacts│
└──────┬──────┘       └────────┬─────────┘
       │                       │
       │                       │ artifact_id
       ▼                       ▼
┌─────────────┐       ┌──────────────────┐
│localization │       │ artifact_stages  │
│    _jobs    │       └────────┬─────────┘
└──────┬──────┘                │
       │                       │
       │                       ▼
       │               ┌──────────────────┐
       │               │artifact_subtasks │
       │               └──────────────────┘
       │
       ▼
┌─────────────┐       ┌──────────────────┐
│localization │       │  image_processing│
│    _logs    │       └──────────────────┘
└─────────────┘
       │
       ▼
┌─────────────┐       ┌──────────────────┐
│ audit_logs  │       │  figma_images    │
└─────────────┘       └──────────────────┘
```

---

## **📊 Table Definitions**

### **1. users**
Stores user information (integrated with DeepHealth SSO)

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'admin', 'localization_manager', 'viewer'
    sso_id VARCHAR(255) UNIQUE,  -- DeepHealth SSO identifier
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_sso_id ON users(sso_id);
CREATE INDEX idx_users_role ON users(role);

-- Comments
COMMENT ON TABLE users IS 'User accounts integrated with DeepHealth SSO';
COMMENT ON COLUMN users.role IS 'User role: admin, localization_manager, viewer';
COMMENT ON COLUMN users.metadata IS 'Additional user preferences and settings';
```

---

### **2. products**
Stores product information

```sql
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
);

-- Indexes
CREATE INDEX idx_products_code ON products(product_code);
CREATE INDEX idx_products_created_by ON products(created_by);
CREATE INDEX idx_products_active ON products(is_active);

-- Comments
COMMENT ON TABLE products IS 'Products that require localization';
COMMENT ON COLUMN products.product_code IS 'Unique product identifier/SKU';
COMMENT ON COLUMN products.metadata IS 'Product-specific configuration and settings';
```

---

### **3. projects**
Localization projects (one per product per target language)

```sql
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    project_name VARCHAR(255) NOT NULL,
    target_language VARCHAR(10) NOT NULL,  -- ISO 639-1 code (e.g., 'de', 'fr', 'es')
    target_market VARCHAR(10),  -- ISO 3166-1 alpha-2 (e.g., 'DE', 'FR', 'US')
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'in_progress', 'partial_complete', 'complete', 'cancelled'
    progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_projects_product_id ON projects(product_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_target_language ON projects(target_language);
CREATE INDEX idx_projects_created_by ON projects(created_by);

-- Unique constraint: one project per product per language
CREATE UNIQUE INDEX idx_projects_unique ON projects(product_id, target_language) 
WHERE status != 'cancelled';

-- Comments
COMMENT ON TABLE projects IS 'Localization projects - one per product per target language';
COMMENT ON COLUMN projects.status IS 'pending, in_progress, partial_complete, complete, cancelled';
COMMENT ON COLUMN projects.target_language IS 'ISO 639-1 language code';
COMMENT ON COLUMN projects.target_market IS 'ISO 3166-1 alpha-2 country code';
```

---

### **4. project_artifacts**
Artifacts within a project (IFU, Video, UI Resource files)

```sql
CREATE TABLE project_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL,  -- 'IFU', 'VIDEO', 'UI_RESOURCE'
    artifact_name VARCHAR(255) NOT NULL,
    source_path VARCHAR(500),  -- S3/GCS path to source file
    source_filename VARCHAR(255),
    source_file_size BIGINT,  -- bytes
    source_file_hash VARCHAR(64),  -- SHA-256 hash
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'in_progress', 'complete', 'failed', 'cancelled'
    progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    output_path VARCHAR(500),  -- S3/GCS path to localized file
    download_url VARCHAR(1000),  -- Presigned URL for download
    download_url_expires_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_artifacts_project_id ON project_artifacts(project_id);
CREATE INDEX idx_artifacts_type ON project_artifacts(artifact_type);
CREATE INDEX idx_artifacts_status ON project_artifacts(status);
CREATE INDEX idx_artifacts_created_at ON project_artifacts(created_at DESC);

-- Comments
COMMENT ON TABLE project_artifacts IS 'Artifacts to be localized within a project';
COMMENT ON COLUMN project_artifacts.artifact_type IS 'IFU, VIDEO, UI_RESOURCE';
COMMENT ON COLUMN project_artifacts.status IS 'pending, processing, in_progress, complete, failed, cancelled';
COMMENT ON COLUMN project_artifacts.metadata IS 'Artifact-specific data (e.g., page count, duration, etc.)';
```

---

### **5. artifact_stages**
Tracks pipeline stages for each artifact

```sql
CREATE TABLE artifact_stages (
    stage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
    stage_name VARCHAR(50) NOT NULL,  -- 'process', 'orchestrate', 'assemble', 'review', 'signoff', 'download'
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'in_progress', 'complete', 'failed', 'skipped'
    progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_stages_artifact_id ON artifact_stages(artifact_id);
CREATE INDEX idx_stages_status ON artifact_stages(status);
CREATE INDEX idx_stages_name ON artifact_stages(stage_name);

-- Unique constraint: one record per artifact per stage
CREATE UNIQUE INDEX idx_stages_unique ON artifact_stages(artifact_id, stage_name);

-- Comments
COMMENT ON TABLE artifact_stages IS 'Pipeline stages for each artifact';
COMMENT ON COLUMN artifact_stages.stage_name IS 'process, orchestrate, assemble, review, signoff, download';
COMMENT ON COLUMN artifact_stages.metadata IS 'Stage-specific data and results';
```

---

### **6. artifact_subtasks**
Sub-tasks within orchestration stage (parallel processing)

```sql
CREATE TABLE artifact_subtasks (
    subtask_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
    parent_stage_id UUID REFERENCES artifact_stages(stage_id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,  -- 'image_pipeline', 'audio_pipeline', 'subtitle_pipeline', 'document_lokalise', 'assembly'
    task_name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'in_progress', 'complete', 'failed'
    progress_percent INT DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    result JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_subtasks_artifact_id ON artifact_subtasks(artifact_id);
CREATE INDEX idx_subtasks_parent_stage ON artifact_subtasks(parent_stage_id);
CREATE INDEX idx_subtasks_status ON artifact_subtasks(status);
CREATE INDEX idx_subtasks_type ON artifact_subtasks(task_type);

-- Comments
COMMENT ON TABLE artifact_subtasks IS 'Sub-tasks within orchestration (parallel processing)';
COMMENT ON COLUMN artifact_subtasks.task_type IS 'image_pipeline, audio_pipeline, subtitle_pipeline, document_lokalise, assembly';
COMMENT ON COLUMN artifact_subtasks.result IS 'Task execution results';
```

---

### **7. image_processing**
Tracks individual image processing within artifacts

```sql
CREATE TABLE image_processing (
    processing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
    image_id UUID NOT NULL,  -- Internal image identifier
    image_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash
    image_path VARCHAR(500),  -- Original image path
    image_position JSONB,  -- Position in document (page, coordinates)
    classification VARCHAR(50),  -- 'ui_screenshot', 'diagram', 'photo', 'chart', 'other'
    classification_confidence DECIMAL(5,4),  -- 0.0000 to 1.0000
    chromadb_match_id UUID,  -- ChromaDB match identifier
    chromadb_similarity DECIMAL(5,4),  -- Similarity score
    figma_frame_id VARCHAR(255),  -- Figma frame ID if matched
    figma_file_key VARCHAR(255),  -- Figma file key
    lokalise_task_id VARCHAR(255),  -- Lokalise task ID
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'classified', 'matched', 'translating', 'translated', 'cached', 'manual', 'failed'
    translated_image_path VARCHAR(500),  -- Path to translated image
    cache_hit BOOLEAN DEFAULT FALSE,
    requires_manual_translation BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_image_proc_artifact_id ON image_processing(artifact_id);
CREATE INDEX idx_image_proc_hash ON image_processing(image_hash);
CREATE INDEX idx_image_proc_status ON image_processing(status);
CREATE INDEX idx_image_proc_classification ON image_processing(classification);
CREATE INDEX idx_image_proc_chromadb_match ON image_processing(chromadb_match_id);

-- Comments
COMMENT ON TABLE image_processing IS 'Individual image processing tracking';
COMMENT ON COLUMN image_processing.classification IS 'AI classification: ui_screenshot, diagram, photo, chart, other';
COMMENT ON COLUMN image_processing.cache_hit IS 'Whether translation was retrieved from cache';
```

---

### **8. figma_images**
Stores Figma image metadata for reuse

```sql
CREATE TABLE figma_images (
    figma_image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(product_id) ON DELETE CASCADE,
    figma_file_key VARCHAR(255) NOT NULL,
    figma_frame_id VARCHAR(255) NOT NULL,
    frame_name VARCHAR(255),
    image_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash of original image
    chromadb_id UUID,  -- ChromaDB vector ID
    text_elements JSONB,  -- Extracted text elements from Figma
    variable_mapping JSONB,  -- Figma variable mappings
    original_language VARCHAR(10),  -- Source language
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_figma_images_product_id ON figma_images(product_id);
CREATE INDEX idx_figma_images_file_key ON figma_images(figma_file_key);
CREATE INDEX idx_figma_images_frame_id ON figma_images(figma_frame_id);
CREATE INDEX idx_figma_images_hash ON figma_images(image_hash);
CREATE INDEX idx_figma_images_chromadb ON figma_images(chromadb_id);

-- Unique constraint
CREATE UNIQUE INDEX idx_figma_images_unique ON figma_images(figma_file_key, figma_frame_id);

-- Comments
COMMENT ON TABLE figma_images IS 'Figma image metadata for ChromaDB matching and reuse';
COMMENT ON COLUMN figma_images.text_elements IS 'Extracted text nodes from Figma frame';
COMMENT ON COLUMN figma_images.variable_mapping IS 'Figma variable IDs mapped to text elements';
```

---

### **9. translation_cache**
Caches translated images for reuse

```sql
CREATE TABLE translation_cache (
    cache_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_image_hash VARCHAR(64) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    figma_frame_id VARCHAR(255),
    translated_image_path VARCHAR(500) NOT NULL,
    translation_quality_score DECIMAL(5,4),  -- AI quality score
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_cache_source_hash ON translation_cache(source_image_hash);
CREATE INDEX idx_cache_target_lang ON translation_cache(target_language);
CREATE INDEX idx_cache_figma_frame ON translation_cache(figma_frame_id);
CREATE INDEX idx_cache_expires_at ON translation_cache(expires_at);

-- Unique constraint
CREATE UNIQUE INDEX idx_cache_unique ON translation_cache(source_image_hash, target_language);

-- Comments
COMMENT ON TABLE translation_cache IS 'Cache of translated images for reuse across projects';
COMMENT ON COLUMN translation_cache.usage_count IS 'Number of times this cached translation was reused';
```

---

### **10. lokalise_tasks**
Tracks Lokalise translation tasks

```sql
CREATE TABLE lokalise_tasks (
    lokalise_task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
    subtask_id UUID REFERENCES artifact_subtasks(subtask_id) ON DELETE CASCADE,
    lokalise_project_id VARCHAR(255) NOT NULL,
    lokalise_task_external_id VARCHAR(255),  -- Lokalise's task ID
    task_type VARCHAR(50) NOT NULL,  -- 'document', 'subtitles', 'transcript', 'ui_strings', 'image_text'
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'uploaded', 'translating', 'reviewing', 'completed', 'failed'
    uploaded_at TIMESTAMP,
    completed_at TIMESTAMP,
    download_url VARCHAR(1000),
    webhook_received_at TIMESTAMP,
    polling_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_lokalise_artifact_id ON lokalise_tasks(artifact_id);
CREATE INDEX idx_lokalise_subtask_id ON lokalise_tasks(subtask_id);
CREATE INDEX idx_lokalise_status ON lokalise_tasks(status);
CREATE INDEX idx_lokalise_external_id ON lokalise_tasks(lokalise_task_external_id);

-- Comments
COMMENT ON TABLE lokalise_tasks IS 'Tracks Lokalise translation tasks';
COMMENT ON COLUMN lokalise_tasks.task_type IS 'document, subtitles, transcript, ui_strings, image_text';
COMMENT ON COLUMN lokalise_tasks.polling_count IS 'Number of times status was polled';
```

---

### **11. review_findings**
Stores AI and human review findings

```sql
CREATE TABLE review_findings (
    finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL,  -- 'ai_review', 'human_review'
    severity VARCHAR(20) NOT NULL,  -- 'critical', 'major', 'minor', 'info'
    category VARCHAR(50),  -- 'completeness', 'formatting', 'quality', 'consistency', 'accuracy'
    description TEXT NOT NULL,
    location JSONB,  -- Page number, image ID, timestamp, etc.
    status VARCHAR(20) DEFAULT 'open',  -- 'open', 'resolved', 'ignored'
    reviewed_by UUID REFERENCES users(user_id),
    resolved_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_findings_artifact_id ON review_findings(artifact_id);
CREATE INDEX idx_findings_type ON review_findings(finding_type);
CREATE INDEX idx_findings_severity ON review_findings(severity);
CREATE INDEX idx_findings_status ON review_findings(status);
CREATE INDEX idx_findings_reviewed_by ON review_findings(reviewed_by);

-- Comments
COMMENT ON TABLE review_findings IS 'AI and human review findings';
COMMENT ON COLUMN review_findings.finding_type IS 'ai_review, human_review';
COMMENT ON COLUMN review_findings.severity IS 'critical, major, minor, info';
```

---

### **12. approvals**
Tracks sign-off approvals

```sql
CREATE TABLE approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES project_artifacts(artifact_id) ON DELETE CASCADE,
    approved_by UUID NOT NULL REFERENCES users(user_id),
    approval_status VARCHAR(20) NOT NULL,  -- 'approved', 'rejected'
    comments TEXT,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_approvals_artifact_id ON approvals(artifact_id);
CREATE INDEX idx_approvals_approved_by ON approvals(approved_by);
CREATE INDEX idx_approvals_status ON approvals(approval_status);

-- Comments
COMMENT ON TABLE approvals IS 'Artifact sign-off approvals';
```

---

### **13. audit_logs**
Comprehensive audit trail

```sql
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,  -- 'create_project', 'upload_artifact', 'approve', 'reject', etc.
    entity_type VARCHAR(50),  -- 'project', 'artifact', 'user', etc.
    entity_id UUID,
    ip_address INET,
    user_agent TEXT,
    changes JSONB,  -- Before/after values
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_entity_type ON audit_logs(entity_type);
CREATE INDEX idx_audit_entity_id ON audit_logs(entity_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at DESC);

-- Partitioning by month (for performance)
-- CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
-- FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- Comments
COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all user and system actions';
COMMENT ON COLUMN audit_logs.changes IS 'Before/after values for update operations';
```

---

### **14. system_settings**
Application configuration

```sql
CREATE TABLE system_settings (
    setting_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) DEFAULT 'string',  -- 'string', 'number', 'boolean', 'json'
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    updated_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_settings_key ON system_settings(setting_key);

-- Comments
COMMENT ON TABLE system_settings IS 'Application-wide configuration settings';
COMMENT ON COLUMN system_settings.is_encrypted IS 'Whether value is encrypted (e.g., API keys)';
```

---

## **🔗 Relationships Summary**

```
users (1) ──────────── (N) products
users (1) ──────────── (N) projects
users (1) ──────────── (N) audit_logs
users (1) ──────────── (N) review_findings
users (1) ──────────── (N) approvals

products (1) ────────── (N) projects
products (1) ────────── (N) figma_images

projects (1) ───────── (N) project_artifacts

project_artifacts (1) ─ (N) artifact_stages
project_artifacts (1) ─ (N) artifact_subtasks
project_artifacts (1) ─ (N) image_processing
project_artifacts (1) ─ (N) lokalise_tasks
project_artifacts (1) ─ (N) review_findings
project_artifacts (1) ─ (N) approvals

artifact_stages (1) ─── (N) artifact_subtasks

artifact_subtasks (1) ─ (N) lokalise_tasks
```

---

## **📈 Estimated Data Volumes**

| Table | Records/Year | Growth Rate |
|-------|--------------|-------------|
| users | 50 | Low |
| products | 20 | Low |
| projects | 200 | Medium |
| project_artifacts | 600 | Medium |
| artifact_stages | 3,600 | Medium |
| artifact_subtasks | 7,200 | Medium |
| image_processing | 180,000 | High |
| figma_images | 5,000 | Medium |
| translation_cache | 50,000 | High |
| lokalise_tasks | 10,000 | Medium |
| review_findings | 5,000 | Medium |
| approvals | 600 | Low |
| audit_logs | 100,000 | High |

---

## **🔧 Maintenance Scripts**

### **Cleanup Old Audit Logs (1 year retention)**
```sql
-- Run monthly
DELETE FROM audit_logs 
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 year';
```

### **Cleanup Expired Translation Cache**
```sql
-- Run daily
DELETE FROM translation_cache 
WHERE expires_at < CURRENT_TIMESTAMP;
```

### **Cleanup Expired Download URLs**
```sql
-- Run daily
UPDATE project_artifacts 
SET download_url = NULL, download_url_expires_at = NULL
WHERE download_url_expires_at < CURRENT_TIMESTAMP;
```

---

## **📊 Performance Optimization**

### **Indexes Created:**
- ✅ Primary keys (automatic)
- ✅ Foreign keys
- ✅ Status columns (for filtering)
- ✅ Timestamp columns (for sorting)
- ✅ Hash columns (for lookups)
- ✅ Unique constraints

### **Future Optimizations:**
- Partitioning for `audit_logs` (by month)
- Materialized views for reporting
- Connection pooling (handled by SQLAlchemy)

---

## **🔒 Security Considerations**

### **Sensitive Data:**
- ✅ API keys in `system_settings` → Encrypted
- ✅ User passwords → Not stored (SSO only)
- ✅ Audit logs → IP addresses logged
- ✅ Row-level security → Not required (application-level)

### **Backup Strategy:**
- Daily automated backups
- Point-in-time recovery enabled
- 30-day retention

---

## **✅ Migration Strategy**

### **Initial Schema Creation:**
```bash
# Using Alembic (SQLAlchemy migrations)
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### **Version Control:**
- All schema changes via Alembic migrations
- Migrations stored in `app/db/migrations/`
- Never modify schema directly in production

---

**Schema Status:** ✅ **LOCKED & IMPLEMENTED** — all 14 tables live at
`knewron-localization/app/models/`, migration `0001_initial_schema.py`
(`app/db/migrations/versions/`). See the note at the top of this document
regarding the July 24, 2026 post-implementation extensions (none of which
touch this schema).
