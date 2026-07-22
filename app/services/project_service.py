"""Business logic for `projects` — one project per product per single target
language (`LOCKED_Design_v1.0.md` §9). Story 1.1.

`projects` has no direct `tenant_id` column — it is scoped transitively via
`product_id -> products.tenant_id` (a join), since a project always belongs
to exactly one product and a product always belongs to exactly one tenant.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artifacts import ProjectArtifact
from app.models.products import Product
from app.models.projects import Project
from app.schemas.project import ProjectCreate


class DuplicateProjectError(Exception):
    """Raised when an active project already exists for (product_id, target_language)."""


class ProductNotFoundError(Exception):
    """Raised when `product_id` doesn't exist or belongs to a different tenant."""


async def create_project(
    db: AsyncSession, body: ProjectCreate, created_by: uuid.UUID, tenant_id: uuid.UUID
) -> Project:
    product = await db.get(Product, body.product_id)
    if product is None or product.tenant_id != tenant_id:
        raise ProductNotFoundError(f"Product {body.product_id} not found")

    metadata: dict = {}
    if body.source_language:
        metadata["source_language"] = body.source_language

    project = Project(
        product_id=body.product_id,
        project_name=body.project_name,
        target_language=body.target_language,
        target_market=body.target_market,
        created_by=created_by,
        metadata_=metadata,
    )
    db.add(project)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateProjectError(
            f"An active project already exists for product {body.product_id} "
            f"and target language '{body.target_language}'"
        ) from exc
    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID, tenant_id: uuid.UUID) -> Project | None:
    query = (
        select(Project)
        .join(Product, Product.product_id == Project.product_id)
        .where(Project.project_id == project_id, Product.tenant_id == tenant_id)
    )
    return (await db.execute(query)).scalar_one_or_none()


async def get_project_with_artifacts(
    db: AsyncSession, project_id: uuid.UUID, tenant_id: uuid.UUID
) -> Project | None:
    query = (
        select(Project)
        .join(Product, Product.product_id == Project.product_id)
        .where(Project.project_id == project_id, Product.tenant_id == tenant_id)
        .options(selectinload(Project.artifacts))
    )
    return (await db.execute(query)).scalar_one_or_none()


async def list_projects(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    status: str | None,
    product_id: uuid.UUID | None,
    page: int,
    limit: int,
) -> tuple[list[Project], int]:
    query = select(Project).join(Product, Product.product_id == Project.product_id).where(
        Product.tenant_id == tenant_id
    )
    count_query = (
        select(func.count())
        .select_from(Project)
        .join(Product, Product.product_id == Project.product_id)
        .where(Product.tenant_id == tenant_id)
    )
    if status is not None:
        query = query.where(Project.status == status)
        count_query = count_query.where(Project.status == status)
    if product_id is not None:
        query = query.where(Project.product_id == product_id)
        count_query = count_query.where(Project.product_id == product_id)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(Project.created_at.desc()).offset((page - 1) * limit).limit(limit)
    projects = (await db.execute(query)).scalars().all()
    return list(projects), total


async def recompute_project_status(db: AsyncSession, project_id: uuid.UUID) -> Project:
    """Derive project status from its artifacts (Architecture_Diagrams §5):
    `pending -> in_progress -> partial_complete -> complete` (or `cancelled`).
    """
    project = await db.get(Project, project_id)
    artifacts = (
        await db.execute(
            select(ProjectArtifact).where(ProjectArtifact.project_id == project_id)
        )
    ).scalars().all()

    if not artifacts:
        return project

    statuses = {a.status for a in artifacts}
    if statuses == {"cancelled"}:
        project.status = "cancelled"
    elif statuses <= {"complete", "cancelled"}:
        project.status = "complete"
    elif "complete" in statuses and statuses - {"complete"}:
        project.status = "partial_complete"
    elif statuses == {"pending"}:
        project.status = "pending"
    else:
        project.status = "in_progress"

    total_progress = sum(a.progress_percent for a in artifacts)
    project.progress_percent = round(total_progress / len(artifacts))
    if project.status == "complete" and project.completed_at is None:
        from datetime import datetime, timezone

        project.completed_at = datetime.now(timezone.utc)

    await db.flush()
    return project
