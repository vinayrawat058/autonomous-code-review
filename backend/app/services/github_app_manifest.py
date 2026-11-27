"""
GitHub App Manifest helpers.

Register an App from a JSON manifest, then exchange the one-time code for
credentials (app id, PEM, webhook secret, HTML URLs).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

DEFAULT_MANIFEST: dict[str, Any] = {
    "name": "Agentic PR Review Studio",
    "url": "https://github.com/vinayrawat058/autonomous-code-review",
    "public": False,
    "default_events": ["pull_request"],
    "default_permissions": {
        "contents": "read",
        "metadata": "read",
        "pull_requests": "write",
    },
}


def build_manifest(*, webhook_url: str, redirect_url: str) -> dict[str, Any]:
    manifest = dict(DEFAULT_MANIFEST)
    manifest["hook_attributes"] = {"url": webhook_url, "active": True}
    manifest["redirect_url"] = redirect_url
    manifest["callback_urls"] = [redirect_url]
    return manifest


def exchange_manifest_code(code: str) -> dict[str, Any]:
    """Convert a manifest redirect code into App credentials."""
    url = f"https://api.github.com/app-manifests/{code}/conversions"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Manifest conversion failed ({response.status_code}): {response.text[:500]}"
            )
        return response.json()


def _upsert_env_value(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    line = f"{key}={value}"
    if pattern.search(text):
        return pattern.sub(line, text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"


def persist_manifest_credentials(payload: dict[str, Any], *, env_path: Path) -> dict[str, str]:
    """
    Write PEM + update .env with App id / webhook secret / private key path.

    Returns non-secret paths useful for the setup UI.
    """
    pem = str(payload.get("pem") or "")
    app_id = str(payload.get("id") or "")
    webhook_secret = str(payload.get("webhook_secret") or "")
    if not pem or not app_id:
        raise RuntimeError("Manifest conversion response missing pem or id.")

    secrets_dir = env_path.parent / ".secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    pem_path = secrets_dir / "github-app.pem"
    pem_path.write_text(pem, encoding="utf-8")

    env_text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    env_text = _upsert_env_value(env_text, "GITHUB_APP_ID", app_id)
    env_text = _upsert_env_value(env_text, "GITHUB_APP_PRIVATE_KEY_PATH", str(pem_path.resolve()))
    env_text = _upsert_env_value(env_text, "GITHUB_APP_PRIVATE_KEY", "")
    env_text = _upsert_env_value(env_text, "GITHUB_WEBHOOK_SECRET", webhook_secret)
    env_text = _upsert_env_value(env_text, "GITHUB_WEBHOOK_REQUIRE_SECRET", "true")
    env_text = _upsert_env_value(env_text, "GITHUB_DEFAULT_OWNER", "vinayrawat058")
    env_text = _upsert_env_value(env_text, "GITHUB_DEFAULT_REPO", "autonomous-code-review")
    env_path.write_text(env_text, encoding="utf-8")

    # Refresh in-process settings used by later requests (uvicorn --reload will also pick up .env).
    settings.github_app_id = app_id
    settings.github_app_private_key_path = str(pem_path.resolve())
    settings.github_app_private_key = ""
    settings.github_webhook_secret = webhook_secret
    settings.github_webhook_require_secret = True

    return {
        "app_id": app_id,
        "pem_path": str(pem_path.resolve()),
        "html_url": str(payload.get("html_url") or ""),
        "slug": str(payload.get("slug") or ""),
    }


def manifest_json(*, webhook_url: str, redirect_url: str) -> str:
    return json.dumps(build_manifest(webhook_url=webhook_url, redirect_url=redirect_url))
