"""Aggregates all `/api/v1` routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    artifacts,
    audit,
    auth,
    figma,
    health,
    products,
    projects,
    reviews,
    storage,
    tenants,
    webhooks,
    websocket,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(products.router)
api_router.include_router(projects.router)
api_router.include_router(artifacts.router)
api_router.include_router(reviews.router)
api_router.include_router(audit.router)
api_router.include_router(figma.router)
api_router.include_router(storage.router)
api_router.include_router(webhooks.router)
api_router.include_router(websocket.router)
