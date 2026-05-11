from __future__ import annotations

import argparse
import getpass
import os
import posixpath
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def ensure_paramiko():
    try:
        import paramiko  # type: ignore
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko"])
        import paramiko  # type: ignore
    return paramiko


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy Telegram Store Manager to a remote Linux server via SSH.")
    parser.add_argument("--host", required=True, help="Server IP or hostname")
    parser.add_argument("--user", default="root", help="SSH username, default: root")
    parser.add_argument("--password", default=os.environ.get("STORE_MANAGER_SERVER_PASSWORD"), help="SSH password")
    parser.add_argument(
        "--remote-dir",
        default="/opt/telegram-store-manager",
        help="Remote deployment directory, default: /opt/telegram-store-manager",
    )
    parser.add_argument(
        "--project-dir",
        default=str(Path(__file__).resolve().parents[1]),
        help="Local project directory",
    )
    parser.add_argument(
        "--reset-data",
        action="store_true",
        help="Drop Docker volumes on the remote server before starting the stack.",
    )
    return parser.parse_args()


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    skip_names = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
    }
    if parts & skip_names:
        return True
    if path.name.endswith((".pyc", ".pyo", ".pyd", ".log")):
        return True
    return False


def build_archive(project_dir: Path) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="store-manager-deploy-"))
    archive_path = temp_dir / "bundle.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in project_dir.rglob("*"):
            if should_skip(path):
                continue
            archive.add(path, arcname=path.relative_to(project_dir))
    return archive_path


def remote_run(ssh, command: str) -> None:
    print(f"[deploy] remote command: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", errors="ignore")
    error = stderr.read().decode("utf-8", errors="ignore")
    if output.strip():
        sys.stdout.buffer.write(output.strip().encode("utf-8", errors="ignore") + b"\n")
        sys.stdout.flush()
    if error.strip():
        sys.stderr.buffer.write(error.strip().encode("utf-8", errors="ignore") + b"\n")
        sys.stderr.flush()
    if exit_code != 0:
        raise RuntimeError(f"Remote command failed with exit code {exit_code}: {command}")


def upload_archive(sftp, local_archive: Path, remote_archive: str) -> None:
    remote_dir = posixpath.dirname(remote_archive)
    mkdir_p(sftp, remote_dir)
    sftp.put(str(local_archive), remote_archive)


def mkdir_p(sftp, remote_directory: str) -> None:
    current = ""
    for part in remote_directory.strip("/").split("/"):
        current = f"{current}/{part}" if current else f"/{part}"
        try:
            sftp.stat(current)
        except OSError:
            sftp.mkdir(current)


def deploy() -> None:
    args = parse_args()
    password = (args.password or getpass.getpass("SSH password: ")).strip()
    project_dir = Path(args.project_dir).resolve()
    archive_path = build_archive(project_dir)
    paramiko = ensure_paramiko()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[deploy] connecting to {args.user}@{args.host}")
    try:
        ssh.connect(
            hostname=args.host,
            username=args.user,
            password=password,
            timeout=30,
            auth_timeout=30,
            banner_timeout=30,
            allow_agent=False,
            look_for_keys=False,
        )
    except paramiko.AuthenticationException as exc:
        raise RuntimeError(
            "SSH authentication failed. Verify username/password and try passing the password via "
            "STORE_MANAGER_SERVER_PASSWORD to avoid manual input mistakes."
        ) from exc
    sftp = ssh.open_sftp()

    remote_archive = posixpath.join(args.remote_dir, "bundle.tar.gz")
    upload_archive(sftp, archive_path, remote_archive)
    sftp.close()

    remote_run(ssh, f"mkdir -p {args.remote_dir}")
    remote_run(
        ssh,
        "command -v python3 >/dev/null 2>&1 || "
        "(command -v apt-get >/dev/null 2>&1 && apt-get update && apt-get install -y python3) || "
        "(echo 'python3 is required on the server' >&2; exit 1)",
    )
    remote_run(
        ssh,
        (
            f"cd {args.remote_dir} && "
            "rm -rf app alembic frontend scripts tests .env.example Dockerfile README.md pyproject.toml "
            "docker-compose.yml alembic.ini .dockerignore Caddyfile && "
            f"tar -xzf {remote_archive} -C {args.remote_dir} && "
            f"python3 {posixpath.join(args.remote_dir, 'scripts/bootstrap_stack.py')} "
            f"{'--reset-data ' if args.reset_data else ''}{args.remote_dir}"
        ),
    )

    print(f"[deploy] deployment completed in {args.remote_dir}")
    ssh.close()


if __name__ == "__main__":
    deploy()
