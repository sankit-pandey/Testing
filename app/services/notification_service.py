"""Notifications — Design ref: `Technical_Design_Document.md` §2.2.1 (email +
in-app + webhook callbacks); `Requirements_Document.md` §5.6.4 ("Who:
Localization Manager; Channel: in-app; Events: all major stage transitions").
Story 7.2.

In-app notifications are the existing Redis Pub/Sub -> WebSocket event bus
(Story 3.1) — `Database_Schema.md`'s 14 tables have no `notifications` table,
and Redis is explicitly the platform's ephemeral real-time channel
(`Architecture_Diagrams.md` §3.1), so persisted "notification inbox" storage
is out of scope for this schema. This module adds the **email** channel for
events a Localization Manager should see even while not actively watching
the UI: artifact failed, human review needed, download ready.
"""
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.artifacts import ProjectArtifact
from app.models.users import User

logger = get_logger(__name__)


def _send_email(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.info("notification_email_skipped_no_smtp", to=to_email, subject=subject)
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_use_tls:
                client.starttls()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password or "")
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.error("notification_email_failed", to=to_email, error=str(exc))


def _project_creator_email(db: Session, artifact: ProjectArtifact) -> str | None:
    project = artifact.project
    if project is None or project.created_by is None:
        return None
    user = db.get(User, project.created_by)
    return user.email if user else None


def notify_artifact_failed(db: Session, artifact: ProjectArtifact, stage: str, error_message: str) -> None:
    email = _project_creator_email(db, artifact)
    if email:
        _send_email(
            email,
            f"[Knewron] Artifact '{artifact.artifact_name}' failed at stage '{stage}'",
            f"Artifact {artifact.artifact_id} ({artifact.artifact_type}) failed during '{stage}':\n\n{error_message}",
        )


def notify_review_required(db: Session, artifact: ProjectArtifact) -> None:
    email = _project_creator_email(db, artifact)
    if email:
        _send_email(
            email,
            f"[Knewron] Artifact '{artifact.artifact_name}' needs human review",
            f"Artifact {artifact.artifact_id} has findings that need your review before sign-off.",
        )


def notify_download_ready(db: Session, artifact: ProjectArtifact) -> None:
    email = _project_creator_email(db, artifact)
    if email:
        _send_email(
            email,
            f"[Knewron] Artifact '{artifact.artifact_name}' is ready to download",
            f"Artifact {artifact.artifact_id} completed localization and is ready to download.",
        )
