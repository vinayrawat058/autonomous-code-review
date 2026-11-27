"""GitHub App Manifest helpers."""

from pathlib import Path

from app.services.github_app_manifest import (
    build_manifest,
    persist_manifest_credentials,
)


def test_build_manifest_sets_webhook_and_permissions():
    manifest = build_manifest(
        webhook_url="https://example.trycloudflare.com/api/github/webhook",
        redirect_url="http://127.0.0.1:8000/api/github/app-manifest/callback",
    )
    assert manifest["hook_attributes"]["url"].endswith("/api/github/webhook")
    assert "pull_request" in manifest["default_events"]
    assert manifest["default_permissions"]["pull_requests"] == "write"


def test_persist_manifest_credentials_writes_env_and_pem(tmp_path: Path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("APP_ENV=development\n", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.github_app_manifest.settings.github_app_id",
        "",
        raising=False,
    )
    saved = persist_manifest_credentials(
        {
            "id": 12345,
            "pem": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n",
            "webhook_secret": "whsec_test",
            "html_url": "https://github.com/apps/demo",
            "slug": "demo",
        },
        env_path=env_path,
    )
    assert saved["app_id"] == "12345"
    pem_path = Path(saved["pem_path"])
    assert pem_path.is_file()
    text = env_path.read_text(encoding="utf-8")
    assert "GITHUB_APP_ID=12345" in text
    assert "GITHUB_WEBHOOK_SECRET=whsec_test" in text
    assert "GITHUB_APP_PRIVATE_KEY_PATH=" in text
