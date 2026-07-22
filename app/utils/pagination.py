"""Pagination helpers matching the `{page, limit, total, totalPages}` shape
used throughout `Technical_Design_Document.md` §4.1.1.
"""
import math

from app.schemas.base import PaginationMeta


def build_pagination_meta(*, page: int, limit: int, total: int) -> PaginationMeta:
    total_pages = math.ceil(total / limit) if limit else 0
    return PaginationMeta(page=page, limit=limit, total=total, total_pages=total_pages)
