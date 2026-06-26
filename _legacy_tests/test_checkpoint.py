"""Tests for the CheckpointManager."""

from morgan.config import Config
from morgan.checkpoint import CheckpointManager

def test_checkpoint_manager(workspace: Config) -> None:
    cm = CheckpointManager(config=workspace)
    
    # Write a test file
    test_file = workspace.workspace_dir / "test.txt"
    test_file.write_text("v1")
    
    # Create checkpoint
    cm.create_checkpoint("Added test.txt")
    
    # Modify file
    test_file.write_text("v2")
    
    # Rollback
    cm.rollback("HEAD")
    
    # Assert
    assert test_file.read_text() == "v1"
