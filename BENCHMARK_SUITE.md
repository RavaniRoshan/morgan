# Benchmark Suite — Morgan

**Status:** Draft for v0.1  
**Date:** 2026-06-22  
**Scope:** Reproducible tasks, metrics, and comparison methodology used to prove Morgan’s speed and autonomy claims.

---

## 1. Overview

The Morgan benchmark suite measures two things:

1. **Speed:** how fast the harness completes a fixed task using the same model.
2. **Autonomy:** how often the harness completes a task without human intervention.

All benchmarks are public, reproducible, and version-controlled. The same task is run across Morgan, Claude Code, OpenCode, and OpenAI Codex CLI whenever possible, using the same model and the same starting workspace state.

---

## 2. Metrics

| Metric | Definition | Why it matters |
|---|---|---|
| **Wall-clock time** | Total time from prompt to final artifact. | The primary speed metric. |
| **Per-turn latency** | Median time for one model-call → tool-execution → result round trip. | Reveals harness overhead. |
| **Model calls** | Number of LLM API calls. | More calls = more latency and cost. |
| **Total tokens** | Input + output tokens. | Cost and context efficiency. |
| **Cached tokens** | Tokens served from provider prompt cache. | Caching efficiency. |
| **Cost** | Estimated dollar cost based on provider pricing. | Economic viability. |
| **Success rate** | % of runs that produce a correct, verifiable artifact. | Autonomy. |
| **Human interventions** | Number of approval prompts or clarifications needed. | Autonomy. |
| **Verification pass rate** | % of runs where the built-in verification passes. | Correctness. |

---

## 3. Task Taxonomy

| Level | Scope | Typical duration | Example |
|---|---|---|---|
| **Micro** | Single file, one command. | <1 minute | Create and run a hello-world script. |
| **Small** | One module + tests. | 1–5 minutes | Add a function and write tests for it. |
| **Medium** | Multi-file refactor. | 5–20 minutes | Split a script into a package and update callers. |
| **Large** | End-to-end project. | 20–120 minutes | Build a small web app from a PRD. |
| **Research** | Information synthesis. | 10–30 minutes | Research a topic and write a report. |

---

## 4. Canonical Tasks

### 4.1 Micro — Hello World

**ID:** `morgan-bench-hello`  
**Prompt:**

```text
Create a hello.py file that prints 'Hello from Morgan' and run it with python.
```

**Success criteria:**
- `hello.py` exists in the workspace.
- Running `python hello.py` outputs `Hello from Morgan`.

**Verification command:** `python hello.py`

---

### 4.2 Small — Calculator Module

**ID:** `morgan-bench-calc`  
**Prompt:**

```text
Create a calculator.py module with add, subtract, multiply, and divide functions. Write pytest tests for all four functions in tests/test_calculator.py. Run the tests and make sure they pass.
```

**Success criteria:**
- `calculator.py` exists with the four functions.
- `tests/test_calculator.py` exists with passing tests.
- `pytest tests/test_calculator.py` passes.

**Verification command:** `pytest tests/test_calculator.py`

---

### 4.3 Medium — Refactor Utils into Package

**ID:** `morgan-bench-refactor`  
**Starting state:** A single `utils.py` file with mixed functions for string manipulation, number operations, and file I/O. A `tests/test_utils.py` file that imports from `utils`.

**Prompt:**

```text
Refactor utils.py into a utils package with three modules: strings.py, numbers.py, and files.py. Update all imports in the codebase and ensure tests/test_utils.py still passes. Do not change function behavior.
```

**Success criteria:**
- `utils/__init__.py`, `utils/strings.py`, `utils/numbers.py`, `utils/files.py` exist.
- All functions are in the correct module.
- All imports across the codebase are updated.
- `pytest tests/test_utils.py` passes.

**Verification command:** `pytest tests/test_utils.py`

---

### 4.4 Large — Build a TODO Web App from PRD

**ID:** `morgan-bench-todo`  
**Starting state:** A PRD file at `examples/todo-app/PRD.md` describing a simple TODO app.

**Prompt:**

```text
Implement the TODO app described in examples/todo-app/PRD.md. The app should use FastAPI for the backend, serve an HTML frontend, and include pytest tests. Run the tests and verify the app starts.
```

**Success criteria:**
- The backend serves the frontend at the root path.
- Users can add, complete, and delete TODO items.
- `pytest examples/todo-app/` passes.
- The app starts without errors and responds to HTTP requests.

**Verification commands:**
- `pytest examples/todo-app/`
- `curl http://localhost:8000/health` returns 200 after startup.

---

### 4.5 Research — Vector Database Comparison

**ID:** `morgan-bench-research`  
**Prompt:**

```text
Research three vector databases suitable for small-scale RAG (e.g., Chroma, FAISS, LanceDB). Compare them on ease of use, performance, and deployment complexity. Write a 500-word Markdown report with sources to examples/research/report.md.
```

**Success criteria:**
- `examples/research/report.md` exists.
- Report is at least 500 words.
- Report has sections: introduction, comparison, recommendation, sources.
- Sources are listed with URLs.

**Verification:** Automated check of word count, sections, and source URLs.

---

## 5. Comparison Methodology

### 5.1 Baseline Tools

| Tool | Why include it |
|---|---|
| **Morgan** | The harness under test. |
| **Claude Code** | The fastest known closed-source harness; single-process architecture. |
| **OpenCode** | The leading open-source alternative; client-server architecture. |
| **OpenAI Codex CLI** | Sandbox-first, background-task model; strong safety defaults. |

### 5.2 Model Locking

- Where possible, use the **same model** across all harnesses (e.g., Claude Sonnet 4.6 or GPT-5.5).
- If a harness is model-locked, note it in the report and run the task with the closest available model.
- For Morgan, run the task with the same provider/model as the baseline for a fair comparison.

### 5.3 Statistical Method

- Run each task **N = 5 times** per harness.
- Report **median** and **P95** for wall-clock time and per-turn latency.
- Report **mean** for token counts and cost.
- Discard runs that fail due to external factors (e.g., network outage) and rerun them.

### 5.4 Workspace State

- Use a fresh workspace for each run.
- Use the same starting files, `.git` state, and `requirements.txt` for each harness.
- Fix the random seed or temperature where possible.

### 5.5 Human Intervention

- Record every approval prompt or clarification request.
- A run is considered **fully autonomous** if it completes without any human intervention.
- Runs requiring intervention are still measured, but marked as non-autonomous.

---

## 6. Reproducibility

- All benchmark tasks are stored in `benchmarks/tasks/` as JSON files.
- Each task JSON contains: `id`, `prompt`, `starting_files`, `expected_files`, `verification_commands`, `expected_outputs`.
- The runner is `benchmarks/runner.py` and is invoked with `python -m benchmarks.runner --task <id>`.
- Results are written to `benchmarks/results/<task>-<timestamp>.json`.
- A `requirements.txt` and `Dockerfile` are provided for the benchmark environment.

---

## 7. Reporting

Each benchmark run produces a JSON report with this structure:

```json
{
  "task_id": "morgan-bench-hello",
  "harness": "morgan",
  "model": "claude-sonnet-4.6",
  "timestamp": "2026-06-22T12:00:00Z",
  "wall_clock_ms": 4500,
  "per_turn_latency_ms": {
    "median": 320,
    "p95": 580
  },
  "model_calls": 8,
  "tokens": {
    "input": 12000,
    "output": 3500,
    "cached": 8000
  },
  "cost_usd": 0.12,
  "success": true,
  "autonomous": true,
  "verification_passed": true,
  "human_interventions": 0,
  "errors": []
}
```

---

## 8. Roadmap

- **Phase 0:** Implement the benchmark runner and the `hello` micro task.
- **Phase 2:** Add the `calculator` and `refactor` tasks; measure Docker overhead.
- **Phase 4:** Add the `todo-app` and `research` tasks; run cross-harness comparisons and publish results.
- **Post-v0.1:** Add community tasks, CI benchmark runs, and regression detection.

---

## 9. References

- OpenCode vs. Claude Code speed analysis: https://nimbalyst.com/blog/opencode-vs-claude-code/
- AutoAgents (Rust) vs. LangGraph benchmark: https://dev.to/saivishwak/benchmarking-ai-agent-frameworks-in-2026-autoagents-rust-vs-langchain-langgraph-llamaindex-338f
- Claude Code agent teams case studies: https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/guide/workflows/agent-teams.md
