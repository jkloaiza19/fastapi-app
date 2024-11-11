from fastapi import Depends
from typing import Annotated
from services.http.http_client import get_http_client, HttpClient
from db.database import get_database_session, get_database_initializer, DataBaseSessionInterface, DataBaseInitializerInterface
from services.AI.chat_bot import get_chat_completion_service
from services.AI.interfaces import OpenAIInterface

http_client_dep = Annotated[HttpClient, Depends(get_http_client)]
database_session_dep = Annotated[DataBaseSessionInterface, Depends(get_database_session)]
database_initializer_dep = Annotated[DataBaseInitializerInterface, Depends(get_database_initializer)]
chat_completion_dep = Annotated[OpenAIInterface, Depends(get_chat_completion_service)]
