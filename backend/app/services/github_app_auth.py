"""
GitHub App authentication: App JWT → installation access token.

Falls back to GITHUB_TOKEN when App credentials are not configured (local demos).
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from app.core.config import settings

API = "https://api.github.com"


class GitHubAppAuthError(RuntimeError):
    """Raised when App credentials or token exchange fail."""


def _load_private_key() -> str:
    raw = (settings.github_app_private_key or "").strip()
    if raw:
        return raw.replace("\\n", "\n")
    path = (settings.github_app_private_key_path or "").strip()
    if path:
        return Path(path).read_text(encoding="utf-8")
    raise GitHubAppAuthError(
        "Set GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH for GitHub App auth."
    )


def create_app_jwt() -> str:
    """Short-lived JWT signed with the GitHub App private key (RS256)."""
    app_id = (settings.github_app_id or "").strip()
    if not app_id:
        raise GitHubAppAuthError("GITHUB_APP_ID is required for GitHub App auth.")

    try:
        import jwt
    except ImportError as exc:  # pragma: no cover
        raise GitHubAppAuthError(
            "PyJWT is required for GitHub App auth. pip install PyJWT cryptography"
        ) from exc

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 9 * 60,
        "iss": app_id,
    }
    return jwt.encode(payload, _load_private_key(), algorithm="RS256")


def get_installation_token(installation_id: int | str) -> str:
    """
    Exchange App JWT for an installation access token.

    If App credentials are missing but GITHUB_TOKEN is set, return that token
    so local webhook tests can still fetch diffs / post comments.
    """
    has_app = bool(
        (settings.github_app_id or "").strip()
        and (
            (settings.github_app_private_key or "").strip()
            or (settings.github_app_private_key_path or "").strip()
        )
    )
    if not has_app:
        token = (settings.github_token or "").strip()
        if token:
            return token
        raise GitHubAppAuthError(
            "Configure GitHub App credentials or GITHUB_TOKEN to call the GitHub API."
        )

    jwt_token = create_app_jwt()
    url = f"{API}/app/installations/{installation_id}/access_tokens"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if response.status_code >= 400:
            raise GitHubAppAuthError(
                f"Installation token exchange failed ({response.status_code}): {response.text}"
            )
        token = response.json().get("token")
        if not token:
            raise GitHubAppAuthError("GitHub did not return an installation token.")
        return str(token)


def api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
