"""Shared Pydantic base classes.

`CamelModel` matches the camelCase JSON field names used throughout the
documented API contracts in `Technical_Design_Document.md` §4
(e.g. `projectId`, `targetLanguage`, `progressPercent`, `createdAt`).
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class PaginationMeta(CamelModel):
    page: int
    limit: int
    total: int
    total_pages: int
