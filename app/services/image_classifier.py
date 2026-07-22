"""AI image classifier — UI screenshot vs non-UI.

Design ref: `Technical_Design_Document.md` §2.1.3; `Requirements_Document.md`
§4.2.1 (confidence threshold **70%**, configurable). Story 5.1.

`Technical_Design_Document.md` §2.1.3 specifies a trained model (min. 1000
labeled samples/category, target >90% accuracy) — that training data/model
does not exist yet. `HeuristicUIScreenshotClassifier` is an honest,
fully-wired placeholder (aspect ratio + edge-density, both real structural
signals for UI chrome/text) so the confidence-threshold gating, review
flagging, and DB writes are all correct now; swap in a trained model behind
the same `ImageClassifier` interface later without touching callers.
"""
import io
from abc import ABC, abstractmethod

from PIL import Image, ImageFilter

from app.core.config import get_settings


class ImageClassifier(ABC):
    @abstractmethod
    def classify(self, image_bytes: bytes) -> tuple[str, float]:
        """Return `(classification, confidence)`; classification is
        `'ui_screenshot'` or `'other'` (Database_Schema.md §7 also allows
        `diagram`/`photo`/`chart`, not distinguished by this heuristic).
        """


class HeuristicUIScreenshotClassifier(ImageClassifier):
    def classify(self, image_bytes: bytes) -> tuple[str, float]:
        image = Image.open(io.BytesIO(image_bytes)).convert("L")
        width, height = image.size
        if not width or not height:
            return "other", 0.0

        aspect = width / height
        aspect_score = 1.0 if 1.2 <= aspect <= 2.2 else 0.4

        edges = image.filter(ImageFilter.FIND_EDGES)
        edge_density = sum(edges.getdata()) / (255.0 * width * height)
        density_score = min(edge_density * 4.0, 1.0)

        confidence = round((aspect_score + density_score) / 2.0, 4)
        classification = "ui_screenshot" if confidence >= 0.5 else "other"
        return classification, confidence


def get_image_classifier() -> ImageClassifier:
    return HeuristicUIScreenshotClassifier()


def is_confident(confidence: float) -> bool:
    return confidence >= get_settings().ai_image_confidence_threshold
