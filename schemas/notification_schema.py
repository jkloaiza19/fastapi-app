from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime


class NotificationRequest(BaseModel):
    user_id: int = Field(..., description="ID of the user associated with the notification")
    type: str = Field(..., description="Type of the notification")
    title: str = Field(..., description="Title of the notification")
    content: str = Field(..., description="Content of the notification")

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        validate_assignment=True
    )

    @field_validator('content')
    def validate_message(cls, value):
        if len(value) > 255:
            raise ValueError("Message length exceeds 255 characters")
        return value

    @field_validator('type')
    def validate_type(cls, value):
        if value not in ["info", "warning", "error"]:
            raise ValueError("Type must be one of: info, warning, error")
        return value


class NotificationResponse(NotificationRequest):
    id: int = Field(default=None, description="Unique identifier for the notification")
    created_at: datetime = Field(default=None, description="Timestamp when the notification was created")
    is_read: bool = Field(default=False, description="Indicates whether the notification has been read")
