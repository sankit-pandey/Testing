"""Story 2.1 acceptance: running the pipeline with `NoOpStrategy` advances
through all six universal stages and completes.
"""
import uuid

from app.models.artifacts import ProjectArtifact
from app.models.products import Product
from app.models.projects import Project
from app.pipeline.constants import STAGE_ORDER
from app.pipeline.executor import Pipeline
from app.pipeline.strategy import NoOpStrategy


def _make_artifact(db_session) -> ProjectArtifact:
    product = Product(product_name="Test Product")
    db_session.add(product)
    db_session.flush()

    project = Project(product_id=product.product_id, project_name="Test Project", target_language="de")
    db_session.add(project)
    db_session.flush()

    artifact = ProjectArtifact(
        project_id=project.project_id,
        artifact_type="NOOP",
        artifact_name="test.docx",
        status="processing",
    )
    db_session.add(artifact)
    db_session.flush()
    return artifact


def test_pipeline_advances_through_all_stages(db_session, monkeypatch):
    monkeypatch.setattr("app.pipeline.executor.publish_event", lambda *a, **k: None)

    artifact = _make_artifact(db_session)
    pipeline = Pipeline(db_session, artifact, NoOpStrategy())

    result = pipeline.execute()

    assert result == {"status": "complete"}
    assert artifact.status == "complete"

    from app.models.stages import ArtifactStage
    from sqlalchemy import select

    stages = db_session.execute(
        select(ArtifactStage).where(ArtifactStage.artifact_id == artifact.artifact_id)
    ).scalars().all()
    completed = {s.stage_name for s in stages if s.status == "complete"}
    assert completed == set(STAGE_ORDER)
