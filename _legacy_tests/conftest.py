"""Pytest fixtures for morgan tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from morgan.config import Config


@pytest.fixture
def workspace() -> Config:
    """Create a temporary directory as the workspace."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Config(workspace_dir=Path(tmpdir))
