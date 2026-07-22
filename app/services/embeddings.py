"""Image embedding backends for ChromaDB similarity matching.

Design ref: `Technical_Design_Document.md` Appendix B — the embedding model
choice is an explicit **open design question**, with "Recommendation: CLIP
(multimodal, good for UI screenshots)". `ClipImageEmbedder` implements that
recommendation; `BedrockTitanImageEmbedder`/`VertexAIImageEmbedder` are
managed-cloud alternatives (no local model download/GPU); `PerceptualHashEmbedder`
is a dependency-light fallback for environments without any ML stack (tests,
CI, minimal dev installs). Select via `AI_EMBEDDING_BACKEND` in `.env`:
`clip` | `phash` | `aws` | `gcp`.
"""
import abc
import base64
import io

from PIL import Image

from app.core.config import get_settings


class ImageEmbedder(abc.ABC):
    @abc.abstractmethod
    def embed(self, image_bytes: bytes) -> list[float]: ...

    @property
    @abc.abstractmethod
    def dimensions(self) -> int: ...


class ClipImageEmbedder(ImageEmbedder):
    """CLIP embeddings via `sentence-transformers` (Technical_Design Appendix B recommendation)."""

    _MODEL_NAME = "clip-ViT-B-32"

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self._MODEL_NAME)

    def embed(self, image_bytes: bytes) -> list[float]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        vector = self._model.encode(image, normalize_embeddings=True)
        return vector.tolist()

    @property
    def dimensions(self) -> int:
        return 512


class BedrockTitanImageEmbedder(ImageEmbedder):
    """AWS: Amazon Titan Multimodal Embeddings via Bedrock Runtime (`boto3`,
    no extra dependency — `boto3` is already a core dependency for the S3
    storage backend).
    """

    _DIMENSIONS = 1024

    def __init__(self) -> None:
        import boto3

        settings = get_settings()
        self._client = boto3.client("bedrock-runtime", region_name=settings.embedding_aws_region)
        self._model_id = settings.embedding_aws_model_id

    def embed(self, image_bytes: bytes) -> list[float]:
        import json

        body = json.dumps(
            {
                "inputImage": base64.b64encode(image_bytes).decode("ascii"),
                "embeddingConfig": {"outputEmbeddingLength": self._DIMENSIONS},
            }
        )
        response = self._client.invoke_model(
            modelId=self._model_id, body=body, contentType="application/json", accept="application/json"
        )
        payload = json.loads(response["body"].read())
        return payload["embedding"]

    @property
    def dimensions(self) -> int:
        return self._DIMENSIONS


class VertexAIImageEmbedder(ImageEmbedder):
    """GCP: Vertex AI multimodal embeddings (`google-cloud-aiplatform`;
    install the `gcp` extra — `poetry install -E gcp`).
    """

    _DIMENSIONS = 1408

    def __init__(self) -> None:
        try:
            import vertexai
            from vertexai.vision_models import MultiModalEmbeddingModel
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "AI_EMBEDDING_BACKEND=gcp requires the 'gcp' extra: poetry install -E gcp"
            ) from exc

        settings = get_settings()
        vertexai.init(project=settings.embedding_gcp_project_id, location=settings.embedding_gcp_location)
        self._model = MultiModalEmbeddingModel.from_pretrained(settings.embedding_gcp_model)

    def embed(self, image_bytes: bytes) -> list[float]:
        from vertexai.vision_models import Image as VertexImage

        embeddings = self._model.get_embeddings(image=VertexImage(image_bytes=image_bytes))
        return list(embeddings.image_embedding)

    @property
    def dimensions(self) -> int:
        return self._DIMENSIONS


class PerceptualHashEmbedder(ImageEmbedder):
    """Deterministic, dependency-light fallback (average-hash grid as a
    fixed-length float vector). Not semantically as strong as CLIP, but
    requires no model download — suitable for tests/CI/minimal installs.
    """

    _GRID = 16  # 16x16 -> 256-dim vector

    def embed(self, image_bytes: bytes) -> list[float]:
        image = Image.open(io.BytesIO(image_bytes)).convert("L").resize((self._GRID, self._GRID))
        pixels = list(image.getdata())
        mean = sum(pixels) / len(pixels)
        return [1.0 if p >= mean else -1.0 for p in pixels]

    @property
    def dimensions(self) -> int:
        return self._GRID * self._GRID


def get_image_embedder() -> ImageEmbedder:
    settings = get_settings()
    if settings.ai_embedding_backend == "clip":
        return ClipImageEmbedder()
    if settings.ai_embedding_backend == "aws":
        return BedrockTitanImageEmbedder()
    if settings.ai_embedding_backend == "gcp":
        return VertexAIImageEmbedder()
    return PerceptualHashEmbedder()
