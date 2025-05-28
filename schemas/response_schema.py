from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from .notification_schema import NotificationResponse
from .user_schema import UserResponse
from .pagination_schema import Pagination


class   ResponseWithPagination(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pagination: Pagination | None = None
    results: list[BaseModel | UserResponse | NotificationResponse] | None = None
