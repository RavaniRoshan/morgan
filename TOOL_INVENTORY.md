# Morgan Tool Inventory

**Status:** Draft for v0.1  
**Date:** 2026-06-22  
**Scope:** All tools available to the Morgan agent, their schemas, risk classes, and trust-mode behavior.

---

## 1. Overview

Tools are the grammar of the Morgan harness. A good tool design makes the model powerful; a poor one makes it dumb or dangerous. Every tool in this inventory has:

- A clear name and purpose.
- A Pydantic-style input schema.
- A Pydantic-style output schema.
- A **risk class**.
- A **trust-mode behavior**.
- A **sandbox requirement**.
- Notes on streaming, background execution, and large-output handling.

This inventory is a living document. New tools can be added via the registry, via MCP servers, or via user-defined `.md` sub-agent definitions.

---

## 2. Risk Taxonomy

| Risk Class | Description | Examples | Default Trust Mode |
|---|---|---|---|
| `read` | Reads data without modifying the workspace. | `read_file`, `list_dir`, `search` | Auto-approve |
| `write` | Modifies files in the workspace. | `write_file`, `edit_file`, `delete_file` | Ask |
| `shell` | Executes arbitrary shell commands. | `bash`, `bash_background` | Ask |
| `network` | Makes external network requests. | `web_fetch` | Ask |
| `git` | Modifies version control state. | `git_commit` | Ask |
| `meta` | Modifies the agent’s own state or plan. | `plan`, `compact`, `write_memory` | Auto-approve (low-risk) / Ask (high-risk) |
| `agent` | Spawns another agent or sub-agent. | `spawn_subagent` | Ask |
| `mcp` | Loaded dynamically from an MCP server; risk determined at load time. | Varies | Classified at registration |

---

## 3. Trust-Mode Behavior Matrix

| Tool Class | Safe Mode | Default / Fast Mode | Full-Access Mode |
|---|---|---|---|
| `read` | Auto-approve | Auto-approve | Auto-approve (within policy) |
| `write` | Ask every time | Ask for destructive/overwrites; auto-approve new files | Allow if within policy and allowlist |
| `shell` | Ask every time | Ask for destructive / network / system-level commands; auto-approve safe commands like `pytest`, `npm test` | Allow if within policy and allowlist |
| `network` | Ask every time | Ask unless domain is in allowlist | Allow if domain is in policy allowlist |
| `git` | Ask every time | Ask for `commit`, `push`, `reset`; auto-approve `status`, `diff` | Allow if within policy |
| `meta` | Ask for `write_memory`, `plan` changes | Auto-approve reads; ask for major plan changes | Allow if within policy |
| `agent` | Ask every time | Ask for sub-agent spawns | Allow if within policy |

---

## 4. Native Tools

### 4.1 File System Tools

#### `read_file`

Read the contents of a file within the workspace.

**Risk class:** `read`  
**Sandbox:** In-process (no sandbox needed)  
**Streaming:** No  
**Large output handling:** If the file exceeds 8 KB, return a reference object and expose the full content via `read_output`.

**Input schema:**
```json
{
  "path": "string (required)",
  "offset": "integer (optional, default 0)",
  "limit": "integer (optional, default 200 lines)"
}
```

**Output schema:**
```json
{
  "content": "string or reference object",
  "path": "string",
  "size": "integer",
  "truncated": "boolean"
}
```

**Validation:** Path must resolve inside the workspace.

---

#### `write_file`

Create or overwrite a file in the workspace.

**Risk class:** `write`  
**Sandbox:** In-process (writes are validated to the workspace)  
**Streaming:** No

**Input schema:**
```json
{
  "path": "string (required)",
  "content": "string (required)",
  "append": "boolean (optional, default false)"
}
```

**Output schema:**
```json
{
  "path": "string",
  "size": "integer",
  "created": "boolean",
  "overwritten": "boolean"
}
```

**Validation:** Path must resolve inside the workspace. Parent directories are created automatically.

---

#### `edit_file`

Make a targeted string replacement in a file.

**Risk class:** `write`  
**Sandbox:** In-process

**Input schema:**
```json
{
  "path": "string (required)",
  "old_string": "string (required)",
  "new_string": "string (required)"
}
```

**Output schema:**
```json
{
  "path": "string",
  "replacements": "integer",
  "success": "boolean",
  "error": "string (optional)"
}
```

**Validation:** If `old_string` is not found exactly once, return an error. Use `write_file` for bulk replacements.

---

#### `delete_file`

Delete a file or directory in the workspace.

**Risk class:** `write` (destructive)  
**Sandbox:** In-process

**Input schema:**
```json
{
  "path": "string (required)",
  "recursive": "boolean (optional, default false)"
}
```

**Output schema:**
```json
{
  "path": "string",
  "deleted": "boolean",
  "error": "string (optional)"
}
```

**Validation:** Path must resolve inside the workspace. `recursive` is required for directories.

---

#### `list_dir`

List the contents of a directory.

**Risk class:** `read`  
**Sandbox:** In-process

**Input schema:**
```json
{
  "path": "string (required)",
  "depth": "integer (optional, default 1)"
}
```

**Output schema:**
```json
{
  "entries": [
    {
      "name": "string",
      "type": "file | directory",
      "size": "integer",
      "modified_at": "ISO timestamp"
    }
  ]
}
```

**Validation:** Path must resolve inside the workspace. `depth` is capped to avoid huge outputs.

---

#### `search`

Search for files or content in the workspace using the repo index.

**Risk class:** `read`  
**Sandbox:** In-process

**Input schema:**
```json
{
  "query": "string (required)",
  "glob": "string (optional, e.g. '*.py')",
  "max_results": "integer (optional, default 20)"
}
```

**Output schema:**
```json
{
  "results": [
    {
      "path": "string",
      "score": "number",
      "snippet": "string (optional)"
    }
  ]
}
```

---

#### `grep`

Run a regex search across files in the workspace.

**Risk class:** `read`  
**Sandbox:** In-process

**Input schema:**
```json
{
  "pattern": "string (required)",
  "path": "string (optional, default workspace root)",
  "max_results": "integer (optional, default 50)"
}
```

**Output schema:**
```json
{
  "matches": [
    {
      "path": "string",
      "line": "integer",
      "text": "string"
    }
  ]
}
```

**Validation:** Path must resolve inside the workspace.

---

### 4.2 Shell and Execution Tools

#### `bash`

Run a shell command in the sandbox.

**Risk class:** `shell`  
**Sandbox:** Required (Docker/devcontainer or subprocess fallback)  
**Streaming:** Yes (stdout/stderr streamed to the agent)  
**Background:** No

**Input schema:**
```json
{
  "command": "string (required)",
  "cwd": "string (optional, default workspace root)",
  "timeout": "integer (optional, default 30 seconds)",
  "env": "object (optional)"
}
```

**Output schema:**
```json
{
  "stdout": "string (or reference for large output)",
  "stderr": "string (or reference for large output)",
  "exit_code": "integer",
  "timed_out": "boolean",
  "duration_ms": "integer"
}
```

**Validation:** `cwd` must resolve inside the workspace. Dangerous patterns (e.g., `rm -rf /`, `curl | sh`) are flagged or blocked by the policy engine.

---

#### `bash_background`

Start a long-running shell command and continue the agent loop.

**Risk class:** `shell`  
**Sandbox:** Required  
**Streaming:** Output buffered and fetched via `bash_output`  
**Background:** Yes

**Input schema:**
```json
{
  "command": "string (required)",
  "cwd": "string (optional, default workspace root)",
  "session_id": "string (optional, auto-generated if omitted)"
}
```

**Output schema:**
```json
{
  "session_id": "string",
  "pid": "integer",
  "status": "started"
}
```

**Validation:** `cwd` must resolve inside the workspace. Process groups are tracked for cleanup.

---

#### `bash_output`

Fetch buffered output from a background command.

**Risk class:** `read` (does not modify state)  
**Sandbox:** In-process query against sandbox registry

**Input schema:**
```json
{
  "session_id": "string (required)",
  "since": "integer (optional, line offset, default 0)",
  "limit": "integer (optional, default 100 lines)"
}
```

**Output schema:**
```json
{
  "session_id": "string",
  "stdout": "string",
  "stderr": "string",
  "running": "boolean",
  "exit_code": "integer (null if still running)"
}
```

---

#### `kill_shell`

Terminate a background shell command.

**Risk class:** `shell`  
**Sandbox:** Required

**Input schema:**
```json
{
  "session_id": "string (required)",
  "force": "boolean (optional, default false)"
}
```

**Output schema:**
```json
{
  "session_id": "string",
  "killed": "boolean",
  "exit_code": "integer (optional)"
}
```

**Behavior:** Sends SIGTERM; if still running after a timeout, sends SIGKILL. Kills the entire process group, not just the shell wrapper.

---

#### `run_test`

Run a test command and return structured results.

**Risk class:** `shell` (but often auto-approved in default mode)  
**Sandbox:** Required

**Input schema:**
```json
{
  "command": "string (required, e.g. 'pytest')",
  "cwd": "string (optional)",
  "timeout": "integer (optional, default 120 seconds)"
}
```

**Output schema:**
```json
{
  "success": "boolean",
  "summary": "string",
  "failures": [
    {
      "test": "string",
      "error": "string"
    }
  ],
  "stdout": "string (or reference)",
  "stderr": "string (or reference)",
  "exit_code": "integer"
}
```

---

#### `run_linter`

Run a linter or type checker and return diagnostics.

**Risk class:** `shell`  
**Sandbox:** Required

**Input schema:**
```json
{
  "command": "string (required, e.g. 'python -m py_compile')",
  "cwd": "string (optional)",
  "timeout": "integer (optional, default 60 seconds)"
}
```

**Output schema:**
```json
{
  "diagnostics": [
    {
      "file": "string",
      "line": "integer",
      "message": "string",
      "severity": "error | warning | info"
    }
  ],
  "exit_code": "integer",
  "stdout": "string (or reference)",
  "stderr": "string (or reference)"
}
```

---

### 4.3 Network Tools

#### `web_fetch`

Fetch content from a URL.

**Risk class:** `network`  
**Sandbox:** Network requests are routed through the sandbox or an allowlist proxy.

**Input schema:**
```json
{
  "url": "string (required)",
  "max_length": "integer (optional, default 8000 tokens)",
  "extract_text": "boolean (optional, default true)"
}
```

**Output schema:**
```json
{
  "url": "string",
  "title": "string (optional)",
  "text": "string (truncated to max_length)",
  "status_code": "integer",
  "error": "string (optional)"
}
```

**Policy:** In default mode, only URLs in the allowlist or explicit user-approved domains are fetched. Safe mode requires approval for every fetch.

---

### 4.4 Git Tools

#### `git_status`

Show the working tree status.

**Risk class:** `git` (read-only)  
**Sandbox:** In-process or sandbox

**Input schema:**
```json
{
  "cwd": "string (optional)"
}
```

**Output schema:**
```json
{
  "branch": "string",
  "status": "string"
}
```

---

#### `git_diff`

Show staged or unstaged changes.

**Risk class:** `git` (read-only)  
**Sandbox:** In-process or sandbox

**Input schema:**
```json
{
  "staged": "boolean (optional, default false)",
  "cwd": "string (optional)"
}
```

**Output schema:**
```json
{
  "diff": "string (or reference)"
}
```

---

#### `git_commit`

Stage files and commit changes.

**Risk class:** `git` (destructive)  
**Sandbox:** Required

**Input schema:**
```json
{
  "message": "string (required)",
  "files": "list[string] (required)",
  "cwd": "string (optional)"
}
```

**Output schema:**
```json
{
  "commit_hash": "string",
  "files": "list[string]"
}
```

**Policy:** Requires approval in default and safe modes. In full-access mode, allowed only if `git_commit` is in the tool allowlist.

---

### 4.5 Meta / Planning Tools

#### `plan`

Create or update the `PLAN.md` living plan.

**Risk class:** `meta`  
**Sandbox:** In-process

**Input schema:**
```json
{
  "goal": "string (required)",
  "phases": "list[string] (optional)",
  "tasks": [
    {
      "id": "string",
      "description": "string",
      "depends_on": "list[string]",
      "status": "pending | in_progress | done | blocked"
    }
  ],
  "notes": "string (optional)"
}
```

**Output schema:**
```json
{
  "path": "string",
  "updated": "boolean"
}
```

---

#### `think`

Ask the model to think step-by-step before acting. This is a no-op tool that encourages reasoning.

**Risk class:** `meta`  
**Sandbox:** None

**Input schema:**
```json
{
  "thoughts": "string (required)"
}
```

**Output schema:**
```json
{
  "acknowledged": "boolean"
}
```

---

#### `compact`

Summarize the conversation history so far and append the summary to the transcript.

**Risk class:** `meta`  
**Sandbox:** None

**Input schema:**
```json
{
  "max_tokens": "integer (optional, default 1000)"
}
```

**Output schema:**
```json
{
  "summary": "string",
  "original_turns": "integer",
  "compressed_turns": "integer"
}
```

**Behavior:** Append-only; never deletes earlier messages. Preserves prompt-cache stability by keeping the system prompt and recent history intact.

---

### 4.6 Memory Tools

#### `read_memory`

Read a memory file or a section of it.

**Risk class:** `read`  
**Sandbox:** In-process

**Input schema:**
```json
{
  "name": "string (required, e.g. 'NOTES')",
  "section": "string (optional)"
}
```

**Output schema:**
```json
{
  "content": "string"
}
```

---

#### `write_memory`

Append a structured entry to a memory file.

**Risk class:** `meta` (write to memory)  
**Sandbox:** In-process

**Input schema:**
```json
{
  "name": "string (required)",
  "type": "decision | lesson | note | convention | procedure | artifact",
  "summary": "string (required)",
  "file_references": "list[string] (optional)",
  "confidence": "number (optional, 0-1)"
}
```

**Output schema:**
```json
{
  "path": "string",
  "updated": "boolean"
}
```

**Behavior:** Appends the entry with a timestamp and freshness caveat. The memory compiler may also call this automatically after significant tasks.

---

### 4.7 Agent Tools

#### `spawn_subagent`

Spawn a sub-agent to handle a focused, independent task.

**Risk class:** `agent`  
**Sandbox:** Sub-agent inherits the same sandbox and policy constraints.

**Input schema:**
```json
{
  "name": "string (required, e.g. 'security-reviewer')",
  "prompt": "string (required)",
  "tools": "list[string] (optional, default inherits from definition)",
  "max_turns": "integer (optional, default 25)",
  "memory": "user | project | local (optional)"
}
```

**Output schema:**
```json
{
  "subagent_id": "string",
  "result": "string",
  "status": "completed | failed | timed_out"
}
```

**Behavior:** Sub-agents run in isolated context windows. The conductor can run them in parallel. Results are returned as summaries to avoid polluting the parent context.

---

### 4.8 Output Handling

#### `read_output`

Fetch the full contents of a large output referenced by another tool.

**Risk class:** `read`  
**Sandbox:** In-process

**Input schema:**
```json
{
  "path": "string (required)",
  "limit": "integer (optional, default 2000 lines)"
}
```

**Output schema:**
```json
{
  "content": "string"
}
```

**Behavior:** Used when a tool returns a reference object instead of the full text to keep the context window small.

---

## 5. MCP Tool Handling

MCP servers expose external tools. Because MCP servers can do almost anything, we treat them as risky by default.

**Rules:**
1. Every MCP tool is registered with a default risk class of `mcp` (treated as `shell` until classified).
2. The user or `MORGAN.md` can map MCP tools to lower-risk classes.
3. MCP tools inherit the same trust-mode behavior as native tools of the same risk class.
4. MCP servers are loaded from a user-controlled `mcp.json` file, never auto-loaded from untrusted sources.
5. MCP tool outputs are passed through the same zero-copy large-output handler as native tools.

---

## 6. Tool Registry

The `ToolRegistry` is the single source of truth for available tools at runtime.

- Native tools are registered at startup.
- MCP tools are registered after MCP servers are loaded.
- Sub-agent definitions are loaded from `.md` files and may expose additional tool subsets.
- The registry exposes the JSON schema of every tool to the model via `bind_tools`.

---

## 7. Future Tools (Post-v0.1)

- `deploy` — deploy to a configured environment.
- `create_issue` / `create_pr` — integrate with GitHub/GitLab.
- `run_security_scan` — static analysis for vulnerabilities.
- `compare_files` — semantic diff between files.
- `visualize` — generate diagrams or flowcharts.
- `voice_transcribe` — optional voice input.

---

## 8. Versioning

- This inventory is versioned with the harness.
- Every tool change requires a corresponding update to this document and a test in `tests/test_tools.py`.
- The model sees the tool schemas from the registry, not from this document; this document is for human maintainers.
