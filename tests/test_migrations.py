import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrades_the_database_named_by_database_url(tmp_path):
    target = tmp_path / "migrated.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{target}"}

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    engine = create_engine(f"sqlite:///{target}")
    assert {"profiles", "projects", "site_meta", "volunteer_work"} <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "d4a8f1c2e7b9"
