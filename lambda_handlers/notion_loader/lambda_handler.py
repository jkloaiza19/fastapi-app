from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

# Import the sync runner and config loader from your project
# Packaging instructions below show how to include the whole project in the ZIP
from utils.notion_loader import load_config_from_env, run_sync

logger = logging.getLogger("notion_sync_lambda")
logger.setLevel(logging.INFO)


def _apply_event_env_overrides(event: Dict[str, Any]) -> None:
    """Optionally override environment variables from the invocation event.

    Provide an `env` dict in the event for testing (not recommended in prod).
    """
    if not event:
        return
    env = event.get("env") or event.get("environment")
    if not isinstance(env, dict):
        return
    for k, v in env.items():
        os.environ[str(k)] = str(v)


def _load_secrets_to_env() -> None:
    """Fetch a secret value from Secrets Manager and set environment variables.

    If the secret string is JSON, its keys are set as env vars (top-level keys only).
    Otherwise the secret is set as the environment variable whose name matches the
    last path component of the ARN (common patterns), or to a sensible default.
    """

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
    )

    secret_id = os.environ.get("SECRET_NAME", "notion-token")
    # if not secret_arn:
    #     return
    # if client is None:
    #     client = boto3.client("secretsmanager")

    try:
        resp = client.get_secret_value(SecretId=secret_id)
    except ClientError as e:
        logger.exception("Failed to fetch secret %s", secret_id)
        raise

    secret_str = resp.get("SecretString")
    if not secret_str:
        # binary secret case; ignore for now
        logger.warning("Secret %s has no SecretString, skipping", secret_id)
        return

    # Try to parse JSON
    try:
        parsed = json.loads(secret_str)
    except Exception:
        parsed = None

    if isinstance(parsed, dict):
        for k, v in parsed.items():
            if v is None:
                continue
            os.environ[str(k)] = str(v)
            logger.debug("Set env from secret: %s", k)
    else:
        os.environ[secret_id] = secret_str
        logger.debug("Set env from secret: %s", secret_id)
        # # Plain string; try guess variable name
        # # If the secret ARN includes a name like /prod/notion-token, use last token
        # name_part = secret_arn.split(":")[-1]
        # # Use a default mapping heuristic
        # guessed_name = None
        # if "notion" in name_part.lower():
        #     guessed_name = "NOTION_TOKEN"
        # elif "openai" in name_part.lower() or "openai" in secret_arn.lower():
        #     guessed_name = "OPENAI_API_KEY"
        # elif "astra" in name_part.lower() or "astra" in secret_arn.lower():
        #     guessed_name = "ASTRA_DB_TOKEN"
        #
        # if not guessed_name:
        #     # fallback to SECRET_VALUE
        #     guessed_name = "SECRET_VALUE"
        #
        # os.environ[guessed_name] = secret_str
        # logger.debug("Set env %s from secret %s", guessed_name, secret_id)


# def _load_all_secrets_from_env() -> None:
#     """Detect secret ARN env vars and load them into environment.
#
#     Supported env vars (optional): NOTION_SECRET_ARN, OPENAI_SECRET_ARN, ASTRA_SECRET_ARN
#     """
#     notion_arn = os.environ.get("NOTION_SECRET_ARN")
#     openai_arn = os.environ.get("OPENAI_SECRET_ARN")
#     astra_arn = os.environ.get("ASTRA_SECRET_ARN")
#
#     if not any([notion_arn, openai_arn, astra_arn]):
#         return
#
#     session = boto3.session.Session()
#     client = session.client(
#         service_name='secretsmanager',
#         region_name=region_name
#     )
#
#     if notion_arn:
#         _load_secret_to_env(notion_arn, client=client)
#     if openai_arn:
#         _load_secret_to_env(openai_arn, client=client)
#     if astra_arn:
#         _load_secret_to_env(astra_arn, client=client)


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """AWS Lambda handler entrypoint.

    This runs the async `run_sync()` helper from `utils.notion_loader` inside
    an asyncio event loop and returns a JSON response compatible with API Gateway.

    Note: ensure the deployment package contains your project code (fastapi-app contents)
    and all required dependencies (see cloudformation/README.md and build script).
    """
    try:
        logger.info("Lambda invoked: starting Notion -> Astra sync")
        _apply_event_env_overrides(event)

        # # If secret ARNs were provided, load them into the environment before reading config
        # _load_all_secrets_from_env()
        #
        # # Optionally, refresh/load config from env (function uses settings internally)
        # _ = load_config_from_env()

        # Load secrets from the Secrets Manager
        _load_secrets_to_env()

        # run_sync is an async function that returns a dict. Run it in a fresh event loop.
        result = asyncio.run(run_sync())

        body = json.dumps({"ok": True, "result": result})
        return {"statusCode": 200, "body": body}
    except Exception as e:
        logger.exception("Sync failed")
        body = json.dumps({"ok": False, "error": str(e)})
        return {"statusCode": 500, "body": body}
