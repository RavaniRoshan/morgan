"""Morgan agent module — async agent loop with real LLM and tool support.

The agent loop calls a model, dispatches tool calls, feeds results back,
and repeats until the model issues a final response or ``max_turns`` is
reached.  When a provider API key is available, the loop uses a real LLM
via ``init_chat_model``; otherwise it falls back to a deterministic mock
model suitable for testing and development.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from morgan.config import Config, TrustMode
from morgan.tools import ToolRegistry, get_native_tools, get_time, think

logger = logging.getLogger("morgan.agent")

# ---------------------------------------------------------------------------
# System prompts — derived from PROMPT_LIBRARY.md
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are Morgan, a fully autonomous, speed-first software-engineering and research agent harness.

Your two edges:
1. Fully autonomous: You can decompose goals, research, design, write, test, review, and refactor on your own, with minimal human intervention.
2. Speed-first: You are the fastest agent harness. If a task fails, it should be because of model reasoning, not because of unnecessary overhead in the harness.

Core rules:
- Work inside the configured workspace directory. Never read or write files outside it unless explicitly approved.
- Use tools to act. Do not just describe what you would do.
- Prefer fast, local actions. Use the cheapest model band that can reliably complete a task; escalate only when needed.
- Keep the context window efficient. Do not re-read unchanged files.
- When you encounter an error, diagnose it, fix it, or escalate to the user with a clear summary.
- Respect the trust mode. If a tool call is blocked by policy, explain why and propose a safer alternative.
- Verify your work: run tests, linters, and the requested commands. Do not claim success unless verification passes.

Your mission is to turn the user's goal into a finished, verifiable artifact."""

TOOL_USE_PROMPT = """\
You have access to a set of tools. Use them to interact with the workspace and complete the task.

Tool-calling rules:
- Call exactly one tool at a time unless the tool supports parallel execution.
- Before editing a file, read it first or use search/grep to understand its contents.
- When you write a file, ensure the content is complete and syntactically valid.
- Use edit_file for small, targeted changes; use write_file for new files or wholesale rewrites.
- If a tool returns an error, do not immediately retry the same call. Diagnose the error and fix the underlying issue.
- For long-running commands (servers, tests, builds), use bash_background and bash_output rather than blocking the loop.
- Avoid loops: if you have made the same tool call twice without progress, stop and report the issue.

Error handling:
- Parse the error message carefully.
- Check file paths, dependencies, and environment state.
- Propose a concrete fix, not a description of the fix."""


# ---------------------------------------------------------------------------
# Mock model for testing / fallback
# ---------------------------------------------------------------------------


def _build_mock_model(native_tools: list[StructuredTool]):
    """Return a deterministic mock model for testing when no LLM key is set."""

    def model(messages: list) -> dict:
        tool_results = [m for m in messages if isinstance(m, ToolMessage)]
        first_user = next(
            (m for m in messages if isinstance(m, HumanMessage)), None
        )
        prompt = (
            first_user.content.lower()
            if first_user and isinstance(first_user.content, str)
            else ""
        )

        # ---------- Create + run a file ----------
        if ("create" in prompt or "make" in prompt) and "file" in prompt:
            wrote_file = any(
                "wrote" in t.content.lower() or "written" in t.content.lower()
                for t in tool_results
            )
            if not wrote_file:
                return {
                    "content": "Creating the file...",
                    "tool_calls": [
                        {
                            "name": "write_file",
                            "args": {
                                "path": "hello.py",
                                "content": "print('Hello from Morgan')",
                            },
                            "id": "call_write",
                        }
                    ],
                }
            ran_file = any(
                "Hello from Morgan" in t.content for t in tool_results
            )
            if not ran_file:
                return {
                    "content": "Running the file...",
                    "tool_calls": [
                        {
                            "name": "bash",
                            "args": {
                                "command": "python3 hello.py",
                                "timeout": 10,
                                "cwd": ".",
                            },
                            "id": "call_run",
                        }
                    ],
                }
            return {
                "content": f"Created hello.py and ran it. Output: {tool_results[-1].content}"
            }

        # ---------- Time query ----------
        if "time" in prompt or "current" in prompt:
            if not tool_results:
                return {
                    "content": "Checking the time...",
                    "tool_calls": [
                        {"name": "get_time", "args": {}, "id": "call_1"}
                    ],
                }
            return {"content": f"The current time is {tool_results[-1].content}."}

        # ---------- Hello ----------
        if "hello" in prompt and not tool_results:
            return {"content": "Hello! How can I help you today?"}
        if "final" in prompt or "done" in prompt:
            return {"content": "Done."}

        # ---------- Generic tool by name ----------
        tool_names = [t.name for t in native_tools]
        for tname in tool_names:
            if tname.replace("_", " ") in prompt or tname in prompt:
                if not tool_results:
                    return {
                        "content": f"Calling {tname}...",
                        "tool_calls": [
                            {"name": tname, "args": {}, "id": "call_1"}
                        ],
                    }
                return {
                    "content": f"Tool {tname} returned: {tool_results[-1].content}"
                }

        # ---------- Fallback ----------
        assistant_msgs = [m for m in messages if isinstance(m, AIMessage)]
        if assistant_msgs:
            return {"content": "Continuing..."}
        return {"content": "Mock response — no tools called"}

    return model


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class Agent:
    """Tool-calling agent loop.

    When a provider API key is available (e.g. ``OPENAI_API_KEY``,
    ``ANTHROPIC_API_KEY``), the loop uses a real LLM.  Otherwise it
    falls back to a deterministic mock model for development and testing.
    """

    def __init__(
        self,
        config: Config | None = None,
        tools: list[StructuredTool] | None = None,
        *,
        model_name: str | None = None,
    ) -> None:
        self.config = config or Config()
        self.tools = ToolRegistry()
        self.tools.register("get_time", get_time)
        self.tools.register("think", think)
        self.max_turns = self.config.max_turns
        self._native_tools = tools if tools is not None else get_native_tools(config=self.config)
        for t in self._native_tools:
            self.tools.register(t.name, t.func)

        from morgan.router import Router
        self.router = Router(config=self.config)
        self._model_name = model_name

        self._llm = self.router.get_model(self._model_name, tools=self._native_tools)
        if self._llm is None:
            logger.info("No LLM API key found; using mock model (development mode).")
            self._mock_model = _build_mock_model(self._native_tools)

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def _tool_dispatch(self, tool_call: dict) -> str:
        """Execute a single tool call and return the result string."""
        name = tool_call.get("name", "")
        args = tool_call.get("args", {})
        func = self.tools.get(name)
        if func is None:
            return f"Error: unknown tool '{name}'"
        try:
            result = func(**args)
            # If the function is a coroutine, await it
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self, prompt: str) -> tuple[list, str]:
        """Run the agent loop on *prompt* and return ``(messages, final_answer)``."""
        from morgan.index import RepoIndex
        
        repo_index = RepoIndex(config=self.config)
        repo_map = repo_index.get_repo_map()
        diff_context = repo_index.get_differential_context()
        
        system_content = (
            f"{SYSTEM_PROMPT}\n\n{TOOL_USE_PROMPT}\n\n"
            f"=== Repository Context ===\n{repo_map}\n\n"
            f"=== File Changes ===\n{diff_context}"
        )
        
        # Add standard caching headers for supported models
        system_msg = SystemMessage(
            content=system_content,
            additional_kwargs={"cache_control": {"type": "ephemeral"}}
        )
        
        messages: list = [
            system_msg,
            HumanMessage(content=prompt),
        ]
        turns = 0

        while turns < self.max_turns:
            turns += 1

            if self._llm is not None:
                # ---- Real LLM path ----
                response = await self._llm.ainvoke(messages)
                messages.append(response)

                # Check for tool calls
                if hasattr(response, "tool_calls") and response.tool_calls:
                    for tc in response.tool_calls:
                        result = await self._tool_dispatch(tc)
                        messages.append(
                            ToolMessage(
                                content=result,
                                tool_call_id=tc.get("id", f"call_{turns}"),
                            )
                        )
                    continue

                # No tool calls → final answer
                break
            else:
                # ---- Mock model path ----
                response = self._mock_model(messages)
                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])

                if tool_calls:
                    messages.append(
                        AIMessage(content=content, tool_calls=tool_calls)
                    )
                    for tc in tool_calls:
                        result = await self._tool_dispatch(tc)
                        messages.append(
                            ToolMessage(
                                content=result,
                                tool_call_id=tc.get("id", "call_1"),
                            )
                        )
                    continue

                # No tool calls → final answer
                messages.append(AIMessage(content=content))
                break

        # Extract final answer (last AIMessage)
        final_answer = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_answer = msg.content
                break

        return messages, final_answer
