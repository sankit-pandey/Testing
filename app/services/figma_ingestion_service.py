"""Figma metadata ingestion — Design ref: `Figma_Integration.md` §3 step 8
("a service/API consumes the metadata JSON and populates ChromaDB"), §4, §9.
Story 4.4 (the runtime counterpart of "load metadata"; the plugin/export
step itself is design-time and out of app scope per
`Implementation/Design_Traceability_Matrix.md`).

Consumes one "Build & Export Metadata" plugin output object (§4 JSON shape)
per call: renders the baseline-language frame via Figma, embeds it, and
stores both the `figma_images` row and the ChromaDB vector so the runtime
image sub-pipeline (Story 5.1) can match against it.
"""
import hashlib
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.figma_images import FigmaImage
from app.services.chromadb_service import ChromaDBService
from app.services.figma_service import FigmaService


def ingest_figma_metadata(
    db: Session, tenant_id: uuid.UUID, product_id: uuid.UUID, metadata_json: dict[str, Any]
) -> FigmaImage:
    """Ingest one frame's metadata (Figma_Integration §4 JSON structure)."""
    figma_file_key = metadata_json["figma_file_key"]
    frame_id = metadata_json["node_id"]
    localization = metadata_json.get("Localization", {})
    modes: dict[str, str] = localization.get("modes", {})
    baseline_language = next(iter(modes.values()), None)
    scale = metadata_json.get("scale", 1)
    fmt = metadata_json.get("format", "png")

    figma = FigmaService(tenant_id=tenant_id)
    image_bytes = figma.export_frame(figma_file_key, frame_id, scale=scale, fmt=fmt)
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    figma_image = FigmaImage(
        tenant_id=tenant_id,
        product_id=product_id,
        figma_file_key=figma_file_key,
        figma_frame_id=frame_id,
        frame_name=metadata_json.get("frame_name"),
        image_hash=image_hash,
        text_elements=localization.get("variables", []),
        variable_mapping=localization,
        original_language=baseline_language,
        metadata_={
            "absolute_bounding_box": metadata_json.get("absolute_bounding_box"),
            "scale": scale,
            "format": fmt,
        },
    )
    db.add(figma_image)
    db.flush()

    chroma = ChromaDBService()
    chromadb_id = chroma.add_image(
        figma_image.figma_image_id,
        image_bytes,
        metadata={
            "product_id": str(product_id),
            "screen_name": metadata_json.get("node_name"),
            "figma_frame_id": frame_id,
            "figma_file_key": figma_file_key,
        },
    )
    figma_image.chromadb_id = uuid.UUID(chromadb_id)
    db.commit()
    return figma_image
