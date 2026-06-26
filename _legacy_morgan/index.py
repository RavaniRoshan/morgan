"""Morgan index module — repository mapping and differential context."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Dict, List, Tuple

from morgan.config import Config

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".morgan", "node_modules"}

class RepoIndex:
    """Maintains a map of the repository and tracks file changes for differential context."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.workspace_dir = self.config.workspace_dir
        self._file_hashes: Dict[str, str] = {}

    def get_repo_map(self) -> str:
        """Return a simple tree-like string of the workspace files."""
        lines = ["# Repository Map", ""]
        
        def _walk(directory: Path, prefix: str = "") -> None:
            try:
                entries = sorted(directory.iterdir(), key=lambda e: (e.is_file(), e.name))
            except PermissionError:
                return
                
            for i, entry in enumerate(entries):
                if entry.name in IGNORE_DIRS or entry.name.startswith("."):
                    continue
                    
                is_last = (i == len(entries) - 1)
                connector = "└── " if is_last else "├── "
                
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    _walk(entry, prefix + ("    " if is_last else "│   "))
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
                    
        _walk(self.workspace_dir)
        return "\n".join(lines)

    def _hash_file(self, path: Path) -> str | None:
        """Compute MD5 hash of a file's content."""
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception:
            return None

    def get_differential_context(self) -> str:
        """Identify files that changed since this was last called."""
        current_hashes = {}
        changes: List[Tuple[str, str]] = []  # (status, path)
        
        for root, dirs, files in os.walk(self.workspace_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            
            for file in files:
                if file.startswith("."):
                    continue
                    
                path = Path(root) / file
                rel_path = str(path.relative_to(self.workspace_dir))
                
                file_hash = self._hash_file(path)
                if file_hash:
                    current_hashes[rel_path] = file_hash
                    
                    old_hash = self._file_hashes.get(rel_path)
                    if old_hash is None:
                        changes.append(("Added", rel_path))
                    elif old_hash != file_hash:
                        changes.append(("Modified", rel_path))

        # Check for deleted files
        for rel_path in self._file_hashes:
            if rel_path not in current_hashes:
                changes.append(("Deleted", rel_path))
                
        self._file_hashes = current_hashes
        
        if not changes:
            return "No files changed in the workspace."
            
        summary = ["# Workspace Changes since last check:"]
        for status, path in sorted(changes):
            summary.append(f"- [{status}] {path}")
            
        return "\n".join(summary)
