"""
Run rewrite tests in Docker (isolated) or locally (fallback).

SANDBOX_BACKEND:
  auto   — Docker when the daemon is up, else local subprocess (default)
  docker — require Docker; surface an error if unavailable
  local  — always use the host Python (tests / no Docker Desktop)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from app.core.config import settings

_DOCKER_PROBE: bool | None = None


def docker_available() -> bool:
    """True when the Docker CLI can talk to a running daemon."""
    global _DOCKER_PROBE
    if _DOCKER_PROBE is not None:
        return _DOCKER_PROBE
    docker = shutil.which("docker")
    if not docker:
        _DOCKER_PROBE = False
        return False
    try:
        completed = subprocess.run(
            [docker, "info"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        _DOCKER_PROBE = completed.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        _DOCKER_PROBE = False
    return _DOCKER_PROBE


def reset_docker_probe_cache() -> None:
    """Clear the cached docker_available() result (tests)."""
    global _DOCKER_PROBE
    _DOCKER_PROBE = None


def _resolve_backend() -> str:
    raw = (settings.sandbox_backend or "auto").strip().lower()
    if raw not in {"auto", "docker", "local"}:
        return "auto"
    if raw == "auto":
        return "docker" if docker_available() else "local"
    return raw


def _write_workspace(code: str, tests: str) -> tempfile.TemporaryDirectory[str]:
    folder = tempfile.TemporaryDirectory(prefix="review-sandbox-")
    root = Path(folder.name)
    (root / "solution.py").write_text(code + "\n", encoding="utf-8")
    (root / "test_solution.py").write_text(tests + "\n", encoding="utf-8")
    return folder


def _errors_from_output(returncode: int, stdout: str, stderr: str) -> list[str]:
    if returncode == 0:
        return []
    output = f"{stdout}\n{stderr}".strip()
    lines = [line for line in output.splitlines() if line.strip()]
    return lines[-20:] or ["Tests failed with no output."]


def _run_local(code: str, tests: str, timeout: int) -> list[str]:
    with _write_workspace(code, tests) as folder:
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "test_solution.py", "-q", "--tb=line"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return [f"Tests timed out after {timeout} seconds."]
        return _errors_from_output(completed.returncode, completed.stdout, completed.stderr)


def _ensure_sandbox_image(docker: str, image: str, timeout: int) -> list[str]:
    """Return error lines if the image cannot be used; empty list means ready."""
    inspect = subprocess.run(
        [docker, "image", "inspect", image],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if inspect.returncode == 0:
        return []

    dockerfile = Path(__file__).resolve().parents[2] / "sandbox" / "Dockerfile"
    if not dockerfile.is_file():
        return [f"Sandbox image {image!r} not found and Dockerfile is missing."]

    build = subprocess.run(
        [docker, "build", "-t", image, str(dockerfile.parent)],
        capture_output=True,
        text=True,
        timeout=max(timeout, 300),
        check=False,
    )
    if build.returncode != 0:
        detail = (build.stderr or build.stdout or "").strip().splitlines()[-5:]
        return [f"Failed to build sandbox image {image!r}.", *detail]
    return []


def _run_docker(code: str, tests: str, timeout: int) -> list[str]:
    docker = shutil.which("docker")
    if not docker:
        return ["Docker CLI not found. Install Docker Desktop or set SANDBOX_BACKEND=local."]

    image = (settings.sandbox_image or "autonomous-code-review-sandbox:latest").strip()
    ensure_errors = _ensure_sandbox_image(docker, image, timeout)
    if ensure_errors:
        return ensure_errors

    mem = (settings.sandbox_memory or "256m").strip()
    cpus = (settings.sandbox_cpus or "1").strip()
    network = "none" if settings.sandbox_network_none else "bridge"

    with _write_workspace(code, tests) as folder:
        work = str(Path(folder).resolve())
        cmd = [
            docker,
            "run",
            "--rm",
            "--network",
            network,
            "--memory",
            mem,
            "--cpus",
            cpus,
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "HOME=/tmp",
            "-e",
            "PYTHONPYCACHEPREFIX=/tmp/pycache",
            "-v",
            f"{work}:/work:ro",
            "-w",
            "/work",
            image,
            "test_solution.py",
            "-q",
            "--tb=line",
            "-p",
            "no:cacheprovider",
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 15,
            )
        except subprocess.TimeoutExpired:
            return [f"Docker sandbox timed out after {timeout} seconds."]
        return _errors_from_output(completed.returncode, completed.stdout, completed.stderr)


def run_sandbox_tests(*, code: str, tests: str) -> list[str]:
    """
    Execute pytest against rewritten code. Returns test_errors (empty = pass).
    """
    timeout = max(5, int(settings.sandbox_timeout_seconds or 30))
    requested = (settings.sandbox_backend or "auto").strip().lower()
    backend = _resolve_backend()
    if backend == "docker":
        if requested == "docker" and not docker_available():
            return [
                "SANDBOX_BACKEND=docker but the Docker daemon is unavailable. "
                "Start Docker Desktop or set SANDBOX_BACKEND=local|auto."
            ]
        return _run_docker(code, tests, timeout)
    return _run_local(code, tests, timeout)
