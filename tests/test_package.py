"""Guards on the package surface and on the version we advertise."""

from __future__ import annotations

import re
from pathlib import Path

import backoffkit

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_version_matches_pyproject() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    declared = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert declared is not None, "pyproject.toml has no version"
    assert declared.group(1) == backoffkit.__version__


def test_every_exported_name_exists() -> None:
    missing = [name for name in backoffkit.__all__ if not hasattr(backoffkit, name)]
    assert missing == []


def test_all_is_sorted_and_unique() -> None:
    names = list(backoffkit.__all__)
    assert names == sorted(names)
    assert len(names) == len(set(names))
