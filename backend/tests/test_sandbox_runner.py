"""Docker/local sandbox runner selection and command construction."""

from app.services import sandbox_runner


def setup_function() -> None:
    sandbox_runner.reset_docker_probe_cache()


def test_local_backend_runs_pytest(monkeypatch):
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_backend", "local")
    errors = sandbox_runner.run_sandbox_tests(
        code='def login(user):\n    return "SELECT ?", (user,)\n',
        tests=(
            "from solution import login\n"
            "def test_ok():\n"
            "    q = login('alice')[0]\n"
            "    assert '?' in q\n"
            "    assert 'alice' not in q\n"
        ),
    )
    assert errors == []


def test_local_backend_reports_failures(monkeypatch):
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_backend", "local")
    errors = sandbox_runner.run_sandbox_tests(
        code='def login(user):\n    return "SELECT " + user\n',
        tests=(
            "from solution import login\n"
            "def test_ok():\n"
            "    assert '?' in login('alice')\n"
        ),
    )
    assert errors


def test_docker_required_when_daemon_down(monkeypatch):
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_backend", "docker")
    monkeypatch.setattr(sandbox_runner, "docker_available", lambda: False)
    errors = sandbox_runner.run_sandbox_tests(code="x=1", tests="def test_x():\n    assert x == 1\n")
    assert any("Docker daemon is unavailable" in line for line in errors)


def test_auto_uses_local_when_docker_unavailable(monkeypatch):
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_backend", "auto")
    monkeypatch.setattr(sandbox_runner, "docker_available", lambda: False)
    called = {"local": False}

    def fake_local(code: str, tests: str, timeout: int) -> list[str]:
        called["local"] = True
        return []

    monkeypatch.setattr(sandbox_runner, "_run_local", fake_local)
    monkeypatch.setattr(
        sandbox_runner,
        "_run_docker",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("docker should not run")),
    )
    assert sandbox_runner.run_sandbox_tests(code="x=1", tests="def test_x():\n assert True\n") == []
    assert called["local"] is True


def test_docker_run_command_uses_isolation_flags(monkeypatch):
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_backend", "docker")
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_image", "sandbox-test:latest")
    monkeypatch.setattr(sandbox_runner.settings, "sandbox_network_none", True)
    monkeypatch.setattr(sandbox_runner, "docker_available", lambda: True)
    monkeypatch.setattr(
        sandbox_runner.shutil,
        "which",
        lambda name: "docker" if name == "docker" else None,
    )
    monkeypatch.setattr(sandbox_runner, "_ensure_sandbox_image", lambda *a, **k: [])

    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(sandbox_runner.subprocess, "run", fake_run)
    errors = sandbox_runner.run_sandbox_tests(
        code="def f():\n    return 1\n",
        tests="from solution import f\ndef test_f():\n    assert f() == 1\n",
    )
    assert errors == []
    cmd = captured["cmd"]
    assert cmd[0] == "docker"
    assert "--network" in cmd and "none" in cmd
    assert "--memory" in cmd
    assert "--read-only" in cmd
    assert "sandbox-test:latest" in cmd
