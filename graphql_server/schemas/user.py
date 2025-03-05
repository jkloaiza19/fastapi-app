import strawberry


@strawberry.type
class User:
    email: str
    username: str
    is_confirmed: bool
    created_at: str
    updated_at: str
