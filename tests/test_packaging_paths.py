"""Relative storage paths must follow the working directory (or NEXUS_ROOT), never the installed package location.

Regression for 0.2.0: `_REPO_ROOT = Path(__file__).parents[2]` resolved to `site-packages` for a wheel install, so
`data/db/*.db` from a .env file were written inside the Python environment.
"""

import os
import subprocess
import sys
from pathlib import Path

import nexus_engine

_CODE = (
    "from nexus_engine.core.config import Settings\n"
    "s = Settings(database_path='data/db/x.db', audit_db_path='data/db/a.db')\n"
    "print(s.database_path)\n"
    "print(s.audit_db_path)\n"
)


def _run(cwd: Path, extra_env: dict[str, str]) -> list[Path]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("NEXUS_ROOT", "DEFAULT_DATABASE_PATH", "DEFAULT_AUDIT_DB_PATH")
    }
    # The child process has no pytest pythonpath: point it at the checkout that is under test.
    env["PYTHONPATH"] = str(Path(nexus_engine.__file__).resolve().parents[1])
    env.update(extra_env)
    out = subprocess.run(
        [sys.executable, "-c", _CODE], cwd=cwd, env=env, capture_output=True, text=True, check=True
    ).stdout.split()
    return [Path(line) for line in out]


def test_relative_paths_resolve_against_working_dir(tmp_path: Path) -> None:
    db, audit = _run(tmp_path, {})
    root = tmp_path.resolve()
    assert db == root / "data" / "db" / "x.db"
    assert audit == root / "data" / "db" / "a.db"
    assert "site-packages" not in str(db)


def test_nexus_root_overrides_working_dir(tmp_path: Path) -> None:
    anchor = (tmp_path / "anchor").resolve()
    anchor.mkdir()
    db, _ = _run(tmp_path, {"NEXUS_ROOT": str(anchor)})
    assert db == anchor / "data" / "db" / "x.db"
