"""Tests for the memory module."""

from pathlib import Path
import pytest
from morgan.config import Config
from morgan.memory import Memory

def test_memory_init(workspace: Config) -> None:
    """Test that Memory.init creates default files."""
    mem = Memory(config=workspace)
    mem.init()
    
    plan_path = workspace.workspace_dir / "PLAN.md"
    notes_path = workspace.workspace_dir / "NOTES.md"
    
    assert plan_path.exists()
    assert notes_path.exists()
    
    plan_content = plan_path.read_text()
    assert "status: pending" in plan_content

def test_memory_read_write(workspace: Config) -> None:
    """Test that Memory can read and write files."""
    mem = Memory(config=workspace)
    mem.write("TEST.md", "hello world")
    
    content = mem.read("TEST.md")
    assert content == "hello world"
    
def test_memory_read_not_found(workspace: Config) -> None:
    """Test reading a non-existent file returns an error string."""
    mem = Memory(config=workspace)
    content = mem.read("MISSING.md")
    assert content.startswith("Error:")

def test_memory_get_frontmatter(workspace: Config) -> None:
    """Test frontmatter parsing."""
    mem = Memory(config=workspace)
    mem.write("FRONT.md", "---\nkey1: val1\nkey2: val2\n---\nbody")
    
    front = mem.get_frontmatter("FRONT.md")
    assert front == {"key1": "val1", "key2": "val2"}
    
def test_memory_get_frontmatter_empty(workspace: Config) -> None:
    """Test frontmatter parsing on file without frontmatter."""
    mem = Memory(config=workspace)
    mem.write("NOFRONT.md", "# Heading\nbody")
    
    front = mem.get_frontmatter("NOFRONT.md")
    assert front == {}
