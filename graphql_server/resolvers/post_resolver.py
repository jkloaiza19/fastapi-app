import typing
import strawberry
from strawberry.types import Info
from strawberry.exceptions import StrawberryException
from strawberry.fastapi import GraphQLRouter
from fastapi import HTTPException
from graphql_server.schemas.post import Post


@strawberry.type
class PostQuery:
    @strawberry.field(graphql_type=Post)
    async def post(self, user_id: int, info: Info) -> Post:
        try:
            user_repository = info.context['user_repository']
            user = await user_repository.find_unique(id=user_id)

            if not user:
                raise StrawberryException("User not found")

            return Post(
                id=user.id,
                title=user.username,
                content=user.username,
                image_url=user.email,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        except StrawberryException as e:
            raise HTTPException(f"Error fetching post: {str(e)}")


@strawberry.type
class PostMutation:
    @strawberry.mutation(graphql_type=Post)
    async def create_post(self):
        return "wipip"
