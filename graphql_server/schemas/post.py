import strawberry


@strawberry.type
class Post:
    id: int
    title: str
    content: str
    author_id: int
    image_url: str
    created_at: str
    updated_at: str
