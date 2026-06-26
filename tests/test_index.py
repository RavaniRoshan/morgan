"""Tests for the RepoIndex module."""

from pathlib import Path
from morgan.config import Config
from morgan.index import RepoIndex

def test_repo_map(workspace: Config) -> None:
    # Create some dummy files
    f1 = workspace.workspace_dir / "a.py"
    f1.write_text("hello")
    d1 = workspace.workspace_dir / "src"
    d1.mkdir()
    f2 = d1 / "b.py"
    f2.write_text("world")
    
    index = RepoIndex(config=workspace)
    repo_map = index.get_repo_map()
    
    assert "a.py" in repo_map
    assert "src/" in repo_map
    assert "b.py" in repo_map

def test_differential_context(workspace: Config) -> None:
    index = RepoIndex(config=workspace)
    
    f1 = workspace.workspace_dir / "file.txt"
    f1.write_text("v1")
    
    # First check: Added
    diff1 = index.get_differential_context()
    assert "[Added] file.txt" in diff1
    
    # Second check: No change
    diff2 = index.get_differential_context()
    assert "No files changed" in diff2
    
    # Modify file
    f1.write_text("v2")
    diff3 = index.get_differential_context()
    assert "[Modified] file.txt" in diff3
    
    # Delete file
    f1.unlink()
    diff4 = index.get_differential_context()
    assert "[Deleted] file.txt" in diff4
