# Morgan — Product Plan (Source of Truth)

**Version:** 0.1-draft  
**Date:** 2026-06-22  
**Status:** Implementation-ready. This document is the source of truth for building Morgan.

> **⚡ CURRENT STATUS: Phase 0 is active. No other phase work is permitted until `python -m morgan.cli "create a hello.py and run it"` passes end-to-end.**

---

## 1. What Morgan Is

Morgan is a fully autonomous, open-source software-engineering and research agent harness. It is designed to be the **fastest-to-execute agent harness**: if a run fails, the cause should be the model's reasoning, not the harness loop, context handling, or tool execution.

This is **not a library or a published package**. It is a real harness codebase in a working directory (`morgan/`), built like Claude Code started: a single, tight agent loop with tools, memory, and a CLI. Packaging, publishing, and polish come after the core works.

**Base:** Start from `langchain-ai/deepagents` as a dependency or forked reference, not as a package to wrap.

---

## 2. The Two Edges (Non-Negotiable Goals)

Every feature, file, and optimization must serve one or both of these goals.

### Edge 1: Fully autonomous software-engineer / research agent harness

After the user initializes Morgan with a goal and documentation, it must be able to:

- Decompose the goal into a long-horizon plan.
- Research, design, write, test, review, and refactor code on its own.
- Manage its own memory, state, and working notes across sessions.
- Recover from tool failures, model errors, and partial successes.
- Produce finished, verifiable artifacts (a working repo, a report, a deployed service).
- Ask for human input only when the trust policy requires it.

### Edge 2: Low-overhead harness

The harness itself must add minimal overhead. This means:

- Single-process, in-process loop by default. No HTTP hops between the harness and the tools.
- Smart context management: only changed information is sent to the model.
- Non-blocking execution of long commands (tests, builds, servers, deployments).
- Parallel sub-agents and speculative fast paths where safe.
- Prompt-cache-first design with stable schemas and append-only history.

**Speed target:** The bottleneck should always be the model API, not the harness. >70% of wall-clock time should be model latency, not Python overhead. We achieve this through pure Python optimizations — not via compiled extensions in v0.1.

---

## 3. Competitive Landscape

| Capability | Claude Code | OpenCode | OpenAI Codex | Cursor | KiloCode | `deepagents` (base) | Morgan Target |
|---|---|---|---|---|---|---|---|
| **License** | Closed | MIT | Apache 2.0 | Closed | MIT | MIT | MIT |
| **Default models** | Claude only | 75+ providers | GPT-Codex | Multi | Multi | Any tool-calling model | Multi, with smart routing |
| **Architecture** | Single TypeScript process | Go TUI + Bun/JS HTTP server | TypeScript/Node CLI | VS Code fork | VS Code extension | LangGraph / Python | **Single-process Python loop** |
| **Speed (same model)** | Baseline | ~78% slower [2] | Slightly slower [5] | ~12% faster on micro, worse on large [6] | Not benchmarked | Not optimized | **v0.1: parity via Python optimizations; v0.2: faster via hot-loop profiling** |
| **Context handling** | Up to 1M tokens; auto-compaction | Selective context | Full context | Effective 70K–120K [6] | Moderate | Filesystem + `/memories/` | 1M-equivalent; differential updates; prompt caching |
| **Tool count** | ~40 modular tools [7] | Core + plugins | Core + subagents | Inline + agent tools | Broad | Planning / filesystem / subagent | 40+ native tools + MCP |
| **Sub-agents** | Built-in, custom via `.md` [8] | Yes | Yes | Agent workspace, parallel | Agent Manager | Yes | First-class, declarative, parallel |
| **Background / non-blocking tasks** | Limited | Limited | `bash_output`, `kill_shell` [9] | Limited | Limited | No | Core feature (Phase 2) |
| **Memory** | Multi-layer + auto-extraction [7] | `AGENTS.md` + snapshots | `AGENTS.md` + cloud handoff | `.cursorrules` | ? | Filesystem + `AGENTS.md` | Memory compiler + `.md` store |
| **Human-in-the-loop** | Permission modes | `/undo` + git snapshots | Policy hooks | Approval UI | ? | Approval gates | Three trust modes |
| **Sandbox** | Local shell | Local shell | Containerized [5] | Local shell | Local shell | Pluggable | subprocess → Docker (Phase 2) |
| **MCP support** | Yes | Yes | Yes | Yes | Yes | Yes | Yes (Phase 3) |

### Speed Lessons

1. **Single-process beats client-server for latency.** Claude Code is one TypeScript process; OpenCode pays a localhost HTTP hop on every tool call — primary reason it is ~78% slower [2].
2. **Model latency dominates.** On a typical coding task, >70% of wall-clock time is waiting for the model API. A 2× faster hot loop on 30% of runtime = 15% overall improvement. The bigger wins are: fewer model calls, differential context, and prompt caching.
3. **IDE-first tools are faster for micro-tasks, worse for complex ones.** Cursor is ~12% faster on simple tasks but truncates context and loses coherence on large refactors [6].
4. **Sandboxing adds safety at the cost of speed.** Codex defaults to a container — slightly slower on filesystem-heavy tasks but safer to leave unattended [5].

---

## 4. Product Pillars

| Pillar | Definition |
|---|---|
| **Autonomy** | Long-horizon planning, self-directed execution, persistent memory, and recovery without constant human input. |
| **Speed** | The harness adds minimal latency. Overhead is measured, visible, and reduced via Python-native techniques first. |
| **Memory** | Every session improves the next. Lessons are stored as structured, human-readable `.md` files. |
| **Safety** | Three trust modes, sandboxing, approval gates, hard budget/time caps, and full audit logs. |
| **Extensibility** | MCP servers, custom tools, custom sub-agents, and pluggable sandboxes. |
| **Observability** | Traces, token usage, cost tracking, timing breakdowns, and checkpoint inspection. |

---

## 5. Architecture

### 5.1 Core Files (Working Directory: `morgan/`)

```
morgan/
├── agent.py          # Main loop + tool dispatch
├── tools.py          # Tool definitions (read, write, edit, bash, etc.)
├── sandbox.py        # Sandbox provider interface + local subprocess adapter
├── memory.py         # Memory compiler + .md file manager
├── conductor.py      # Long-horizon planning + sub-agent orchestration
├── router.py         # Multi-provider model routing + budget tracking
├── config.py         # Settings, trust modes, policy
├── cli.py            # Terminal entry point
└── __init__.py       # (empty, only to allow imports)
```

No `setup.py`, no `pyproject.toml` packaging metadata, no CI, no publish workflow until v0.1. Dependency management is via `requirements.txt` only.

### 5.2 Layers

1. **CLI Layer** — `cli.py`. Reads the user prompt, starts the loop, prints results.
2. **Conductor Layer** — `conductor.py`. Owns the goal, plan, and long-horizon loop. Decides what to do next and what to delegate.
3. **Agent Loop** — `agent.py`. Single-process, async tool loop. Binds tools, calls the model, executes tools, streams results.
4. **Tools Layer** — `tools.py`. Pydantic-modeled tools. 40+ native tools plus MCP-loaded tools.
5. **Sandbox Layer** — `sandbox.py`. Isolates shell/network execution. Local subprocess by default; Docker/devcontainer in Phase 2.
6. **Memory Layer** — `memory.py`. Working, episodic, semantic, and procedural memory exposed as files or indices.
7. **Model Router** — `router.py`. Provider-agnostic, budget-aware model selection.
8. **Safety Layer** — `config.py` + policy hooks. Trust modes, approval gates, budget caps, audit log.

### 5.3 Performance Design (Pure Python)

The following optimizations are achievable in Python without compiled extensions and will get Morgan to speed parity with Claude Code on same-model tasks:

- **In-process loop.** No HTTP between `agent.py` and `tools.py`.
- **Large output offloading.** Tool outputs > 8 KB are written to the filesystem and referenced by path, not serialized into the conversation.
- **Background task tools.** `bash_background` + `bash_output` + `kill_shell` — tests, builds, and servers run non-blocking.
- **File watcher + hash cache.** Only changed files enter the model context; unchanged files referenced by hash or pointer.
- **Stable schemas + append-only history.** Maximizes provider prompt-cache hits; never mutate past turns.
- **Async parallel sub-agents.** Independent tasks run concurrently with their own context windows.
- **Model cascading.** Cheap/fast model for routine tool calls; frontier model for planning and hard reasoning only.

> **Hot-loop Rust migration is explicitly out of scope for v0.1 and v0.2.** Profile first. >70% of latency is model API wait time — no compiled extension will fix that. If benchmarks after v0.1 show Python loop overhead > 15% of total wall-clock time, open an ADR for hot-loop optimization at that point. Not before.

---

## 6. Tech Stack

- **Language:** Python 3.11+ (only)
- **Agent framework:** LangGraph + LangChain
- **Model access:** `langchain_core.utils.init_chat_model` for multi-provider routing
- **Tool schemas:** Pydantic v2
- **CLI:** `typer` + `rich`
- **Sandbox:** subprocess (Phase 0); Docker / devcontainer (Phase 2); Modal / Daytona / Runloop (Phase 4+)
- **Persistence:** JSON/SQLite checkpoints; vector store optional (Chroma, FAISS, or LanceDB)
- **Tests:** `pytest`

---

## 7. Trust Model

| Mode | Behavior | Use Case |
|---|---|---|
| **Default** | ~90% autonomous. Approvals required for destructive, irreversible, external, or high-cost actions (deletes, deploys, network egress, large spend). | Daily engineering work. |
| **Safe** | Human approval required for every write, shell command, and external tool call. | Sensitive codebases, learning, or untrusted projects. |
| **Full Access** | No interactive approvals. Runs within a strict policy: tool allowlist, max steps, max cost, max time, sandbox isolation. Full audit log. | Overnight or long-horizon autonomous runs. |

The mode is set per session and can be overridden by per-tool or per-project policies.

---

## 8. Memory System

Four tiers, all exposed as files or indices:

1. **Working Memory** — LangGraph state + current conversation. Session-scoped.
2. **Episodic Memory** — Session transcripts, checkpoints, sub-agent outputs. Used for resumes and post-mortems.
3. **Semantic Memory** — Vector index of repo, documentation, and research findings. Used for retrieval and codebase understanding. *(Phase 1+)*
4. **Procedural Memory** — `.md` files that encode conventions, runbooks, decisions, and goals. This is the "code-as-human" layer.

### Memory Files

**Phase 0 (active — use only these two):**
- `PLAN.md` — living plan with phases, tasks, owners, status.
- `NOTES.md` — working notes, errors, and findings.

**Phase 1+ (add when the loop runs):**
- `MORGAN.md` — project conventions and agent instructions.
- `GOALS.md` — current objectives and definition of done.
- `DECISIONS.md` — architectural decisions with rationale.
- `RUNBOOK.md` — repeatable procedures and commands.
- `ARTIFACTS.md` — list of produced outputs and their status.

The memory compiler runs after each significant loop to extract decisions, lessons, and conventions and writes them to the appropriate file. Do not implement the full memory compiler before the loop works end-to-end.

---

## 9. Execution Backend

- **Phase 0–1 default:** Local subprocess with cwd restriction and PATH allowlist.
- **Phase 2 default:** Docker Compose or devcontainer, rootless when possible.
- **Phase 4+:** Adapters for Modal, Daytona, Runloop, AWS EC2, GCP Workstations.
- **Enterprise / BYO:** Bring-your-own infrastructure via a sandbox provider contract.

The same `.devcontainer` / `Dockerfile` / Nix spec is used everywhere so the environment is reproducible.

---

## 10. Roadmap

> **Phases are sequential. Do not start Phase N+1 until Phase N verification passes.**

### Phase 0 — Core Harness Skeleton (Week 1)

Goal: A minimal, end-to-end harness that accepts a prompt, reads/writes files, runs shell commands, and completes a simple task.

- Create `morgan/` working directory with all 8 core files.
- Add `requirements.txt` only.
- Implement native tools: `read_file`, `write_file`, `edit_file`, `bash`, `list_dir`, `plan`, `think`.
- Implement single-process async agent loop with LangGraph.
- Implement local subprocess sandbox with cwd restriction.
- Implement three trust modes in `config.py`.
- **Verification:** `python -m morgan.cli "create a hello.py and run it"` completes without error.

**Day-level targets:**
- Day 1: `cli.py`, `config.py` (trust modes), project scaffold
- Day 2: `tools.py` — `read_file`, `write_file`, `bash` (3 tools, Pydantic schemas)
- Day 3: `agent.py` — LangGraph loop, tool binding, model call, result streaming
- Day 4: Smoke test passes end-to-end
- Day 5: `sandbox.py` (subprocess cwd jail), `pytest tests/` green

### Phase 1 — Conductor & Memory (Weeks 2–3)

Goal: The harness can plan a multi-step task and persist memory across turns.

- Build `conductor.py` with plan generation, decomposition, and loop-until-done logic.
- Implement `PLAN.md` read/write and status updates.
- Implement memory manager and memory compiler (post-session extraction).
- Add full memory file set: `MORGAN.md`, `GOALS.md`, `NOTES.md`, `DECISIONS.md`, `RUNBOOK.md`, `ARTIFACTS.md`.
- Add staleness handling and file-reference verification.
- **Verification:** Prompt requiring planning and memory (e.g., "refactor this script into a module with tests") completes autonomously.

### Phase 2 — Speed & Parallelism (Weeks 4–5)

Goal: Remove structural overhead; enable non-blocking execution.

- Profile a 10-turn task end-to-end. Identify top 3 overhead sources. Fix them in Python.
- Implement background task tools: `bash_background`, `bash_output`, `kill_shell` with process groups and timeouts.
- Implement parallel sub-agent execution in `conductor.py`.
- Implement file watcher / hash cache and differential context updates.
- Add a basic repo index (file list, AST where easy; vector embeddings optional).
- **Verification:** Background test runs while main loop continues editing. Parallel sub-agents complete independent tasks concurrently.

> If profiling shows Python loop overhead > 15% of total wall-clock time after these optimizations, open a new ADR for hot-loop optimization. Not before.

### Phase 3 — Model Router & Extensibility (Weeks 6–7)

Goal: Multi-provider support, budget control, and a larger tool ecosystem.

- Implement `router.py` using `init_chat_model` with fast/reasoning/speculative bands.
- Implement token/cost tracking and hard budget caps.
- Add MCP server loading and tool conversion.
- Expand native tools: `search`, `grep`, `web_fetch`, `git_status`, `git_diff`, `git_commit`, `run_test`, `run_linter`.
- **Verification:** Same task with two different providers compares cost. Budget cap stops the run before overspend.

### Phase 4 — Performance & Benchmarking (Weeks 8–9)

Goal: Prove speed; add Docker sandboxing and cloud adapters.

- Build public benchmark suite with canonical tasks (see `docs/BENCHMARK_SUITE.md`).
- Measure wall-clock time and token usage against Claude Code on the same model.
- Implement prompt caching: stable system prompt segments, append-only history, tool schema caching.
- Refine context filtering and serialization.
- Add Docker/devcontainer sandbox provider. Cloud adapters (Modal, Daytona, Runloop, EC2) as stretch goals.
- **Verification:** Benchmark shows Morgan ≤ 20% slower than Claude Code on same model (parity, not faster — that comes in v0.2). Cloud sandbox runs a command successfully.

### Phase 5 — UI & Reference Projects (Weeks 10–11)

Goal: Demonstrate real-world autonomy; provide a monitoring surface.

- Build a lightweight web UI (FastAPI + SSE) for monitoring and approvals.
- Reference project 1: Build a full-stack web app from a PRD.
- Reference project 2: Conduct a research topic and produce a Markdown report.
- **Verification:** Both reference projects produce working artifacts. Web UI shows status and allows approval.

### Phase 6 — Hardening & Release (Weeks 12–13)

Goal: Safe, observable, and ready for public use.

- Add structured logging, tracing, and cost dashboards.
- Add audit logs and checkpoint rollback.
- Write architecture and usage docs.
- Add a comprehensive test suite; run it green.
- Tag v0.1 and publish to GitHub as open-source beta.
- **Verification:** All tests pass. A third party can clone the repo and run the hello-world test in < 10 minutes.

---

## 11. Success Metrics

| Metric | v0.1 Target | v0.2 Target |
|---|---|---|
| **Wall-clock speed** | Within 20% of Claude Code on same model (parity, pure Python). | Faster than Claude Code on small tasks via optimized hot path. |
| **Token efficiency** | Same-model tasks use no more tokens than Claude Code. | Better than Cursor's reported overhead. |
| **Autonomy rate** | ≥ 80% of defined tasks in default mode complete without human intervention. | ≥ 90%. |
| **Recovery rate** | ≥ 90% of tool/model failures recovered without user action. | ≥ 95%. |
| **Safety** | Zero unintended destructive actions in default mode. All destructive actions logged and reversible. | Same. |
| **Cost predictability** | Budget caps fire before user-defined spend limits. Cost per task visible in real time. | Same. |
| **Setup time** | A new developer can run the hello-world test in < 10 minutes. | < 5 minutes. |

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Optimizing for speed hurts correctness. | Keep verification tools (tests, type checks, human review) configurable; never skip safety for speed. |
| API costs or rate limits stall long runs. | Budget caps, model cascading, prompt caching, and backoff/retry with checkpointing. |
| Sandbox escapes or destructive actions. | Isolated subprocess cwd, then Docker; approval gates; audit logs; reversibility via git/checkpoints. |
| Long-horizon context drift. | Memory compiler, periodic review loops, compacted summaries, and differential context. |
| Building too many features at once. | Phases are sequential. Phase 0 is the only active work until the hello-world test passes. |
| "Fastest" claim is hard to prove before shipping. | Speed-parity target for v0.1 (measurable). "Faster" target for v0.2 after profiling data exists. |
| Premature optimization kills the project. | No compiled extensions until benchmarks on a working system justify them. Profile first. |

---

## 13. Why This Is Not a Clone

Morgan is not a weaker version of Claude Code or a re-skin of OpenCode. It is a **persistent, autonomous, memory-first engineering harness** built on the open `deepagents` foundation. It borrows the best ideas from closed tools — Claude Code's tool depth and memory, Codex's background tasks, OpenCode's multi-provider flexibility, Cursor's speed awareness, and KiloCode's open-core model — and removes the structural bottlenecks that make them slow or closed.

The result is an open-source agent that can run a whole project on its own, with its speed limited by the model, not by the harness around it.

---

## 14. Sources & References

- [1] LangChain `open-swe` — open-source async coding agent with pluggable sandbox. https://github.com/langchain-ai/open-swe
- [2] Nimbalyst, "OpenCode vs Claude Code (2026)." https://nimbalyst.com/blog/opencode-vs-claude-code/
- [3] Reddit r/opencodeCLI, "How does OpenCode's harness compare to Codex?" https://www.reddit.com/r/opencodeCLI/comments/1t0nu99/how_does_opencodes_harness_compares_to_codex/
- [4] Nimbalyst, "OpenCode vs Codex vs Claude Code (2026 Comparison)." https://nimbalyst.com/blog/claude-code-vs-codex-vs-opencode-definitive-comparison/
- [5] Pinggy, "Top 5 CLI coding agents in 2026." https://pinggy.io/blog/top_cli_based_ai_coding_agents/
- [6] futureproofing.dev, "Cursor vs Claude Code 2026." https://www.futureproofing.dev/resources/ai-native-team/cursor-vs-claude-code-2026
- [7] Digital Applied, "Claude Code Leak: Agentic Architecture Lessons 2026." https://www.digitalapplied.com/blog/claude-code-leak-agentic-architecture-lessons-2026
- [8] vrungta, "Claude Code Architecture (Reverse Engineered)." https://vrungta.substack.com/p/claude-code-architecture-reverse
- [9] GitHub `openai/codex` issue #6404, "Background task management for Codex." https://github.com/openai/codex/issues/6404
- [10] KiloCode `AGENTS.md`. https://github.com/Kilo-Org/kilocode/blob/main/AGENTS.md
- [11] LangChain `deepagents`. https://github.com/langchain-ai/deepagents
