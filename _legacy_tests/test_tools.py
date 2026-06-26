"""Comprehensive tests for morgan tools — valid inputs and error cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from morgan.config import Config, TrustMode
from morgan.tools import (
    edit_file,
    get_time,
    hello,
    list_dir,
    plan,
    read_file,
    think,
    write_file,
)


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


class TestReadFile:
    """Tests for the read_file tool."""

    def test_read_existing_file(self, workspace: Config) -> None:
        """Read an existing file and verify its contents."""
        (workspace.workspace_dir / "sample.txt").write_text("line one\nline two\n")
        result = read_file("sample.txt", config=workspace)
        assert "line one" in result
        assert "line two" in result

    def test_read_with_limit(self, workspace: Config) -> None:
        """Read only the first N lines of a file."""
        content = "\n".join(f"line {i}" for i in range(10))
        (workspace.workspace_dir / "many_lines.txt").write_text(content)
        result = read_file("many_lines.txt", limit=3, config=workspace)
        assert "line 0" in result
        assert "line 2" in result
        assert "line 3" not in result

    def test_read_nonexistent_file(self, workspace: Config) -> None:
        """Reading a missing file returns an error string."""
        result = read_file("does_not_exist.txt", config=workspace)
        assert result.startswith("Error:")
        assert "file not found" in result

    def test_read_directory_path(self, workspace: Config) -> None:
        """Reading a directory path returns an error string."""
        subdir = workspace.workspace_dir / "subdir"
        subdir.mkdir()
        result = read_file("subdir", config=workspace)
        assert result.startswith("Error:")
        assert "directory" in result


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


class TestWriteFile:
    """Tests for the write_file tool."""

    def test_write_new_file(self, workspace: Config) -> None:
        """Write a new file and verify it exists on disk."""
        result = write_file("new.txt", "hello world", config=workspace)
        assert "wrote" in result
        assert "created" in result
        assert (workspace.workspace_dir / "new.txt").read_text() == "hello world"

    def test_write_nested_directory(self, workspace: Config) -> None:
        """Write to a nested path — parent directories should be created."""
        result = write_file("a/b/c/nested.txt", "deep content", config=workspace)
        assert "wrote" in result
        assert "created" in result
        assert (workspace.workspace_dir / "a/b/c/nested.txt").read_text() == "deep content"

    def test_write_overwrite_existing(self, workspace: Config) -> None:
        """Overwriting an existing file reports 'overwritten'."""
        (workspace.workspace_dir / "ow.txt").write_text("old")
        result = write_file("ow.txt", "new", config=workspace)
        assert "overwritten" in result
        assert (workspace.workspace_dir / "ow.txt").read_text() == "new"

    def test_write_blocked_in_safe_mode(self, workspace: Config) -> None:
        """Safe trust mode blocks writes entirely."""
        cfg_safe = Config(workspace_dir=workspace.workspace_dir, trust_mode=TrustMode.SAFE)
        result = write_file("blocked.txt", "content", config=cfg_safe)
        assert "Error:" in result
        assert "safe" in result.lower()
        assert not (workspace.workspace_dir / "blocked.txt").exists()


# ---------------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------------


class TestEditFile:
    """Tests for the edit_file tool."""

    def test_edit_success(self, workspace: Config) -> None:
        """Find-and-replace in an existing file."""
        (workspace.workspace_dir / "edit_me.txt").write_text("foo bar baz\n")
        result = edit_file("edit_me.txt", "bar", "qux", config=workspace)
        assert "edits applied" in result
        assert (workspace.workspace_dir / "edit_me.txt").read_text() == "foo qux baz\n"

    def test_edit_old_string_not_found(self, workspace: Config) -> None:
        """Editing with a missing old_string returns an error."""
        (workspace.workspace_dir / "stable.txt").write_text("no match here\n")
        result = edit_file("stable.txt", "MISSING", "replacement", config=workspace)
        assert result.startswith("Error:")
        assert "old_string not found" in result

    def test_edit_nonexistent_file(self, workspace: Config) -> None:
        """Editing a missing file returns an error."""
        result = edit_file("ghost.txt", "a", "b", config=workspace)
        assert result.startswith("Error:")
        assert "file not found" in result


# ---------------------------------------------------------------------------
# list_dir
# ---------------------------------------------------------------------------


class TestListDir:
    """Tests for the list_dir tool."""

    def test_list_directory(self, workspace: Config) -> None:
        """List a directory that contains files."""
        (workspace.workspace_dir / "alpha.txt").write_text("a")
        (workspace.workspace_dir / "beta.txt").write_text("b")
        result = list_dir(".", config=workspace)
        assert "alpha.txt" in result
        assert "beta.txt" in result

    def test_list_with_depth(self, workspace: Config) -> None:
        """Listing with depth > 0 shows nested entries."""
        sub = workspace.workspace_dir / "child"
        sub.mkdir()
        (sub / "inner.txt").write_text("x")
        result = list_dir(".", depth=1, config=workspace)
        assert "child" in result
        assert "inner.txt" in result

    def test_list_nonexistent_directory(self, workspace: Config) -> None:
        """Listing a missing directory returns an error."""
        result = list_dir("nope", config=workspace)
        assert result.startswith("Error:")
        assert "not found" in result

    def test_list_file_path(self, workspace: Config) -> None:
        """Listing a file path (not a dir) returns an error."""
        (workspace.workspace_dir / "afile.txt").write_text("x")
        result = list_dir("afile.txt", config=workspace)
        assert result.startswith("Error:")
        assert "file" in result.lower()


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


class TestPlan:
    """Tests for the plan tool."""

    def test_plan_with_goal(self, workspace: Config) -> None:
        """Plan returns a success message and creates PLAN.md."""
        result = plan("build a REST API", config=workspace)
        assert "Created PLAN.md" in result
        
        plan_content = (workspace.workspace_dir / "PLAN.md").read_text()
        assert "build a REST API" in plan_content

    def test_plan_with_constraints(self, workspace: Config) -> None:
        """Plan includes constraints when provided."""
        plan("deploy service", constraints={"lang": "python"}, config=workspace)
        plan_content = (workspace.workspace_dir / "PLAN.md").read_text()
        assert "python" in plan_content


# ---------------------------------------------------------------------------
# think
# ---------------------------------------------------------------------------


class TestThink:
    """Tests for the think tool."""

    def test_think_returns_acknowledgment(self, workspace: Config) -> None:
        """Think returns a confirmation string."""
        result = think("I need to refactor the module", config=workspace)
        assert "thought recorded" in result


# ---------------------------------------------------------------------------
# hello & get_time (no config needed)
# ---------------------------------------------------------------------------


class TestHello:
    """Tests for the hello tool."""

    def test_hello_returns_greeting(self) -> None:
        """Hello returns a greeting string."""
        result = hello()
        assert "hello" in result.lower()


class TestGetTime:
    """Tests for the get_time tool."""

    def test_get_time_returns_string(self) -> None:
        """get_time returns a non-empty time string with expected format."""
        result = get_time()
        assert isinstance(result, str)
        assert len(result) > 0
        # Expect format like "HH:MM:SS on YYYY-MM-DD"
        assert "on" in result
