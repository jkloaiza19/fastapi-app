import typing
import strawberry
from strawberry.types import Info
from strawberry.exceptions import StrawberryException
from fastapi import HTTPException
from graphql_server.schemas.user import User


@strawberry.type
class UserQuery:
    @strawberry.field(graphql_type=User)
    async def user(self, user_id: int, info: Info) -> User:
        try:
            user_repository = info.context['user_repository']
            # db = info.context['db']
            # print(db)
            user = await user_repository.find_unique(id=user_id)

            if not user:
                raise StrawberryException("User not found")

            return User(
                email=user.email,
                username=user.username,
                is_confirmed=user.is_confirmed,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        except StrawberryException as e:
            raise HTTPException(f"Error fetching user: {str(e)}")


@strawberry.type
class UserMutation:
    @strawberry.mutation(graphql_type=User)
    async def create_user(self):
        return "wipip"
