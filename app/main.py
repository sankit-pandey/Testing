"""FastAPI entry point — REST API, WebSocket, and webhook receivers.

Design ref: `LOCKED_Design_v1.0.md` §10, §11. Story 0.1.
"""
from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware, register_error_handlers

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(CorrelationIdMiddleware)
register_error_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)
