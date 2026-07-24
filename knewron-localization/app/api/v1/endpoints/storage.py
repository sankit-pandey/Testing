"""Local storage dev-fallback endpoints — see `LocalStorageBackend` in
`app/services/storage_service.py`. Not used when `STORAGE_BACKEND=s3`
(real S3 presigned URLs are used directly by the client instead). Story 4.1.
"""
from fastapi import APIRouter, HTTPException, Request, Response, status
from jose import JWTError, jwt

from app.core.config import get_settings
from app.services.storage_service import STORAGE_TOKEN_TYPE, LocalStorageBackend

router = APIRouter(prefix="/storage/local", tags=["storage"])


def _decode(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired URL") from exc
    if payload.get("type") != STORAGE_TOKEN_TYPE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage token")
    return payload


@router.put("/{token}")
async def local_upload(token: str, request: Request) -> Response:
    payload = _decode(token)
    if payload["action"] != "put":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is not an upload URL")

    body = await request.body()
    LocalStorageBackend().put_bytes(payload["key"], body, payload.get("content_type"))
    return Response(status_code=status.HTTP_200_OK)


@router.get("/{token}")
async def local_download(token: str) -> Response:
    payload = _decode(token)
    if payload["action"] != "get":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is not a download URL")

    backend = LocalStorageBackend()
    if not backend.exists(payload["key"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    data = backend.get_bytes(payload["key"])
    return Response(content=data, media_type="application/octet-stream")
