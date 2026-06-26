# Agent Guide — Morgan

This document tells any AI agent (including Claude Code, Cursor, or Morgan itself) how to work on the Morgan codebase. It is derived from `plan.md`, which is the source of truth for the product.

---

> **⚡ PHASE 0 IS ACTIVE.**
> The only permitted work right now is implementing the core harness skeleton in `morgan/`.
> Do not touch `docs/`, add memory files beyond `PLAN.md` and `NOTES.md`, build the web UI, or implement anything from Phase 1+.
> **Stop criteria:** `python -m morgan.cli "create a hello.py and run it"` completes end-to-end. That is when Phase 0 is done.

---

## 1. Project Identity

Morgan is a fully autonomous, open-source software-engineering and research agent harness. It is designed to be a low-overhead harness: failures should come from the model, not the harness loop, context handling, or tool execution.

This is **not a publishable library or package**. It is a real harness codebase in a working directory (`morgan/`). Do not add packaging, publishing, CI, or marketing infrastructure until v0.1.

---

## 2. Directory Layout

```
.
├── plan.md              # Source-of-truth product plan (read before any work)
├── agent.md             # This file
├── prompt_pack.md       # Context-driven prompts for every phase/task
├── requirements.txt     # Python dependencies only
├── README.md            # One-page setup and run instructions
├── record.md            # Shared agent handoff log (created on first run, appended thereafter)
├── docs/                # Deep planning documents
│   ├── ARCHITECTURE_DECISION_RECORD.md  # Major architecture decisions and rationale
│   ├── TOOL_INVENTORY.md                # All tools, schemas, risk classes, and trust-mode behavior
│   ├── PROMPT_LIBRARY.md                # Versioned prompts for the agent, sub-agents, and memory compiler
│   └── BENCHMARK_SUITE.md              # Canonical tasks, metrics, and comparison methodology
├── morgan/              # Core harness code (working directory, not a package)
│   ├── __init__.py      # empty
│   ├── cli.py           # Terminal entry point
│   ├── agent.py         # Main loop + tool dispatch
│   ├── conductor.py     # Long-horizon planning + orchestration
│   ├── tools.py         # Native tool definitions
│   ├── sandbox.py       # Sandbox provider interface + local subprocess adapter
│   ├── memory.py        # Memory compiler + .md file manager
│   ├── router.py        # Multi-provider model routing + budget tracking
│   └── config.py        # Settings, trust modes, policy
└── tests/               # Verification tests
    └── ...
```

---

## 3. Tech Stack

- **Python 3.11+ (only — no Rust, no TypeScript, no compiled extensions in v0.1)**
- **LangGraph + LangChain** for the agent loop
- **`langchain_core.utils.init_chat_model`** for multi-provider model access
- **Pydantic v2** for tool schemas
- **Typer + Rich** for the CLI
- **pytest** for tests
- **subprocess** for Phase 0 sandbox; **Docker / devcontainer** for Phase 2
- **JSON / SQLite** for checkpoints; optional vector store (Chroma, FAISS, LanceDB) in Phase 1+

---

## 4. How to Run and Test

### Setup

```bash
cd /home/user
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the harness

```bash
python -m morgan.cli "create a hello.py file and run it"
```

### Run tests

```bash
pytest tests/
```

Every feature must have at least one test. The minimal end-to-end test is the hello-world command above.

---

## 5. Development Rules

### Code style

- Use Pydantic models for every tool input and output.
- Use type hints everywhere.
- Keep functions small and focused.
- Prefer `async` for I/O-bound work (file reads, shell, model calls).
- Avoid HTTP/RPC between harness components. The loop is in-process.
- Never hardcode API keys. Read them from environment variables.

### Safety rules

- All file paths must be validated to stay inside the workspace directory.
- Destructive operations (delete, overwrite, deploy, network egress, expensive calls) must respect the trust mode in `config.py`.
- Shell commands must be executed in the sandbox (subprocess with cwd restriction in Phase 0; Docker/devcontainer in Phase 2).
- Background tasks must use process groups and be killable with timeouts.
- Every action must be logged to the audit log.

### Performance rules

- Tool outputs larger than 8 KB should be written to the filesystem and referenced by path, not serialized into the conversation.
- Only changed files are added to the model context. Use file hashes to detect changes.
- Conversation history is append-only. Do not mutate past turns.
- Use the cheapest/fastest model band that can reliably complete a task; escalate only when validation fails.
- Run independent sub-agents concurrently.
- **Do not add compiled extensions or Rust hot paths.** Profile a working system first. See ADR-001.

### Memory rules

**Phase 0 — use only these two files:**
- `PLAN.md` — living plan with task status. Update after every completed task.
- `NOTES.md` — working notes, errors encountered, and observations.

**Phase 1+ — add remaining memory files when the loop runs end-to-end:**
- `MORGAN.md` — project conventions and agent instructions.
- `GOALS.md` — current objectives and definition of done.
- `DECISIONS.md` — architectural decisions with rationale.
- `RUNBOOK.md` — repeatable procedures and commands.
- `ARTIFACTS.md` — produced outputs and their status.

After every significant task, run the memory compiler to extract lessons and write them to the correct file. Stale entries must be flagged with a freshness caveat; verify file/function references before using them.

---

## 6. How to Add a Feature

1. **Check `plan.md`** to confirm the feature is in the active phase.
2. **Write the test first** in `tests/`. The test should fail before the feature exists.
3. **Implement the feature** in the smallest possible file.
4. **Register it** in `agent.py` (for tools) or `conductor.py` (for planning logic) or `sandbox.py` (for sandbox providers) or `router.py` (for providers).
5. **Run the test**. Make it pass.
6. **Run the full suite** with `pytest tests/`.
7. **Run the hello-world smoke test** with `python -m morgan.cli "create a hello.py and run it"`.
8. **Update memory files** if the change affects architecture or conventions.

---

## 7. Trust Modes

Implement in `config.py`. Every tool must check the mode before executing a risky action.

- **Default:** ~90% autonomous. Ask for approval only on destructive, irreversible, external, or high-cost actions.
- **Safe:** Ask for approval on every write and shell command.
- **Full Access:** No interactive approvals. Run inside a strict policy (tool allowlist, max steps, max cost, max time, sandbox).

---

## 8. Common Agent Tasks

### Add a new tool

1. Define a Pydantic input model in `tools.py`.
2. Write an async function that performs the action and returns a result.
3. Add it to the tool registry in `agent.py`.
4. Add a test in `tests/test_tools.py`.

### Add a new sub-agent

1. Create a `.md` file under `morgan/agents/` with YAML frontmatter (`name`, `tools`, `model`, `max_turns`, `memory`).
2. Add a factory function in `conductor.py` that spawns the sub-agent with its own context window.
3. Add a test that spawns the sub-agent and checks its output.

### Add a new sandbox provider

1. Implement the `SandboxProvider` interface in `sandbox.py`.
2. Add adapters: `LocalSubprocessProvider` (Phase 0), `DockerProvider` (Phase 2), `CloudProvider` (Phase 4+).
3. Add a test that runs a shell command in the provider and returns the output.

### Add a new model provider

1. Add configuration in `config.py` (env var name, base URL, model list).
2. Add a routing rule in `router.py` (fast band / reasoning band / speculative band).
3. Add a test that calls the router with a sample prompt and returns a model instance.

---

## 9. What to Avoid

- Do not turn this into a published PyPI/Node package until v0.1.
- Do not add a client-server HTTP layer between the harness and the tools.
- Do not build a web UI before the core CLI harness works end-to-end.
- Do not add heavy observability dashboards before the loop is fast.
- Do not commit API keys, secrets, or `.env` files.
- Do not write code without a corresponding test.
- **Do not add Rust, PyO3, Cython, or any compiled extensions.** Profile a working system first (see ADR-001).
- **Do not implement Phase 1+ memory files during Phase 0.** Use only `PLAN.md` and `NOTES.md` until hello-world passes.

---

## 10. Verification Checklist

Before considering any task done, verify:

- [ ] The code runs: `python -m morgan.cli "create a hello.py and run it"`.
- [ ] The tests pass: `pytest tests/`.
- [ ] No API keys are hardcoded.
- [ ] File paths are workspace-relative and validated.
- [ ] Destructive actions respect the trust mode.
- [ ] Memory files are updated if the task changed architecture or conventions.
- [ ] A benchmark or timing measurement was added if the task affects speed.

---

## 11. Deep Planning Documents

The `docs/` directory contains the detailed planning artifacts that back up `plan.md`. Any agent working on Morgan should read the relevant document before making decisions in these areas:

- **`docs/ARCHITECTURE_DECISION_RECORD.md`** — Read before changing the runtime, architecture, sandbox, provider, or trust model. ADR-001 explicitly rules out Rust/compiled extensions until benchmarks on a working system justify them.
- **`docs/TOOL_INVENTORY.md`** — Read before adding, modifying, or removing tools. Contains the full risk taxonomy, trust-mode behavior matrix, and input/output schemas for every native tool.
- **`docs/PROMPT_LIBRARY.md`** — Read before editing any system prompt, tool-use prompt, or sub-agent prompt. Prompts are versioned; changes here must be tracked.
- **`docs/BENCHMARK_SUITE.md`** — Read before optimizing performance or claiming a speed improvement. Defines the canonical tasks, metrics, and comparison methodology.

If a change contradicts one of these documents, update the document first and record the reasoning.

---

## 12. Agent Handoff Workflow — `record.md`

Every agent that works on Morgan must maintain a shared handoff log so that the next agent can see what was done, when, and why.

### Workflow

1. **At the start of every agent session:**
   - Read `agent.md` (this file).
   - Check for `record.md` at the workspace root.
   - If `record.md` does **not** exist, create it with a header and the first entry.
   - If `record.md` **already exists**, read it to understand the previous work before starting.

2. **At the start of the work cycle:**
   - Append a new entry to `record.md` with:
     - `date`
     - `start_time`
     - `agent` (the agent identifier or name)
     - `status: started`
     - `description`: a one-sentence summary of what this cycle will work on.

3. **At the end of the work cycle:**
   - Update the same entry with:
     - `end_time`
     - `status: completed` or `status: blocked` or `status: partial`
     - `description`: a one-sentence summary of what was actually done, including any blockers or next steps.

4. **Before switching to another agent:**
   - Ensure the current cycle is closed in `record.md`.
   - The next agent reads `record.md` first to pick up where the previous agent left off.

### `record.md` format

```markdown
# Morgan — Agent Work Record

## Entry 1 — 2026-06-22
- **agent:** Claude Code
- **date:** 2026-06-22
- **start_time:** 14:30
- **end_time:** 15:45
- **status:** completed
- **description:** Created the initial `morgan/` directory and implemented the `read_file` and `write_file` tools.
- **next_steps:** Implement the `bash` tool and the hello-world smoke test.
```

### Rules

- Do not create a second `record.md` if one already exists. Append to the existing file.
- Keep each entry concise but informative. One sentence is enough.
- Always close the cycle with an `end_time` and `status` before stopping work.
- If a task was blocked, explain why and what the next agent should do.
- If a task was partially completed, list what is finished and what remains.

---

## 13. Contact / Source of Truth

- Product plan: `plan.md`
- Agent instructions: `agent.md` (this file)
- Prompt pack: `prompt_pack.md`
- Deep planning documents: `docs/`

When in doubt, read `plan.md` first, then consult the relevant `docs/` document for the area you are changing.
