"""
Local GitHub App Manifest registration UI + callback.

GET  /api/github/app-setup          — form that POSTs a manifest to GitHub
GET  /api/github/app-manifest/callback — exchanges ?code= for credentials
"""

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.services.github_app_manifest import (
    exchange_manifest_code,
    manifest_json,
    persist_manifest_credentials,
)

router = APIRouter()


def _public_base(request: Request, public_base: str | None) -> str:
    if public_base:
        return public_base.rstrip("/")
    # Prefer reverse-proxy headers when behind cloudflared / ngrok.
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        return f"{proto}://{host}".rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/app-setup", response_class=HTMLResponse)
async def app_setup_page(
    request: Request,
    public_base: str | None = Query(
        default=None,
        description="Public HTTPS origin (tunnel). Example: https://abc.trycloudflare.com",
    ),
):
    """One-click GitHub App Manifest registration for local / tunnel setups."""
    if settings.app_env != "development":
        raise HTTPException(status_code=404, detail="App setup UI is development-only.")

    base = _public_base(request, public_base)
    webhook_url = f"{base}/api/github/webhook"
    # Callback must be reachable by the browser after GitHub redirects (localhost is fine).
    redirect_url = "http://127.0.0.1:8000/api/github/app-manifest/callback"
    manifest = manifest_json(webhook_url=webhook_url, redirect_url=redirect_url)
    safe_manifest = html.escape(manifest)
    safe_webhook = html.escape(webhook_url)

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Register GitHub App — Agentic PR Review Studio</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
    code {{ background: #f4f4f5; padding: 0.1rem 0.35rem; border-radius: 4px; }}
    button {{ background: #238636; color: #fff; border: 0; padding: 0.65rem 1.1rem; border-radius: 6px; font-size: 1rem; cursor: pointer; }}
    .note {{ color: #52525b; font-size: 0.95rem; }}
  </style>
</head>
<body>
  <h1>Register GitHub App</h1>
  <p>This posts a <strong>GitHub App Manifest</strong> so GitHub creates the App with the right permissions and webhook URL.</p>
  <p>Webhook URL: <code>{safe_webhook}</code></p>
  <p class="note">After you click Create, GitHub redirects back to <code>127.0.0.1:8000</code>, which writes <code>backend/.env</code> and <code>backend/.secrets/github-app.pem</code> (never commit those).</p>
  <form action="https://github.com/settings/apps/new" method="post">
    <input type="hidden" name="manifest" value="{safe_manifest}" />
    <button type="submit">Create GitHub App</button>
  </form>
</body>
</html>"""
    return HTMLResponse(body)


@router.get("/app-manifest/callback", response_class=HTMLResponse)
async def app_manifest_callback(code: str | None = None):
    """Exchange the one-time manifest code and persist local credentials."""
    if settings.app_env != "development":
        raise HTTPException(status_code=404, detail="App setup callback is development-only.")
    if not code:
        raise HTTPException(status_code=400, detail="Missing manifest code query parameter.")

    try:
        payload = exchange_manifest_code(code)
        env_path = Path(__file__).resolve().parents[3] / ".env"
        saved = persist_manifest_credentials(payload, env_path=env_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    install_url = ""
    slug = saved.get("slug") or ""
    if slug:
        install_url = f"https://github.com/apps/{quote(slug)}/installations/new"

    html_url = html.escape(saved.get("html_url") or "")
    app_id = html.escape(saved.get("app_id") or "")
    pem_path = html.escape(saved.get("pem_path") or "")
    install_link = html.escape(install_url) if install_url else ""

    install_block = (
        f'<p><a href="{install_link}">Install the App on autonomous-code-review</a></p>'
        if install_url
        else "<p>Open the App page on GitHub and install it on this repository.</p>"
    )

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>GitHub App registered</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
    code {{ background: #f4f4f5; padding: 0.1rem 0.35rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>GitHub App registered</h1>
  <p>App id <code>{app_id}</code> saved. Private key: <code>{pem_path}</code>. Webhook secret written to <code>backend/.env</code>.</p>
  <p>App settings: <a href="{html_url}">{html_url}</a></p>
  {install_block}
  <p>Restart the API (or rely on <code>--reload</code>) so settings reload, then open a test PR.</p>
</body>
</html>"""
    return HTMLResponse(body)
