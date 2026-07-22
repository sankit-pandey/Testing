"""Story 2.5 acceptance: two branches completing in any order (including
duplicates) trigger the next stage exactly once; barrier state is DB-backed.
"""
import fakeredis
import pytest

from app.models.artifacts import ProjectArtifact
from app.models.products import Product
from app.models.projects import Project
from app.models.stages import ArtifactStage
from app.pipeline import join_barrier
from app.pipeline import persistence as pers


@pytest.fixture()
def fake_redis(monkeypatch):
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.utils.idempotency.redis.Redis.from_url", lambda *a, **k: client)
    return client


@pytest.fixture()
def artifact_with_subtasks(db_session, tenant_id, monkeypatch):
    monkeypatch.setattr("app.pipeline.join_barrier.SessionLocal", lambda: db_session)
    # prevent db_session.close() inside the barrier's `with SessionLocal() as db`
    monkeypatch.setattr(db_session, "close", lambda: None)

    product = Product(tenant_id=tenant_id, product_name="P")
    db_session.add(product)
    db_session.flush()
    project = Project(product_id=product.product_id, project_name="Proj", target_language="de")
    db_session.add(project)
    db_session.flush()
    artifact = ProjectArtifact(project_id=project.project_id, artifact_type="IFU", artifact_name="a.docx")
    db_session.add(artifact)
    db_session.flush()
    stage = ArtifactStage(artifact_id=artifact.artifact_id, stage_name="orchestrate")
    db_session.add(stage)
    db_session.flush()
    pers.create_subtasks(db_session, artifact.artifact_id, stage.stage_id, ["document_lokalise", "image_pipeline"])
    db_session.commit()
    return artifact


def test_barrier_trips_once_both_branches_complete(artifact_with_subtasks, fake_redis, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.pipeline_tasks.resume_pipeline.delay", lambda *a, **k: calls.append(a)
    )

    first = join_barrier.complete_subtask_and_maybe_resume(artifact_with_subtasks.artifact_id, "document_lokalise")
    assert first is False  # only one of two branches done

    second = join_barrier.complete_subtask_and_maybe_resume(artifact_with_subtasks.artifact_id, "image_pipeline")
    assert second is True  # last branch trips the barrier
    assert len(calls) == 1


def test_duplicate_completion_is_ignored(artifact_with_subtasks, fake_redis, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.pipeline_tasks.resume_pipeline.delay", lambda *a, **k: calls.append(a)
    )

    join_barrier.complete_subtask_and_maybe_resume(artifact_with_subtasks.artifact_id, "document_lokalise")
    duplicate = join_barrier.complete_subtask_and_maybe_resume(artifact_with_subtasks.artifact_id, "document_lokalise")

    assert duplicate is False
    assert len(calls) == 0  # barrier never tripped (image_pipeline still pending)


def test_barrier_trips_exactly_once_on_simultaneous_completion(artifact_with_subtasks, fake_redis, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.pipeline_tasks.resume_pipeline.delay", lambda *a, **k: calls.append(a)
    )

    results = [
        join_barrier.complete_subtask_and_maybe_resume(artifact_with_subtasks.artifact_id, "document_lokalise"),
        join_barrier.complete_subtask_and_maybe_resume(artifact_with_subtasks.artifact_id, "image_pipeline"),
        join_barrier.complete_subtask_and_maybe_resume(artifact_with_subtasks.artifact_id, "image_pipeline"),
    ]

    assert results.count(True) == 1
    assert len(calls) == 1
