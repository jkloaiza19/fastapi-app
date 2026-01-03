from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime


class Link(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rel: str
    href: str
    method: str
    title: str | None = None


class Pagination(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int
    page_size: int
    total_items: int
    total_pages: int
    links: list[Link] | None = None
