"""Figma integration — Design ref: `Figma_Integration.md` (all sections);
`Technical_Design_Document.md` §2.1.5; `Database_Schema.md` §8 (`figma_images`).
Story 4.4.

Implements exactly the operations `Figma_Integration.md` describes: load
frame metadata (§4), set variable values for the target-language mode (§5,
§6), and render/export the frame using the metadata's bbox/scale/format (§7).
Wrapped in a circuit breaker + bounded concurrency + retry-with-backoff
(`Requirements_Document.md` §4.4.3, §4.7.2 — min 1 call/screenshot, 5-10
concurrent, 3-5 retries with exponential backoff).
"""
import threading
import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.figma_images import FigmaImage
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.retry import with_retry

logger = get_logger(__name__)


class FigmaError(Exception):
    """Raised when a Figma API call fails after retries."""


class FigmaService:
    def __init__(self) -> None:
        settings = get_settings()
        self.token = settings.figma_access_token
        self.base_url = settings.figma_base_url
        self.max_retries = settings.figma_max_retries
        self.breaker = CircuitBreaker("figma")
        self._semaphore = threading.Semaphore(settings.figma_max_concurrent_requests)

    def _headers(self) -> dict[str, str]:
        return {"X-Figma-Token": self.token or ""}

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            with self._semaphore, httpx.Client(timeout=30.0) as client:
                response = client.request(method, f"{self.base_url}{path}", headers=self._headers(), **kwargs)
                response.raise_for_status()
                return response.json()

        try:
            return self.breaker.call(
                lambda: with_retry(_call, max_attempts=self.max_retries, exceptions=(httpx.HTTPError,))
            )
        except httpx.HTTPError as exc:
            raise FigmaError(f"Figma API call to {path} failed: {exc}") from exc

    def get_file(self, file_key: str) -> dict[str, Any]:
        """Read Figma file metadata (Requirements §4.4.3)."""
        return self._request("GET", f"/files/{file_key}")

    def set_variable_values(self, file_key: str, mode_id: str, variable_values: dict[str, str]) -> None:
        """Update variable values (translations) for one mode — Technical_Design
        §2.1.5 `updateVariables`; Figma_Integration §5, §6.
        """
        if not variable_values:
            return
        payload = {
            "variableModeValues": [
                {"variableId": variable_id, "modeId": mode_id, "value": value}
                for variable_id, value in variable_values.items()
            ]
        }
        self._request("POST", f"/files/{file_key}/variables", json=payload)

    def get_or_create_mode(
        self, file_key: str, collection_id: str, language_code: str, existing_modes: dict[str, str]
    ) -> str:
        """Return the modeId for `language_code`, creating a new mode in the
        variable collection if the design-time export didn't already seed one
        (Figma_Integration §5 — design-time seeds one baseline mode; runtime
        adds the target-language mode).
        """
        for mode_id, lang in existing_modes.items():
            if lang == language_code:
                return mode_id

        payload = {
            "variableModes": [
                {
                    "action": "CREATE",
                    "id": f"tmp_{language_code}",
                    "variableCollectionId": collection_id,
                    "name": language_code,
                }
            ]
        }
        result = self._request("POST", f"/files/{file_key}/variables", json=payload)
        temp_id_map = result.get("meta", {}).get("tempIdToRealId", {})
        new_mode_id = temp_id_map.get(f"tmp_{language_code}")
        if not new_mode_id:
            raise FigmaError(f"Figma did not return a real mode id for new mode '{language_code}'")
        return new_mode_id

    def export_frame(self, file_key: str, node_id: str, *, scale: float = 1, fmt: str = "png") -> bytes:
        """Export the frame as an image (Figma_Integration §7 — bbox/scale/format
        carried in the frame's stored metadata; the export call itself takes
        `ids`/`scale`/`format`).
        """
        data = self._request(
            "GET", f"/images/{file_key}", params={"ids": node_id, "scale": scale, "format": fmt}
        )
        image_url = data.get("images", {}).get(node_id)
        if not image_url:
            raise FigmaError(f"Figma export returned no image URL for node {node_id}")

        def _download() -> bytes:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(image_url)
                response.raise_for_status()
                return response.content

        try:
            return self.breaker.call(
                lambda: with_retry(_download, max_attempts=self.max_retries, exceptions=(httpx.HTTPError,))
            )
        except httpx.HTTPError as exc:
            raise FigmaError(f"Failed to download exported Figma image: {exc}") from exc

    def render_localized_frame(
        self, figma_image: FigmaImage, target_language: str, translations: dict[str, str]
    ) -> bytes:
        """End-to-end render: set the target-language mode's variable values,
        then export the frame — Figma_Integration §6.

        `translations` maps variable `name` (the stable key, §5) -> translated text.
        """
        mapping = figma_image.variable_mapping or {}
        collection_id = mapping.get("collectionId")
        modes = mapping.get("modes", {})
        variables = mapping.get("variables", [])

        mode_id = self.get_or_create_mode(
            figma_image.figma_file_key, collection_id, target_language, modes
        )

        name_to_id = {v["name"]: v["variableId"] for v in variables}
        variable_values = {
            name_to_id[name]: text for name, text in translations.items() if name in name_to_id
        }
        self.set_variable_values(figma_image.figma_file_key, mode_id, variable_values)

        metadata = figma_image.metadata_ or {}
        bbox_scale = metadata.get("scale", 1)
        fmt = metadata.get("format", "png")
        return self.export_frame(
            figma_image.figma_file_key, figma_image.figma_frame_id, scale=bbox_scale, fmt=fmt
        )


def get_text_elements(figma_image: FigmaImage) -> list[dict[str, Any]]:
    """Source text per variable, from cached metadata (Figma_Integration §4)."""
    mapping = figma_image.variable_mapping or {}
    return mapping.get("variables", [])
