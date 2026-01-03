from abc import ABC, abstractmethod
from schemas.login_schema import SignUpModel
from fastapi import BackgroundTasks, Request
from db.interfaces import DataBaseRepositoryInterface


class LoginServiceInterface(ABC):
    @abstractmethod
    async def login(self, username: str, password: str) -> str:
        pass

    @abstractmethod
    async def logout(self, username: str) -> bool:
        pass

    @abstractmethod
    async def register(self,
                       user: SignUpModel,
                       background_tasks: BackgroundTasks,
                       db: DataBaseRepositoryInterface,
                       request: Request) -> bool:
        pass

    # @abstractmethod
    # async def get_user(self, username: str) -> dict:
    #     pass
    #
    # @abstractmethod
    # async def get_users(self) -> list:
    #     pass
    #
    # @abstractmethod
    # async def delete_user(self, username: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def update_user(self, username: str, password: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def change_password(self, username: str, old_password: str, new_password: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def get_user_role(self, username: str) -> str:
    #     pass
    #
    # @abstractmethod
    # async def get_user_roles(self) -> list:
    #     pass
    #
    # @abstractmethod
    # async def add_user_role(self, username: str, role: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def delete_user_role(self, username: str, role: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def get_user_permissions(self, username: str) -> list:
    #     pass
    #
    # @abstractmethod
    # async def get_user_roles_permissions(self) -> dict:
    #     pass
    #
    # @abstractmethod
    # async def add_user_permission(self, username: str, permission: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def delete_user_permission(self, username: str, permission: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def get_user_role_permissions(self, role: str) -> list:
    #     pass
    #
    # @abstractmethod
    # async def add_user_role_permission(self, role: str, permission: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def delete_user_role_permission(self, role: str, permission: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def get_user_role_permission(self, role: str, permission: str) -> bool:
    #     pass
    #
    # @abstractmethod
    # async def get_user_permissions(self, username: str) -> list:
    #     pass


# class LoginService(LoginServiceInterface):
