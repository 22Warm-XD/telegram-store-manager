from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import argparse
from pathlib import Path


def run(command: list[str] | str, *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    shell = isinstance(command, str)
    print(f"[bootstrap] running: {command}")
    return subprocess.run(command, cwd=cwd, shell=shell, check=check, text=True)


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def ensure_linux() -> None:
    if platform.system().lower() != "linux":
        raise RuntimeError("bootstrap_stack.py is intended to run on a Linux server.")


def ensure_docker() -> None:
    if shutil.which("docker") and _docker_compose_available():
        return

    if shutil.which("apt-get") is None:
        raise RuntimeError("Docker is not installed and apt-get is unavailable. Install Docker manually.")

    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", "ca-certificates", "curl", "tar"])
    run("curl -fsSL https://get.docker.com | sh")
    run("systemctl enable docker --now || service docker start || true")

    if not shutil.which("docker") or not _docker_compose_available():
        raise RuntimeError("Docker installation finished, but `docker compose` is still unavailable.")


def _docker_compose_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def deploy(project_dir: Path, *, reset_data: bool = False) -> None:
    ensure_linux()
    require_file(project_dir / ".env", ".env")
    require_file(project_dir / "docker-compose.yml", "docker-compose.yml")
    ensure_docker()

    if reset_data:
        run(["docker", "compose", "down", "-v"], cwd=project_dir, check=False)

    run(["docker", "compose", "up", "-d", "--build"], cwd=project_dir)
    run(["docker", "compose", "ps"], cwd=project_dir)
    run(["docker", "compose", "logs", "--tail=50", "bot", "backend", "web"], cwd=project_dir, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Telegram Store Manager bot + Mini App stack on a Linux server.")
    parser.add_argument("project_dir", nargs="?", default=os.environ.get("STORE_MANAGER_PROJECT_DIR"))
    parser.add_argument("--reset-data", action="store_true", help="Recreate stack and drop Docker volumes for a clean DB/Redis state.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve() if args.project_dir else Path(__file__).resolve().parents[1]
    deploy(project_dir, reset_data=args.reset_data)


if __name__ == "__main__":
    main()
