from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator
from abc import ABC, abstractmethod
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ApiError
import aiofiles

from fastapi import Request, status, HTTPException
from fastapi.templating import Jinja2Templates
from jinja2 import Template
from core.logger import get_logger
from core.config import settings
from utils.templates_util import TemplateType


logger = get_logger(__name__)


class EmailClientInterface(ABC):
    @abstractmethod
    async def send_email(
            self,
            to: List[str],
            cc: Optional[List[str]],
            bcc: Optional[List[str]],
            subject: str,
            body: str,
            message_type: str
    ) -> None:
        pass

    @abstractmethod
    def is_valid_template(self, template: str) -> bool:
        pass

    @abstractmethod
    def get_template(self, template_name: str, request: Request, context: Dict[str, Any] = {}) -> str:
        pass

    @abstractmethod
    async def send_confirmation_email(self, email: str, username: str, confirmation_link: str) -> None:
        pass

    @abstractmethod
    def get_email_template(self, template_name: str, context: Dict[str, Any] = {}) -> str:
        pass


class EmailClient(EmailClientInterface):
    def __init__(self):
        self.templates = Jinja2Templates(directory="templates")
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.GODADDY_SMTP_USER,
            MAIL_PASSWORD=settings.GODADDY_SMTP_PASSWORD,
            MAIL_FROM=settings.GODADDY_SMTP_USER or "test@email.com",
            MAIL_PORT=settings.GODADDY_SMTP_PORT,
            MAIL_SERVER=settings.GODADDY_SMTP_HOST,
            MAIL_STARTTLS=False,
            MAIL_SSL_TLS=True,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        self.fast_mail = FastMail(self.conf)

    async def send_email(
            self,
            to: List[str],
            subject: str,
            body: str,
            cc: Optional[List[str]] = [],
            bcc: Optional[List[str]] = [],
            message_type: MessageType = MessageType.html
    ) -> None:
        logger.info("Sending email")
        try:
            message = MessageSchema(
                subject=subject,
                recipients=to,
                body=body,
                subtype=message_type,
                bcc=bcc,
                cc=cc
            )

            await self.fast_mail.send_message(message)
        except ApiError as e:
            logger.error(f"Error sending email: {e}")
            raise e

    def is_valid_template(self, template: str) -> bool:
        return template in (item.value for item in TemplateType)

    def get_template(self, template_name: str, request: Request, context: Dict[str, Any] = {}) -> str:
        template = self.templates.TemplateResponse(
            request=request, name=template_name, context=context
        )

        return template

    async def send_confirmation_email(self, email: str, username: str, confirmation_link: str) -> None:
        try:
            body_html = await self.get_email_template(
                template_name=TemplateType.NEW_ACCOUNT.value,
                context={"username": username, "confirmation_link": confirmation_link}
            )

            await self.send_email(
                    to=[email],
                    subject="Successfully signed up!",
                    body=body_html,
            )
        except ApiError as e:
            logger.error(f"Could not send the confirmation email {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

    async def get_email_template(self, template_name: str, context: Dict[str, Any] = {}) -> str:
        template_path = Path(__file__).parent.parent.parent / "templates" / template_name

        async with aiofiles.open(template_path, mode="r") as file:
            template_str = await file.read()

        html_content = Template(template_str).render(context)
        return html_content


async def get_email_client() -> AsyncGenerator[EmailClientInterface, None]:
    try:
        email_client = EmailClient()
        print(f"Email client initialized: {email_client}")
        yield email_client
    except Exception as e:
        logger.error(f"{str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize Email service. {str(e)}")
