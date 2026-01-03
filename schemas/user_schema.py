from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str = Field(min_length=5, max_length=20)
    email: str = Field(pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


class UserRequest(UserBase):
    password: str = Field(
        min_length=8,
        max_length=20,
        title="Password must be 8-20 characters long, contain at least one uppercase letter, one lowercase letter, "
              "one digit, and one special character."
    )

    @field_validator('password')
    def validate_password(cls, value):
        if not any(char.islower() for char in value):
            raise ValueError('Password must contain at least one lowercase letter.')
        if not any(char.isupper() for char in value):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one digit.')
        if not any(char in '!@#$%^&*' for char in value):
            raise ValueError('Password must contain at least one special character: !@#$%^&*')
        return value


class UserResponse(UserBase):
    id: int = Field()
    is_confirmed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
