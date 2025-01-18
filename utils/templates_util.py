from enum import Enum

from jinja2 import Template
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Dict, Any

from starlette.templating import _TemplateResponse

templates = Jinja2Templates(directory="templates")


class TemplateType(str, Enum):
    CONFIRM_USER = "confirm_email_template.html"
    NEW_ACCOUNT = "new_account_template.html"


def get_template(template_name: str, request: Request, context: Dict[str, Any] = {}) -> _TemplateResponse:
    template = templates.TemplateResponse(
        request=request, name=template_name, context=context
    )

    return template
