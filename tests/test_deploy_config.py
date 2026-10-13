import json
import os
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


def test_deploy_commands_migrate_but_never_seed():
    deploy = json.loads((ROOT / "railway.json").read_text())["deploy"]
    commands = " ".join(deploy["preDeployCommand"] + [deploy["startCommand"]])
    assert "alembic upgrade head" in commands
    assert "seed" not in commands


def test_starting_and_serving_leaves_an_empty_database_empty(db_engine):
    client = TestClient(create_app())
    for path in ["/", "/resume", "/projects", "/contact", "/health"]:
        assert client.get(path).status_code == 200

    with Session(db_engine) as db:
        for table in Base.metadata.sorted_tables:
            assert db.scalar(select(func.count()).select_from(table)) == 0, table.name


def test_start_command_trusts_the_proxys_forwarded_proto():
    start = json.loads((ROOT / "railway.json").read_text())["deploy"]["startCommand"]
    assert '--forwarded-allow-ips="*"' in start


def _non_loopback_ip():
    # Railway's proxy reaches the app from a non-loopback address. Uvicorn trusts
    # 127.0.0.1 by default, so the test must connect from a real interface to be meaningful.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 80))  # TEST-NET-1: no packet is sent for UDP connect
            ip = probe.getsockname()[0]
        except OSError:
            return None
    return None if ip.startswith("127.") else ip


def test_app_behind_proxy_builds_https_urls(tmp_path):
    ip = _non_loopback_ip()
    if ip is None:
        pytest.skip("no non-loopback interface to simulate Railway's proxy")

    with socket.socket() as free:
        free.bind(("", 0))
        port = free.getsockname()[1]
    start = json.loads((ROOT / "railway.json").read_text())["deploy"]["startCommand"]
    env = {
        **os.environ,
        "PORT": str(port),
        "DATABASE_URL": f"sqlite:///{tmp_path / 'empty.db'}",
        "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
    }
    server = subprocess.Popen(start, shell=True, cwd=ROOT, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        base = f"http://{ip}:{port}"
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
        os.killpg(server.pid, 15)
        server.wait(timeout=10)
