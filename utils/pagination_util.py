from typing import Type, TypeVar, List, Optional
from pydantic import BaseModel
from schemas.pagination_schema import Pagination, Link
from fastapi import Request
from utils.general_util import serialize_response

T = TypeVar("T", bound=BaseModel)


def get_base_url(request: Request) -> str:
    """
    Get the base URL from the request.
    """
    # return f"{request.url.scheme}://{request.headers['host']}{request.url.path}"
    return f"{request.url.scheme}://{request.url.netloc}{request.url.path}"


def generate_pagination(
    page: int,
    page_size: int,
    total_items: int,
    base_url: str,
    method: str = "GET",
) -> Pagination:
    total_pages = (total_items + page_size - 1) // page_size

    links = [
        Link(rel="self", href=f"{base_url}?offset={page}&limit={page_size}", method=method, title="Current Page"),
        Link(rel="first", href=f"{base_url}?offset=1&limit={page_size}", method=method, title="First Page"),
        Link(rel="last", href=f"{base_url}?offset={total_pages}&limit={page_size}", method=method, title="Last Page")
    ]

    if page > 1:
        links.append(Link(
            rel="prev",
            href=f"{base_url}?offset={page - 1}&limit={page_size}",
            method=method, title="Previous Page")
        )
    if page < total_pages:
        links.append(Link(
            rel="next",
            href=f"{base_url}?offset={page + 1}&limit={page_size}",
            method=method, title="Next Page")
        )

    return Pagination(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        links=links
    )
