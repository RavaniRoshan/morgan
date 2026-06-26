"""Morgan tools module — native tool definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel, Field

from morgan.config import Config, TrustMode, audit_log


class ReadFileInput(BaseModel):
    path: str = Field(description="Path to the file, relative to the workspace directory")
    limit: Optional[int] = Field(default=None, description="Maximum number of lines to read")


class WriteFileInput(BaseModel):
    path: str = Field(description="Path to the file, relative to the workspace directory")
    content: str = Field(description="Text content to write to the file")


class EditFileInput(BaseModel):
    path: str = Field(description="Path to the file, relative to the workspace directory")
    old_string: str = Field(description="Exact text to find and replace")
    new_string: str = Field(description="New text to insert")


class BashInput(BaseModel):
    command: str = Field(description="Shell command to execute")
    timeout: Optional[int] = Field(default=30, description="Command timeout in seconds")
    cwd: Optional[str] = Field(default=".", description="Working directory relative to workspace root")


class ListDirInput(BaseModel):
    path: str = Field(description="Directory path to list, relative to workspace")
    depth: Optional[int] = Field(default=1, description="Recursion depth; 0 means no subdirectories, 1 includes immediate children, etc.")


class PlanInput(BaseModel):
    goal: str = Field(description="Goal description for planning")
    constraints: Optional[dict[str, str]] = Field(default=None, description="Planning constraints")


class ThinkInput(BaseModel):
    reasoning: str = Field(description="Internal reasoning to record")

class BashBackgroundInput(BaseModel):
    command: str = Field(description="Shell command to execute in the background")
    cwd: Optional[str] = Field(default=".", description="Working directory relative to workspace root")

class BashOutputInput(BaseModel):
    pid: int = Field(description="The PID of the background task")

class KillShellInput(BaseModel):
    pid: int = Field(description="The PID of the background task to terminate")


class ToolRegistry:
    """Registry of callable tools available to the agent loop."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., str]] = {}

    def register(self, name: str, fn: Callable[..., str]) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., str] | None:
        return self._tools.get(name)


def resolve_and_validate(path: str, cwd: Path) -> Path:
    """Resolve *path* relative to *cwd* and ensure it stays inside."""
    resolved = (cwd / path).resolve()
    cwd_resolved = cwd.resolve()
    if not str(resolved).startswith(str(cwd_resolved)):
        msg = f"Path '{path}' escapes workspace directory '{cwd}'"
        raise ValueError(msg)
    return resolved


import hashlib

def _handle_large_output(text: str, cfg: Config) -> str:
    """Handle large tool outputs by saving them to a file if they exceed 8KB."""
    size = len(text.encode("utf-8"))
    if size <= 8192:
        return text
        
    outputs_dir = cfg.workspace_dir / ".morgan" / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # Hash content for stable filename
    content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    out_file = outputs_dir / f"output_{content_hash}.txt"
    out_file.write_text(text, encoding="utf-8")
    
    return f"Output too large ({size} bytes). Saved to: {out_file.relative_to(cfg.workspace_dir)}"


def read_file(path: str, limit: int | None = None, *, config: Config | None = None) -> str:
    """Read a file inside the workspace and return its contents as a string.

    *path* is resolved relative to ``config.workspace_dir``.  If the resolved
    path escapes the workspace, a :class:`ValueError` is raised.  Binary files
    are detected and reported gracefully instead of raising.
    """
    cfg = config or Config()
    resolved = resolve_and_validate(path, cfg.workspace_dir)

    if not resolved.exists():
        return f"Error: file not found: {path}"

    if resolved.is_dir():
        return f"Error: path is a directory, not a file: {path}"

    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: binary file, cannot display: {path}"

    if limit is not None:
        lines = text.splitlines(keepends=True)
        text = "".join(lines[:limit])

    return _handle_large_output(text, cfg)


def write_file(path: str, content: str, *, config: Config | None = None) -> str:
    """Write *content* to a file inside the workspace.

    Validates that the resolved path stays within ``config.workspace_dir``,
    creates parent directories as needed, and respects the current trust mode:
    in **safe** mode the write is blocked (returns an error); in **default**
    and **full_access** modes the write proceeds and is recorded in the audit log.

    Returns a human-readable summary including path, byte size, and whether
    the file was created or overwritten.
    """
    cfg = config or Config()
    resolved = resolve_and_validate(path, cfg.workspace_dir)

    if cfg.trust_mode == TrustMode.SAFE:
        msg = f"Error: write blocked by safe trust mode: {path}"
        audit_log("write_blocked", {"path": path, "trust_mode": "safe"})
        return msg

    created = not resolved.exists()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    size = len(content.encode("utf-8"))
    status = "created" if created else "overwritten"
    summary = f"wrote {path} ({size} bytes, {status})"

    audit_log("write_file", {"path": path, "size": size, "status": status})
    return summary


def edit_file(path: str, old_string: str, new_string: str, *, config: Config | None = None) -> str:
    """Edit a file inside the workspace by finding and replacing *old_string*.

    Validates that the resolved path stays within ``config.workspace_dir``.
    Reads the file, locates the first occurrence of ``old_string``, and replaces
    it with ``new_string``. Returns a summary including number of replacements
    performed and lines affected. If ``old_string`` is not found, returns an
    error message. Binary files and directory paths are rejected.
    """
    cfg = config or Config()
    resolved = resolve_and_validate(path, cfg.workspace_dir)

    if not resolved.exists():
        return f"Error: file not found: {path}"

    if resolved.is_dir():
        return f"Error: path is a directory, not a file: {path}"

    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: binary file, cannot display: {path}"

    if old_string not in text:
        return f"Error: old_string not found in {path}"

    new_text = text.replace(old_string, new_string, 1)
    resolved.write_text(new_text, encoding="utf-8")

    lines = text.splitlines()
    old_line_start = text.count('\n', 0, text.index(old_string))
    old_line_end = old_line_start + old_string.count('\n')
    line_summary = f"lines {old_line_start + 1}-{old_line_end + 1}"
    return f"edits applied: 1, {line_summary}, path={path}"


def bash(command: str, timeout: int | None = None, cwd: str = ".", *, config: Config | None = None) -> str:
    """Execute a shell command inside the workspace.

    Validates that *command* is safe and *cwd* is inside the workspace.
    Respects trust modes:
    * In **safe** mode: blocks all bash execution and returns an error.
    * In **default** mode: allows safe patterns, blocks destructive ones.
    * In **full_access** mode: allows any command, logs all actions.

    Returns command output, exit code, and timeout status.
    """
    cfg = config or Config()

    if cfg.trust_mode == TrustMode.SAFE:
        msg = f"Error: bash command blocked by safe trust mode"
        audit_log("bash_blocked", {"trust_mode": "safe"})
        return msg

    # Validate cwd is inside workspace
    cwd_resolved = resolve_and_validate(cwd, cfg.workspace_dir)

    # Destructive command detection in default mode
    destructive_patterns = [
        ("rm", "-rf", "/"),
        ("rm", "-rf", "*"),
        ("curl", "|"),
        ("wget", "|"),
        ("bash", "<(curl"),
        ("python", "-c", "__import__('os').system"),
        ("sh", "c", "rm -rf"),
    ]

    lower_command = command.lower()
    is_destructive = any(
        all(pattern.lower() in lower_command for pattern in patterns)
        for patterns in destructive_patterns
    )

    if is_destructive and cfg.trust_mode == TrustMode.DEFAULT:
        msg = f"Error: destructive command blocked by default trust mode: {command}"
        audit_log("bash_blocked_destructive", {"command": command})
        return msg

    audit_log("bash_executed", {"command": command, "cwd": cwd, "trust_mode": cfg.trust_mode})

    import subprocess

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd_resolved),
            capture_output=True,
            text=True,
            timeout=timeout or 30,
        )
        output = f"exit_code={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        if result.returncode != 0:
            audit_log("bash_error", {"command": command, "exit_code": result.returncode})
        return _handle_large_output(output, cfg)
    except subprocess.TimeoutExpired:
        audit_log("bash_timeout", {"command": command, "timeout": timeout})
        return f"Error: command timed out after {timeout or 30} seconds"
    except Exception as e:
        audit_log("bash_exception", {"command": command, "error": str(e)})
        return f"Error: {e}"

def bash_background(command: str, cwd: str = ".", *, config: Config | None = None) -> str:
    """Execute a shell command in the background and return its PID.
    
    Respects trust modes similarly to the bash tool.
    Returns the PID which can be used with bash_output or kill_shell.
    """
    cfg = config or Config()

    if cfg.trust_mode == TrustMode.SAFE:
        msg = f"Error: bash_background command blocked by safe trust mode"
        audit_log("bash_blocked", {"trust_mode": "safe"})
        return msg

    audit_log("bash_background_started", {"command": command, "cwd": cwd})

    from morgan.sandbox import LocalSandbox
    sandbox = LocalSandbox(config=cfg)
    try:
        pid = sandbox.run_background(command, cwd=cwd)
        return f"Started background task with PID: {pid}"
    except Exception as e:
        return f"Error starting background task: {e}"

def bash_output(pid: int, *, config: Config | None = None) -> str:
    """Read the current output from a background task."""
    cfg = config or Config()
    from morgan.sandbox import LocalSandbox
    sandbox = LocalSandbox(config=cfg)
    
    out = sandbox.get_output(pid)
    return _handle_large_output(out, cfg) if out else "No new output."

def kill_shell(pid: int, *, config: Config | None = None) -> str:
    """Terminate a background task and its children."""
    cfg = config or Config()
    from morgan.sandbox import LocalSandbox
    sandbox = LocalSandbox(config=cfg)
    
    res = sandbox.kill(pid)
    audit_log("kill_shell", {"pid": pid, "result": res})
    return res


def list_dir(path: str = ".", depth: int = 1, *, config: Config | None = None) -> str:
    """List contents of a directory inside the workspace.

    Validates that the resolved path stays within ``config.workspace_dir``.
    Returns a sorted list of filenames and directories, including read-only permissions.
    """
    cfg = config or Config()
    resolved = resolve_and_validate(path, cfg.workspace_dir)

    if not resolved.exists():
        return f"Error: directory not found: {path}"

    if not resolved.is_dir():
        return f"Error: path is a file, not a directory: {path}"

    return _list_dir_recursive(resolved, depth=depth)


def _list_dir_recursive(dir_path: Path, depth: int) -> str:
    """Recursively list directory contents up to specified depth."""
    if depth < 0:
        return ""

    try:
        entries = []
        for entry in sorted(dir_path.iterdir()):
            mode = "dir" if entry.is_dir() else "file"
            size = entry.stat().st_size if entry.is_file() else 0
            mtime = entry.stat().st_mtime

            entry_info = f"{entry.name} ({mode}, {size} bytes, mtime={mtime})"

            if depth > 0 and entry.is_dir():
                subdir_content = _list_dir_recursive(entry, depth - 1)
                if subdir_content:
                    entry_info += f"\n  {subdir_content}"

            entries.append(entry_info)
        return "\n".join(entries)
    except PermissionError:
        return f"{dir_path.name} (permission denied)"


def plan(goal: str, constraints: dict[str, str] | None = None, *, config: Config | None = None) -> str:
    """Generate a structured plan for achieving a goal.
    
    Writes the plan to PLAN.md in the workspace using the Memory module.
    """
    from morgan.memory import Memory
    
    cfg = config or Config()
    mem = Memory(config=cfg)
    mem.init()
    
    frontmatter = "---\nstatus: planning\ngoal_id: current\n---\n"
    content = f"# Goal\n\n{goal}\n\n"
    
    if constraints:
        content += "## Constraints\n\n"
        for k, v in constraints.items():
            content += f"- **{k}**: {v}\n"
            
    content += "\n## Plan\n\n1. [ ] Initial step\n"
    
    mem.write("PLAN.md", frontmatter + content)
    
    audit_log("plan_created", {"goal": goal})
    return f"Created PLAN.md for goal: {goal}"


def think(reasoning: str, *, config: Config | None = None) -> str:
    """Record internal reasoning for debugging and memory tracking.

    Logs to audit and memory, respects trust modes, and returns summary.
    """
    cfg = config or Config()

    audit_log("think", {"reasoning": reasoning})
    return f"thought recorded"


def get_time() -> str:
    """Get the current time.

    A simple utility tool to demonstrate tool calling in the agent loop.
    """
    import datetime
    return datetime.datetime.now().strftime("%H:%M:%S on %Y-%m-%d")


def hello() -> str:
    """Placeholder tool — returns a greeting."""
    return "hello from morgan"


def get_native_tools(config: Config | None = None) -> list:
    """Return a list of StructuredTool instances for all native tools.

    If *config* is provided, each tool function is wrapped in a closure
    that injects the config.  This lets the model call tools without
    knowing about the config parameter, while the tools still operate
    on the correct workspace directory and trust mode.
    """
    from langchain_core.tools import StructuredTool

    cfg = config  # captured by closures below

    # --- Wrapper functions that close over *cfg* ---
    # Each wrapper has an explicit signature so Pydantic/LangChain can
    # introspect the type hints for schema generation.

    def _read_file(path: str, limit: int | None = None) -> str:
        """Read a file inside the workspace. Returns contents or an error message."""
        return read_file(path, limit, config=cfg)

    def _write_file(path: str, content: str) -> str:
        """Write text content to a file inside the workspace."""
        return write_file(path, content, config=cfg)

    def _edit_file(path: str, old_string: str, new_string: str) -> str:
        """Find and replace text in a file inside the workspace."""
        return edit_file(path, old_string, new_string, config=cfg)

    def _list_dir(path: str = ".", depth: int = 1) -> str:
        """List contents of a directory inside the workspace."""
        return list_dir(path, depth, config=cfg)

    def _bash(command: str, timeout: int | None = 30, cwd: str = ".") -> str:
        """Execute a shell command inside the workspace."""
        return bash(command, timeout, cwd, config=cfg)

    def _plan(goal: str, constraints: dict[str, str] | None = None) -> str:
        """Generate a structured plan for achieving a goal."""
        return plan(goal, constraints, config=cfg)

    def _think(reasoning: str) -> str:
        """Record internal reasoning for debugging and memory tracking."""
        return think(reasoning, config=cfg)

    def _bash_background(command: str, cwd: str = ".") -> str:
        """Execute a shell command in the background and return its PID."""
        return bash_background(command, cwd, config=cfg)

    def _bash_output(pid: int) -> str:
        """Read the current output from a background task."""
        return bash_output(pid, config=cfg)

    def _kill_shell(pid: int) -> str:
        """Terminate a background task and its children."""
        return kill_shell(pid, config=cfg)

    def _git_status() -> str:
        """Get the current git status."""
        return bash("git status", timeout=10, config=cfg)

    def _git_diff() -> str:
        """Get the current git diff."""
        return bash("git diff", timeout=10, config=cfg)

    def _git_commit(message: str) -> str:
        """Commit all changes with a message."""
        return bash(f"git add . && git commit -m '{message}'", timeout=15, config=cfg)

    def _run_test(target: str = "tests/") -> str:
        """Run the test suite."""
        return bash(f"pytest {target}", timeout=60, config=cfg)

    def _run_linter(target: str = ".") -> str:
        """Run standard linters (ruff, mypy)."""
        return bash(f"ruff check {target}", timeout=30, config=cfg)

    def _search(query: str, path: str = ".") -> str:
        """Search for a string in the workspace."""
        return bash(f"grep -rn '{query}' {path}", timeout=30, config=cfg)

    def _web_fetch(url: str) -> str:
        """Fetch content from a URL."""
        return bash(f"curl -sL {url} | head -c 8000", timeout=15, config=cfg)

    tools = []

    tools.append(StructuredTool.from_function(
        func=_read_file,
        name="read_file",
        description="Read a file inside the workspace. Returns contents or an error message.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_write_file,
        name="write_file",
        description="Write text content to a file inside the workspace. Returns a summary with path and byte size.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_edit_file,
        name="edit_file",
        description="Find and replace text in a file inside the workspace. Returns a summary of changes.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_list_dir,
        name="list_dir",
        description="List contents of a directory inside the workspace.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_bash,
        name="bash",
        description="Execute a shell command inside the workspace. Returns output, exit code, and errors.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_plan,
        name="plan",
        description="Generate a structured plan for achieving a goal.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_think,
        name="think",
        description="Record internal reasoning for debugging and memory tracking.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_bash_background,
        name="bash_background",
        description="Execute a shell command in the background and return its PID. Use this for servers or long-running tasks.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_bash_output,
        name="bash_output",
        description="Read the current output from a background task.",
        infer_schema=True,
    ))

    tools.append(StructuredTool.from_function(
        func=_kill_shell,
        name="kill_shell",
        description="Terminate a background task and its children.",
        infer_schema=True,
    ))

    # Phase 3 Extended Tools
    for func, name, desc in [
        (_git_status, "git_status", "Get the current git status."),
        (_git_diff, "git_diff", "Get the current git diff."),
        (_git_commit, "git_commit", "Commit all changes with the given message."),
        (_run_test, "run_test", "Run the test suite using pytest."),
        (_run_linter, "run_linter", "Run standard code linters."),
        (_search, "search", "Search for a string across files in a directory."),
        (_web_fetch, "web_fetch", "Fetch content from a URL via curl.")
    ]:
        tools.append(StructuredTool.from_function(
            func=func,
            name=name,
            description=desc,
            infer_schema=True,
        ))

    return tools


