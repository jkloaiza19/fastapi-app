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
from utils.notion_loader import load_config_from_env, NotionAstraSync

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
        _load_secrets_to_env()

        cfg = load_config_from_env()
        sync = NotionAstraSync(cfg)
        result = asyncio.run(sync.run())

        # Log summary for CloudWatch
        print(json.dumps(result["summary"]))
        body = json.dumps({"ok": True, "result": result})
        return {"statusCode": 200, "body": body}
    except Exception as e:
        logger.exception("Sync failed")
        body = json.dumps({"ok": False, "error": str(e)})
        return {"statusCode": 500, "body": body}
