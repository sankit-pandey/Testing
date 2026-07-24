"""AI review — Design ref: `Requirements_Document.md` §4.5.3, §5.9.2;
`Database_Schema.md` §11 (`review_findings`). Stories 5.1, 6.1.

Real automated visual/text-completeness QA (OCR-based comparison against
source, layout diffing) needs a vision-QA model this exercise cannot train;
these checks implement the structural/completeness parts of Requirements
§4.5.3 that don't need one (corruption, byte-size sanity, expected-element
counts), producing the same `review_findings` shape a stronger model would.
"""
import io
from dataclasses import dataclass
from typing import Any

from PIL import Image, UnidentifiedImageError

CRITICAL = "critical"
MAJOR = "major"
MINOR = "minor"
INFO = "info"


@dataclass
class Finding:
    severity: str
    category: str
    description: str
    location: dict[str, Any] | None = None


def review_rendered_image(image_bytes: bytes, *, expected_variable_count: int) -> list[Finding]:
    """Checks from Requirements §4.5.3: readable/not-corrupt, non-trivial size
    (proxy for "not cut off/blank"), and a completeness proxy vs. how many
    text variables should have been localized.
    """
    findings: list[Finding] = []

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        findings.append(Finding(CRITICAL, "quality", f"Rendered image is corrupt or unreadable: {exc}"))
        return findings

    if width < 10 or height < 10:
        findings.append(
            Finding(MAJOR, "formatting", f"Rendered image is suspiciously small ({width}x{height})")
        )

    if len(image_bytes) < 500 and expected_variable_count > 0:
        findings.append(
            Finding(
                MINOR,
                "completeness",
                "Rendered image is very small in bytes for a frame with translatable text; "
                "verify text was not dropped",
            )
        )

    return findings


def review_document_completeness(
    *, expected_image_count: int, assembled_image_count: int, expected_tables: int, actual_tables: int
) -> list[Finding]:
    """QA checks from Requirements §5.9.2 (post-Lokalise, Knewron-side):
    completeness vs. source, no missing content.
    """
    findings: list[Finding] = []
    if assembled_image_count < expected_image_count:
        findings.append(
            Finding(
                MAJOR,
                "completeness",
                f"Assembled document has {assembled_image_count} images, expected {expected_image_count}",
            )
        )
    if actual_tables != expected_tables:
        findings.append(
            Finding(
                MAJOR,
                "formatting",
                f"Assembled document has {actual_tables} tables, expected {expected_tables}",
            )
        )
    return findings
