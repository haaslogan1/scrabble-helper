"""Alembic graph and upgrade-path guards (catch deploy #22 class failures in CI)."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app import models  # noqa: F401 — register metadata for create_all
from app.config import settings
from app.database import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"


def _script() -> ScriptDirectory:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(cfg)


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def test_alembic_single_head():
    heads = _script().get_heads()
    assert heads == ["010_game_ending_at"], f"expected single head 010, got {heads}"


def test_alembic_down_revisions_resolve():
    script = _script()
    for rev in script.walk_revisions():
        if rev.down_revision is None:
            continue
        downs = rev.down_revision if isinstance(rev.down_revision, tuple) else (rev.down_revision,)
        for down in downs:
            assert script.get_revision(down) is not None, (
                f"{rev.revision} down_revision {down!r} does not resolve"
            )


def test_alembic_version_files_have_no_bom():
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path.name} has a UTF-8 BOM"


def test_shipped_session_version_revision_still_present():
    script = _script()
    assert script.get_revision("009_user_session_version") is not None
    assert script.get_revision("010_game_ending_at") is not None


def test_upgrade_path_from_session_version_includes_ending_at():
    script = _script()
    ids = [r.revision for r in script.iterate_revisions("head", "009_user_session_version")]
    assert "010_game_ending_at" in ids, f"upgrade path missing 010: {ids}"


def test_upgrade_from_prior_stamp_succeeds(tmp_path, monkeypatch):
    """Simulate staging/prod stamped at 009_user_session_version after single-session ship."""
    db_path = tmp_path / "alembic_guard.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "database_url", url)

    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(64) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('009_user_session_version')")
        )

    cfg = _alembic_config()
    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        stamped = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert stamped == "010_game_ending_at"
    columns = {c["name"] for c in inspect(engine).get_columns("games")}
    assert "ending_at" in columns
    engine.dispose()
