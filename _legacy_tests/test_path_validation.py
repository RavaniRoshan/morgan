"""Path validation tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from morgan.config import Config
from morgan.tools import read_file, write_file, edit_file, list_dir, bash


@pytest.fixture
def workspace() -> Config:
    """Create a temporary directory as the workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Config(workspace_dir=Path(tmpdir))


def test_read_file_traversal_attempt(workspace: Config) -> None:
    """Test that path traversal attempts are blocked in read_file."""
    # Test cases that should raise ValueError
    traversal_paths = [
        "../../../etc/passwd",
        "../outside_file.txt",
        "subdir/../../../etc/passwd",
    ]

    for path in traversal_paths:
        with pytest.raises(ValueError, match="escapes workspace directory"):
            read_file(path, config=workspace)


def test_write_file_traversal_attempt(workspace: Config) -> None:
    """Test that path traversal attempts are blocked in write_file."""
    traversal_paths = [
        "../../../etc/passwd",
        "../outside_file.txt",
        "subdir/../../../etc/passwd",
    ]

    for path in traversal_paths:
        with pytest.raises(ValueError, match="escapes workspace directory"):
            write_file(path, "malicious content", config=workspace)


def test_edit_file_traversal_attempt(workspace: Config) -> None:
    """Test that path traversal attempts are blocked in edit_file."""
    traversal_paths = [
        "../../../etc/passwd",
        "../outside_file.txt",
        "subdir/../../../etc/passwd",
    ]

    for path in traversal_paths:
        with pytest.raises(ValueError, match="escapes workspace directory"):
            edit_file(path, "old", "new", config=workspace)


def test_list_dir_traversal_attempt(workspace: Config) -> None:
    """Test that path traversal attempts are blocked in list_dir."""
    traversal_paths = [
        "../../../etc",
        "../outside_dir",
        "subdir/../../../etc",
    ]

    for path in traversal_paths:
        with pytest.raises(ValueError, match="escapes workspace directory"):
            list_dir(path, config=workspace)


def test_bash_traversal_attempt(workspace: Config) -> None:
    """Test that path traversal attempts are blocked in bash."""
    traversal_paths = [
        "../../../etc",
        "../outside_dir",
        "subdir/../../../etc",
    ]

    for path in traversal_paths:
        with pytest.raises(ValueError, match="escapes workspace directory"):
            bash("echo test", cwd=path, config=workspace)


def test_symlink_traversal_attempt(workspace: Config) -> None:
    """Test that symlinks pointing outside workspace are blocked."""
    # Create a directory outside the workspace
    target_dir = Path("/tmp") / "outside"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Create a symlink inside the workspace pointing outside
    link_path = workspace.workspace_dir / "link_to_outside"
    link_path.symlink_to(target_dir)

    # Attempts to access the symlink should be blocked
    traversal_paths = [
        "link_to_outside",
        "./link_to_outside",
    ]

    for path in traversal_paths:
        with pytest.raises(ValueError, match="escapes workspace directory"):
            read_file(path, config=workspace)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])