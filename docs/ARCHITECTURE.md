# Morgan v0.1 Architecture

Morgan is a persistent, autonomous, memory-first engineering harness. 

## Key Layers

1. **Agent (Inner Loop)**: A LangChain-powered execution core that handles tool calling and error recovery.
2. **Conductor (Outer Loop)**: Decomposes goals into a YAML-frontmatter `PLAN.md`, then routes sequential and parallel tasks to the Agent.
3. **Memory System**:
   - Maintains working memory (`PLAN.md`, `NOTES.md`).
   - Recompiles learning periodically into `MORGAN.md` (conventions) using the `MemoryCompiler`.
4. **Router & Extensibility**: Intelligently routes LLM calls across providers (NVIDIA, Anthropic, OpenAI) while tracking strict financial budgets.
5. **Sandbox & Performance**:
   - Supports Local and Docker sandboxing for commands.
   - Applies zero-copy optimizations for massive tool outputs.
   - Provides MD5-based repository indices to keep context slim.
6. **Web Dashboard**: An asynchronous FastAPI + SSE UI for viewing agent progress.
