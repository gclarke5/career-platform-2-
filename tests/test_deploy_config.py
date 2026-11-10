import os
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import create_app
from app.models import Base

ROOT = Path(__file__).resolve().parents[1]


def test_starting_and_serving_leaves_an_empty_database_empty(db_engine):
    client = TestClient(create_app())
    for path in ["/", "/resume", "/projects", "/contact", "/health"]:
        assert client.get(path).status_code == 200

    with Session(db_engine) as db:
        for table in Base.metadata.sorted_tables:
            assert db.scalar(select(func.count()).select_from(table)) == 0, table.name


def _service_exec_start():
    unit = (ROOT / "deploy" / "career-platform.service").read_text()
    return next(line for line in unit.splitlines() if line.startswith("ExecStart=")).removeprefix("ExecStart=")


def test_app_behind_nginx_builds_https_urls(tmp_path):
    # Start uvicorn with the production systemd command (on a free port) and send what nginx
    # sends from 127.0.0.1: X-Forwarded-Proto: https must turn into https:// redirects and links.
    with socket.socket() as free:
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
    args = shlex.split(_service_exec_start())
    assert args[0].endswith("/uvicorn")
    args = [sys.executable, "-m", "uvicorn", *args[1:]]
    args[args.index("--port") + 1] = str(port)
    args[args.index("--workers") + 1] = "1"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'empty.db'}",
        "ENVIRONMENT": "development",
    }
    server = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                httpx.get(f"{base}/health", timeout=0.5)
                break
            except httpx.TransportError:
                time.sleep(0.1)
        headers = {"X-Forwarded-Proto": "https"}

        redirect = httpx.get(f"{base}/projects/", headers=headers, follow_redirects=False)
        assert redirect.status_code == 307
        assert redirect.headers["location"].startswith("https://")

        page = httpx.get(f"{base}/", headers=headers).text
        assert 'rel="stylesheet" href="http://' not in page
    finally:
        server.terminate()
        server.wait(timeout=10)


def test_aws_deploy_script_migrates_but_never_seeds():
    script = (ROOT / "deploy" / "deploy.sh").read_text()
    assert "alembic upgrade head" in script
    assert "seed" not in script.lower().replace("never seeds", "")
    assert "set -euo pipefail" in script


def test_aws_service_listens_on_localhost_only_and_trusts_only_nginx():
    unit = (ROOT / "deploy" / "career-platform.service").read_text()
    exec_start = next(line for line in unit.splitlines() if line.startswith("ExecStart="))
    assert "--host 127.0.0.1" in exec_start
    assert "--forwarded-allow-ips=127.0.0.1" in exec_start
    assert "*" not in exec_start
    assert "EnvironmentFile=/etc/career-platform.env" in unit


def test_aws_nginx_blocks_admin_and_hides_the_test_hostname():
    conf = (ROOT / "deploy" / "nginx-career-platform.conf").read_text()
    assert "location ^~ /admin" in conf
    assert "return 444" in conf
    assert 'aws.gavinclarke.me "noindex, nofollow"' in conf
