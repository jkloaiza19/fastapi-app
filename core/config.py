import secrets
from typing import Optional, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DATABASE_URL: Optional[str] = None
    ASYNC_DATABASE_URL: Optional[str] = None
    DB_FORCE_ROLLBACK: bool = False
    AWS_REGION: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_BUCKET_URL: str = ""
    AWS_API_VERSION: str = ""
    SENTRY_DNS: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ENCRYPTION_KEY: str = ""
    GODADDY_SMTP_HOST: Optional[str] = ""
    GODADDY_SMTP_PORT: Optional[int] = 465
    GODADDY_SMTP_USER: Optional[str] = ""
    GODADDY_SMTP_PASSWORD: Optional[str] = ""
    DEEP_AI_API_KEY: Optional[str] = ""
    OPENAI_API_KEY: Optional[str] = ""
    OPENAI_HTTP_URL: Optional[str] = ""
    CHAT_COMPLETION_MODEL: Optional[str] = "gpt-4o"
    COGNITO_USER_POOL_ID: Optional[str] = ""
    COGNITO_CLIENT_ID: Optional[str] = ""
    COGNITO_CLIENT_SECRET: Optional[str] = ""
    COGNITO_JWK_URL: Optional[str] = ""
    ASTRA_CLIENT_ID: Optional[str] = ""
    ASTRA_SECRET_KEY: Optional[str] = ""
    ASTRA_DB_NAMESPACE: Optional[str] = ""
    ASTRA_DB_TOKEN: Optional[str] = ""
    ASTRA_DB_ENDPOINT: Optional[str] = ""

    def is_local_environment(self) -> bool:
        return self.ENVIRONMENT == "local"

    # def load_secrets_from_aws(self, secret_name: str):
    #     if self.ENVIRONMENT == "production":
    #         session = boto3.session.Session()
    #         client = session.client(
    #             service_name="secretsmanager",
    #             region_name=self.AWS_REGION,
    #         )
    #         try:
    #             response = client.get_secret_value(SecretId=secret_name)
    #             secret_dict = json.loads(response["SecretString"])
    #             for key, value in secret_dict.items():
    #                 if hasattr(self, key):
    #                     setattr(self, key, value)
    #         except Exception as e:
    #             raise RuntimeError(f"Failed to load secrets: {e}")


settings = Settings()
# if settings.ENVIRONMENT == "production":
#     settings.load_secrets_from_aws("secret-name")
