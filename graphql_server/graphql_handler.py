
from strawberry.fastapi import GraphQLRouter
from strawberry.tools import merge_types
from strawberry.schema import Schema
from strawberry.schema.config import StrawberryConfig

from graphql_server.context import get_context
# from domains.users.queries import UserQuery
# from domains.teams.queries import TeamQuery
#
# from domains.users.mutations import UserMutation
# from domains.teams.mutations import TeamMutation
from graphql_server.resolvers.user_resolver import UserQuery, UserMutation
from graphql_server.resolvers.post_resolver import PostQuery, PostMutation


queries = (UserQuery, PostQuery)
mutations = (UserMutation, PostMutation)

Query = merge_types('Query', (UserQuery, PostQuery))
Mutation = merge_types('Mutation', (UserMutation, PostMutation))

schema = Schema(query=Query, mutation=Mutation) # config=StrawberryConfig(auto_camel_case=False)

graphql_app = GraphQLRouter(schema, context_getter=get_context)
