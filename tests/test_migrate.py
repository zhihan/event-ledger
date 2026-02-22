"""Tests for the migration script."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from memory import Memory

# Import the script module directly
import importlib.util
import sys

_script_path = Path(__file__).resolve().parent.parent / "scripts" / "migrate_to_firestore.py"
_spec = importlib.util.spec_from_file_location("migrate_to_firestore", _script_path)
migrate_mod = importlib.util.module_from_spec(_spec)
sys.modules["migrate_to_firestore"] = migrate_mod
_spec.loader.exec_module(migrate_mod)


def _write_memory(path: Path, **kwargs) -> None:
    defaults = dict(
        target=date(2026, 3, 15),
        expires=date(2026, 4, 15),
        content="Event.",
        user_id="cambridge-lexington",
    )
    defaults.update(kwargs)
    Memory(**defaults).dump(path)


@patch("firestore_storage.save_memory", return_value="doc-123")
def test_migrate_imports_files(mock_save, tmp_path: Path):
    _write_memory(tmp_path / "a.md", title="Event A")
    _write_memory(tmp_path / "b.md", title="Event B")

    count = migrate_mod.migrate(tmp_path)

    assert count == 2
    assert mock_save.call_count == 2


def test_migrate_dry_run(tmp_path: Path):
    _write_memory(tmp_path / "a.md", title="Event A")

    count = migrate_mod.migrate(tmp_path, dry_run=True)

    assert count == 1


def test_migrate_empty_dir(tmp_path: Path):
    count = migrate_mod.migrate(tmp_path)
    assert count == 0
