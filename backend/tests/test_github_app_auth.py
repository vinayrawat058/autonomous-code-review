"""GitHub App auth falls back to PAT when installation id is missing."""

from app.services import github_app_auth


def test_get_installation_token_falls_back_without_installation_id(monkeypatch):
    monkeypatch.setattr(github_app_auth.settings, "github_app_id", "123")
    monkeypatch.setattr(github_app_auth.settings, "github_app_private_key", "pem")
    monkeypatch.setattr(github_app_auth.settings, "github_app_private_key_path", "")
    monkeypatch.setattr(github_app_auth.settings, "github_token", "pat-token")
    assert github_app_auth.get_installation_token(0) == "pat-token"
    assert github_app_auth.get_installation_token("") == "pat-token"
