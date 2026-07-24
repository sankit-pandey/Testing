"""Pydantic schema for the Figma metadata ingestion endpoint — Design ref:
`Figma_Integration.md` §4. Story 4.4.
"""
import uuid
from typing import Any

from pydantic import BaseModel, Field


class FigmaIngestRequest(BaseModel):
    product_id: uuid.UUID = Field(alias="productId")
    metadata: dict[str, Any] = Field(description="One frame's Build & Export Metadata plugin output")

    model_config = {"populate_by_name": True}


class FigmaIngestResponse(BaseModel):
    figma_image_id: uuid.UUID
    chromadb_id: uuid.UUID | None
