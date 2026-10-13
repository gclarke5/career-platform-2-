"""Copy every content table from one database into an empty, migrated one.

Used once to move the SQLite content into Railway Postgres:

    TARGET_DATABASE_URL=... python -m app.content_copy sqlite:///./career_platform.db

The target URL comes from an environment variable so its password never lands in
shell history or output.
"""

import argparse
import os
import sys

from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.engine import Engine

from app.config import normalize_database_url
from app.db import engine_options
from app.models import Base


class TargetNotEmptyError(RuntimeError):
    """Raised when the target already holds content, so a copy would duplicate it."""


def copy_content(source: Engine, target: Engine) -> dict[str, int]:
    tables = Base.metadata.sorted_tables

    with target.connect() as connection:
        occupied = [t.name for t in tables if connection.scalar(select(func.count()).select_from(t))]
    if occupied:
        raise TargetNotEmptyError(f"Target already has rows in: {', '.join(occupied)}")

    counts: dict[str, int] = {}
    with source.connect() as reader, target.begin() as writer:
        for table in tables:
            rows = [dict(row._mapping) for row in reader.execute(select(table))]
            if rows:
                writer.execute(insert(table), rows)
            counts[table.name] = len(rows)
            if target.dialect.name == "postgresql":
                # Explicit ids don't advance Postgres sequences; move each past the copied max.
                writer.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"
                    )
                )

    with target.connect() as connection:
        for table in tables:
            copied = connection.scalar(select(func.count()).select_from(table))
            if copied != counts[table.name]:
                raise RuntimeError(f"{table.name}: expected {counts[table.name]} rows, found {copied}")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy content into an empty, migrated database.")
    parser.add_argument("source_url", help="e.g. sqlite:///./career_platform.db")
    parser.add_argument("--target-env", default="TARGET_DATABASE_URL", help="env var holding the target URL")
    args = parser.parse_args(argv)

    target_url = os.environ.get(args.target_env)
    if not target_url:
        print(f"Set {args.target_env} to the target database URL.", file=sys.stderr)
        return 2

    target_url = normalize_database_url(target_url)
    source = create_engine(args.source_url)
    target = create_engine(target_url, **engine_options(target_url))
    try:
        counts = copy_content(source, target)
    except TargetNotEmptyError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        source.dispose()
        target.dispose()

    for name, copied in counts.items():
        print(f"{name}: {copied}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
