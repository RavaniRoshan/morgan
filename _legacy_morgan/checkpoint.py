"""Morgan checkpoint module — git-based state rollback."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from morgan.config import Config

logger = logging.getLogger("morgan.checkpoint")

class CheckpointManager:
    """Manages workspace snapshots and rollbacks using git."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.workspace_dir = self.config.workspace_dir
        self._ensure_git_repo()

    def _ensure_git_repo(self) -> None:
        git_dir = self.workspace_dir / ".git"
        if not git_dir.exists():
            logger.info("Initializing git repository for checkpoints in %s", self.workspace_dir)
            self._run_git("init")
            
            # Create standard .gitignore
            gitignore = self.workspace_dir / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text(".morgan/\n.venv/\n__pycache__/\n", encoding="utf-8")
                
            self.create_checkpoint("Initial Morgan workspace")

    def _run_git(self, cmd: str) -> str:
        res = subprocess.run(
            f"git {cmd}",
            cwd=self.workspace_dir,
            shell=True,
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            logger.warning("Git command 'git %s' failed: %s", cmd, res.stderr.strip())
        return res.stdout.strip()

    def create_checkpoint(self, message: str) -> str:
        """Create a snapshot of the current workspace."""
        self._run_git("add -A")
        # Ensure there is something to commit
        status = self._run_git("status --porcelain")
        if not status:
            return "No changes to commit."
            
        self._run_git(f"commit -m '{message}'")
        rev = self._run_git("rev-parse --short HEAD")
        logger.info("Created checkpoint: %s", rev)
        return rev

    def rollback(self, commit_hash: str = "HEAD~1") -> str:
        """Rollback the workspace to a previous checkpoint."""
        # Use hard reset to wipe uncommitted changes and move HEAD
        self._run_git(f"reset --hard {commit_hash}")
        logger.info("Rolled back to checkpoint %s", commit_hash)
        return f"Rolled back to {commit_hash}"
