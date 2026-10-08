import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.content_copy import TargetNotEmptyError, copy_content, main
from app.models import Base, Profile, Project, SiteMeta, Skill


@pytest.fixture
def source(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Profile(id=1, full_name="Gavin Clarke", headline="Analyst", summary="Summary."),
                Project(id=1, title="One", slug="one", short_summary="First."),
                Project(id=3, title="Three", slug="three", short_summary="Third.", category="Finance"),
                Skill(id=1, name="Excel", category="Technical"),
                SiteMeta(id=1, key="availability", value="Open to roles."),
            ]
        )
        db.commit()
    yield engine
    engine.dispose()


def count(engine, model):
    with Session(engine) as db:
        return db.scalar(select(func.count()).select_from(model))


def test_copy_moves_every_row_with_ids_and_values(source, db_engine):
    counts = copy_content(source, db_engine)

    assert counts["profiles"] == 1 and counts["projects"] == 2 and counts["skills"] == 1
    assert counts["volunteer_work"] == 0
    with Session(db_engine) as db:
        three = db.get(Project, 3)
        assert three.slug == "three" and three.category == "Finance"
        assert db.get(SiteMeta, 1).value == "Open to roles."


def test_copy_refuses_non_empty_target_and_changes_nothing(source, db_engine):
    copy_content(source, db_engine)

    with pytest.raises(TargetNotEmptyError, match="profiles"):
        copy_content(source, db_engine)

    assert count(db_engine, Project) == 2
    assert count(db_engine, Profile) == 1


def test_new_rows_after_copy_get_fresh_ids(source, db_engine):
    copy_content(source, db_engine)

    with Session(db_engine) as db:
        db.add(Project(title="Four", slug="four", short_summary="Added later."))
        db.commit()
        assert db.scalar(select(Project.id).where(Project.slug == "four")) > 3


def test_cli_without_target_url_exits_2(source, monkeypatch, capsys):
    monkeypatch.delenv("TARGET_DATABASE_URL", raising=False)
    assert main([str(source.url)]) == 2
    assert "TARGET_DATABASE_URL" in capsys.readouterr().err


def test_cli_copies_and_prints_counts_without_the_url(source, db_engine, monkeypatch, capsys):
    monkeypatch.setenv("TARGET_DATABASE_URL", db_engine.url.render_as_string(hide_password=False))
    assert main([str(source.url)]) == 0
    output = capsys.readouterr().out
    assert "projects: 2" in output
    assert str(db_engine.url.password or "no-password") not in output
