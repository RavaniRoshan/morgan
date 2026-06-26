# Architecture Decision Record — Morgan

**Status:** Draft for v0.1  
**Date:** 2026-06-22  
**Scope:** High-impact architectural decisions required before building Morgan v0.1

---

## Summary

Morgan is a fully autonomous, low-overhead software engineering and research agent harness. This document records the major architectural decisions made before v0.1, the rationale behind them, and the open risks that must be validated during the build.

---

## ADR-001: Runtime — Pure Python; profile before optimizing

### Context

The tight agent loop (model call → tool dispatch → tool execution → result serialization) is where most harness overhead lives. Two approaches exist: (a) pure Python with structural optimizations, or (b) a compiled hot loop (Rust via PyO3) for lower-level dispatch speed.

Key benchmarks exist showing Rust agent frameworks (AutoAgents, OpenFANG) with 40–80% lower latency than LangGraph. These numbers are real. The question is whether they are relevant to Morgan's bottleneck.

**The actual bottleneck analysis:**

On a typical coding agent task (write a module + tests), wall-clock time breaks down as:
- Model API wait time: **65–80%** of total
- Tool execution (file I/O, subprocess): **10–20%**
- Python orchestration (LangGraph dispatch, serialization): **5–15%**

A 2× speedup on 10% of runtime = 5% total improvement. A 43.7% faster Python orchestration layer (matching the AutoAgents benchmark gap) on 10% of runtime = 4.4% total improvement. Neither justifies a two-language build.

The real speed wins are:
- Differential context (only changed files): reduces input tokens → reduces model call latency
- Prompt caching: reduces time-to-first-token by 50–90% on stable prefixes
- Parallel sub-agents: runs independent tasks concurrently, reduces wall-clock time proportional to parallelizable work
- Model cascading: routes cheap tasks to fast/cheap models, expensive tasks to frontier models
- Fewer model calls: better planning means fewer round trips

All of these are achievable in pure Python.

### Decision

- **Morgan v0.1 and v0.2 are pure Python.** No Rust, no PyO3, no compiled extensions.
- Build Phase 0 → measure → profile with real tasks → identify real bottlenecks.
- If post-v0.1 benchmarks show Python loop overhead > 15% of total wall-clock time **after applying all pure-Python optimizations above**, open a new ADR for hot-loop optimization at that point.
- Until that evidence exists, a compiled hot loop is speculative optimization of a system that doesn't exist yet.

### Rationale

- Eliminates two-language build complexity, PyO3 bridge overhead, and Rust CI from a project that has zero working code today.
- The AutoAgents/LangGraph benchmark measures full-framework routing tasks — not LLM-tool-call-LLM cycles. The bottleneck profile is different.
- Python gives us LangGraph, LangChain, deepagents, and the full ML ecosystem without compromise.
- Speculative optimization before profiling is the most common cause of over-engineered, unshippable agent projects.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Rust hot loop + Python orchestration (hybrid)** | Justified by benchmarks that measure the wrong bottleneck. Bridge overhead partially cancels the gain. Adds two-language build before v0.1 exists. Deferred to post-v0.2 if profiling data justifies it. |
| **Pure Rust** | Maximum runtime performance, but loses deepagents, LangGraph, and Python ML ecosystem. v0.1 would take months longer. |
| **TypeScript/Node** | Matches Claude Code's single-process architecture, but loses deepagents, LangGraph, and Python-first AI ecosystem. |
| **Go** | Fast and good at async; weaker ML/agent tooling; would require building many primitives from scratch. |

### Consequences

- Speed parity with Claude Code (within 20%) is the v0.1 target, not "faster than Claude Code."
- After v0.1, run the benchmark suite. If data shows Python overhead > 15% of wall-clock time, open ADR-001-v2 for hot-loop optimization.
- "Fastest harness" framing shifts to: fastest to autonomy (fewest human interventions per completed task), not fastest raw loop.

---

## ADR-002: Architecture — Single in-process CLI

### Context

OpenCode is community-led, MIT-licensed, and supports 75+ model providers, but it pays a heavy speed tax for its architecture. Its Go-based TUI talks over HTTP to a Bun/JavaScript server, and even on `localhost` every tool call pays a network hop. Builder.io head-to-head tests found OpenCode to be **~78% slower overall** than Claude Code on the same model, with much of the gap coming from client-server overhead [5]. Claude Code, by contrast, is a single TypeScript process where the harness, CLI, and model orchestration live together.

### Decision

- The **core Morgan harness** is a single in-process CLI.
- The loop, tool registry, model router, and memory manager live in the same process.
- A web UI or remote daemon may be added later (Phase 5), but it must connect to the engine via **shared memory, an event bus, or a lightweight IPC** — not a per-tool HTTP hop.

### Rationale

- Eliminates per-turn network overhead — the primary source of OpenCode's 78% slowdown.
- Matches the architecture of the fastest closed-source harness (Claude Code).
- Keeps initial design simple; avoids premature distributed-system complexity.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Client-server by default** | Adds per-tool latency, as shown by OpenCode's 78% slowdown. |
| **Thin CLI + remote daemon** | Useful for managed cloud, but not for the local v0.1 target. |
| **Engine in cloud, CLI thin** | Network latency makes speed parity impossible. |

### Consequences

- Multi-session orchestration and remote monitoring require a later optional layer.
- UI updates must be non-blocking and event-driven.
- The CLI process must handle long-running background tasks without freezing.

---

## ADR-003: Sandbox — subprocess (Phase 0), Docker / devcontainer (Phase 2), microVMs (post-v0.1)

### Context

Autonomous coding agents write code, run shell commands, install dependencies, and sometimes access the network. Without isolation, mistakes or malicious generated code can damage the host. Sandboxing is mandatory, but the choice of sandbox technology is a trade-off between speed, isolation, and operational complexity.

Key data points:
- Docker Sandboxes with microVM-based isolation can reduce permission prompts by **84%** while maintaining productivity [6].
- **Firecracker** microVMs boot in **~125 ms** with **<5 MB** overhead and provide hardware-level isolation [7].
- Plain Docker containers share the host kernel; security analysis recommends gVisor or Kata/Firecracker for high-risk AI-agent workloads [8].
- Docker rebuilt its sandbox architecture around microVMs because "if the sandbox is slow, developers skip it" [9].

### Decision

- **Phase 0 sandbox:** Local subprocess with strict `cwd` restriction and `PATH` allowlist. Fast, zero setup, good enough for development.
- **Phase 2 sandbox:** Docker / devcontainer running as a non-root user. Default for all runs.
- **Pluggable provider model:** `sandbox.py` exposes a `SandboxProvider` interface with adapters for subprocess, Docker, and cloud.
- **Post-v0.1:** microVM-backed providers (Kata, gVisor, Firecracker) for high-risk production deployments.

### Rationale

- Subprocess sandbox is zero-friction for Phase 0, letting the loop prove itself before adding Docker overhead.
- Docker/devcontainer is reproducible, widely available, and fits developer workflows.
- A pluggable provider model lets users upgrade isolation without rewriting the harness.
- MicroVMs are the future, but Docker is sufficient for v0.1 validation.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Docker from Phase 0** | Adds setup friction and cold-start latency before the loop works. Phase 0 goal is hello-world, not isolation. |
| **MicroVM by default** | Stronger isolation, but higher operational complexity for v0.1. |
| **Cloud sandbox by default** | Adds network latency; makes speed-parity claim hard to prove. |

### Consequences

- Docker overhead must be measured in Phase 2 and minimized.
- Users without Docker must run in subprocess mode with hard warnings and limited trust mode.
- The `SandboxProvider` interface must be stable enough to swap adapters without touching the agent loop.

---

## ADR-004: Model Provider — OpenAI, Anthropic, OpenRouter by default

### Context

OpenCode supports 75+ providers via Models.dev and custom OpenAI-compatible endpoints. Supporting that breadth in v0.1 would drown the project in provider-specific integration work. The three most common provider families users ask for are OpenAI (GPT), Anthropic (Claude), and OpenRouter (aggregated open-source and alternative models).

### Decision

- **v0.1 supports three providers out of the box:** OpenAI, Anthropic, and OpenRouter.
- Each provider is configured via environment variables and a JSON config file (`~/.morgan/providers.json` or project-level config).
- **Custom OpenAI-compatible endpoints** can be added later by extending the provider schema.
- Model routing starts as manual selection (`--model`, `--provider`, or config). Smart routing (fast/reasoning/speculative bands) is added in **Phase 3** (Weeks 6–7).

### Rationale

- Covers the majority of users and use cases without the complexity of a full catalog.
- OpenRouter provides access to experimental models without custom integrations.
- Anthropic and OpenAI are the most reliable for tool calling today.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Single provider only** | Too restrictive; contradicts the open, multi-provider philosophy. |
| **75+ providers from day one** | Too much integration, testing, and maintenance for v0.1. |
| **Local-only models first** | Local models are not yet strong enough for reliable coding tasks. |

### Consequences

- OpenRouter model quality and tool-calling reliability vary widely; we must test and whitelist reliable models.
- We need provider-specific logic for token counting, pricing, and prompt caching.
- Smart routing will require a per-task complexity estimator and validation step.

---

## ADR-005: Tool Execution — Capability-based routing

### Context

Not all tools are equally dangerous. A `read_file` tool is safe; a `bash` tool can delete the host; an MCP tool can do anything its server exposes. Claude Code's Auto Mode uses a risk classifier to auto-approve safe actions and escalate risky ones. Real incidents such as the Langflow CVE-2025-3248 RCE and Cursor MCP RCE show that uncontrolled tool execution is a serious risk [8].

### Decision

- Every tool is classified by risk category: `read`, `write`, `shell`, `network`, `git`, `meta`, `agent`.
- **Safe tools** (`read`, some `meta`) run in-process.
- **Risky tools** (`write`, `shell`, `network`, `git`, `agent`) run in the sandbox and are routed through the approval/policy engine.
- **Trust modes** govern execution:
  - **Default / Fast:** auto-approve `read` and low-risk `meta`; ask for `write`, `shell`, `network`, `git`.
  - **Safe:** ask for every `write` and `shell` call.
  - **Full Access:** bounded autonomous run with hard caps, tool allowlist, and sandbox; no interactive approval.
- **MCP tools** are treated as risky until explicitly classified and added to an allowlist.

### Rationale

- Balances speed and safety.
- Matches the user's expectation of mode-dependent behavior.
- Avoids the Cursor MCP security mistake by not trusting external tools blindly.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **All tools in-process** | Fastest, but unsafe for shell and network. |
| **All tools in sandbox** | Maximum isolation, but adds overhead to every file read. |
| **Model decides safety** | Too unreliable; safety must be a hard policy, not a model judgment. |

### Consequences

- Need a clear risk matrix and approval queue CLI.
- Policy engine must be version-controlled, auditable, and testable.
- Each tool must be instrumented for audit logging.

---

## ADR-006: Memory / Context — Hybrid (recent full + summarized/retrieved + prompt caching)

### Context

Context windows are growing but remain expensive and slow. A naive approach that resends the entire repo and full conversation history every turn wastes tokens and latency. Prompt caching reduces cost and time-to-first-token by reusing stable prompt prefixes [17].

### Decision

- **Working memory:** Keep recent conversation history full up to a token budget.
- **Compaction:** Periodically summarize older turns and append the summary to the transcript (append-only).
- **Differential context:** Use a file hash cache to include only changed files; unchanged files referenced by path or hash.
- **Retrieval:** Vector + BM25 retrieval over memory files, repo index, and documentation. *(Phase 1+)*
- **Prompt caching:** Keep system prompt segments and tool schemas stable to maximize provider prompt-cache hits.

### Rationale

- Minimizes tokens per turn while preserving critical context.
- Retrieval handles large repos; full context handles recent work.
- Prompt caching is a major speed and cost win — often the single biggest lever.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Full history always** | Simple, but context and cost grow unbounded. |
| **RAG only** | Retrieval can miss context needed for multi-file reasoning. |
| **Compaction only** | Loses detail; retrieval is needed for precise lookups. |

### Consequences

- Need a memory compiler and retrieval-quality monitoring.
- Risk of retrieval missing context; mitigate with a "working set" of recent edits, open files, and the current plan.
- Must design stable system prompt segments to maximize cache hits.

---

## ADR-007: Sub-agents — Parallel sub-agents with conductor orchestration

### Context

Claude Code offers two multi-agent patterns: **sub-agents** (ephemeral, focused workers that return summaries to the parent) and **agent teams** (persistent, specialized agents that communicate directly). Sub-agents are best for independent parallel work; agent teams are best for collaborative tasks requiring negotiation. Practitioner reports claim **2× execution speed** with agent teams and **50% faster** code review with parallel scope-focused sub-agents [18][19][20].

### Decision

- Implement a **conductor** that can spawn **parallel sub-agents** for independent tasks.
- Sub-agents have isolated context windows, defined tool subsets, and return structured summaries.
- **Agent teams** are out of scope for v0.1; they may be added later for complex collaborative workflows.
- Work should be split by **context/task**, not by role, to avoid handoff degradation.

### Rationale

- Parallel sub-agents improve speed and keep the parent context clean.
- Simpler than full agent teams for v0.1.
- Proven by real-world Claude Code deployments.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Single agent, many tools** | Simpler but serial and limited by one context window. |
| **Sequential sub-agents** | Cleaner but slower; parallelism is key to the speed edge. |
| **Agent teams in v0.1** | Too complex; inter-agent communication and state management are a later concern. |

### Consequences

- Need dependency resolution, result synthesis, and concurrency limits.
- Over-decomposition can hurt; the conductor must decide when to parallelize and when to stay in the main loop.

---

## ADR-008: Safety — Mode-dependent trust policy

### Context

Claude Code's default mode is safe but interrupt-heavy; `--dangerously-skip-permissions` is convenient but unsafe outside sandboxes. Anthropic introduced Auto Mode to close the gap, using a classifier to auto-approve low-risk actions while blocking things like `curl | bash`, production deploys, and force-pushes to `main` [13]. The gap between "too many prompts" and "no prompts at all" is where Morgan's mode-dependent design lives.

### Decision

- Implement three trust modes, each as a version-controlled policy file:
  - **Default / Fast:** auto-approve low-risk actions; escalate high-risk or ambiguous actions for approval.
  - **Safe:** require explicit approval for every `write` and `shell` call.
  - **Full Access:** no interactive approval; runs within a strict policy (tool allowlist, max steps, max cost, max time, sandbox) with full audit logging.
- The policy engine evaluates every tool call before execution.
- Users can override per-tool or per-project rules via `MORGAN.md` or `morgan.json`.

### Rationale

- Gives users explicit speed/safety trade-offs.
- Keeps safety mandatory while allowing speed optimization inside boundaries.
- Matches the two product edges.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Speed first, safety later** | Too risky; safety incidents would destroy trust. |
| **Safety first, speed later** | Would fail to prove the speed edge. |
| **Single mode with manual overrides** | Less flexible than explicit modes. |

### Consequences

- The policy engine must be robust, auditable, and fast.
- The default-mode risk classifier must be well-tuned; if too conservative, it feels like safe mode; if too permissive, it becomes bypass mode.
- Every tool call is logged with mode, policy outcome, and user action.

---

## Open Risks & Validation Spikes

| Spike | Question | Target Phase |
|---|---|---|
| **Docker overhead** | How much latency does Docker add per tool call vs. subprocess? | Phase 2 |
| **Provider tool-calling** | Which OpenRouter models reliably support tool calling? | Phase 3 |
| **Retrieval quality** | Does hybrid retrieval match or beat full-context baselines on coding tasks? | Phase 1 / Phase 4 |
| **Risk classifier** | Can a simple policy engine match Claude Code Auto Mode's approval behavior? | Phase 0 / Phase 1 |
| **Python loop overhead** | After all pure-Python optimizations, what % of wall-clock time is Python overhead? | Phase 2 / Phase 4 — **gate for any future hot-loop ADR** |

---

## References

1. AutoAgents (Rust) vs. LangGraph benchmark: https://dev.to/saivishwak/benchmarking-ai-agent-frameworks-in-2026-autoagents-rust-vs-langchain-langgraph-llamaindex-338f
2. OpenFANG Rust agent OS benchmarks: https://www.sitepoint.com/openfang-rust-agent-os-performance-benchmarks/
3. Claw Code hybrid Python/Rust architecture: https://claw-code.codes/architecture.html
4. Red Hat: moving hot paths from Python to Rust: https://developers.redhat.com/articles/2025/09/15/why-some-agentic-ai-developers-are-moving-code-python-to-rust
5. OpenCode vs. Claude Code speed analysis: https://nimbalyst.com/blog/opencode-vs-claude-code/
6. Docker Sandboxes for Claude Code: https://www.mintmcp.com/blog/sandbox-claude-code
7. Sandbox technology feature matrix: https://github.com/restyler/awesome-sandbox
8. Why Docker alone is not enough for AI agents: https://www.softwareseni.com/ai-agent-sandboxing-explained-why-docker-is-not-enough-and-what-actually-works/
9. Docker microVM architecture: https://www.docker.com/blog/why-microvms-the-architecture-behind-docker-sandboxes/
10. OpenCode providers: https://open-code.ai/en/docs/providers
11. OpenCode multi-provider model routing: https://help.apiyi.com/en/opencode-api-proxy-configuration-guide-en.html
12. Claude Code Auto Mode: https://productivetechtalk.com/2026/03/28/claude-code-auto-mode-smarter-permissions-for-devs/
13. Claude Code Auto Mode deep dive: https://blog.laozhang.ai/en/posts/claude-code-auto-mode
14. OpenClaw context management: https://github.com/JnBrymn/openclaw/issues/2
15. Context engineering guide: https://qubittool.com/blog/context-engineering-complete-guide
16. Cache-Augmented Generation vs. RAG: https://www.prompthub.us/blog/retrieval-augmented-generation-vs-cache-augmented-generation
17. Prompt caching overview: https://www.ibm.com/think/topics/prompt-caching
18. Claude Code sub-agents vs. agent teams: https://www.reddit.com/r/ClaudeCode/comments/1rumv62/claude_subagents_vs_agent_teams_explained_simply/
19. Claude Code agent teams docs: https://code.claude.com/docs/en/agent-teams
20. Agent teams case studies: https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/guide/workflows/agent-teams.md
