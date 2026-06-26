"""Comprehensive tests for the morgan Agent class."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from morgan.agent import Agent
from morgan.config import Config


# ---------------------------------------------------------------------------
# Agent initialisation
# ---------------------------------------------------------------------------


class TestAgentInit:
    """Tests for Agent construction."""

    def test_init_default_config(self, workspace: Config) -> None:
        """Agent initialises with the provided config."""
        agent = Agent(config=workspace)
        assert agent.config is workspace
        assert agent.max_turns == workspace.max_turns

    def test_init_registers_tools(self, workspace: Config) -> None:
        """Agent registers native tools and get_time."""
        agent = Agent(config=workspace)
        assert agent.tools.get("get_time") is not None
        assert agent.tools.get("read_file") is not None
        assert agent.tools.get("write_file") is not None


# ---------------------------------------------------------------------------
# Agent.run — async tests
# ---------------------------------------------------------------------------


class TestAgentRun:
    """Tests for the Agent.run async method."""

    def test_run_hello_terminates(self, workspace: Config) -> None:
        """'hello' prompt produces a final answer without tool calls."""
        agent = Agent(config=workspace)
        messages, final_answer = asyncio.run(agent.run("hello"))
        assert isinstance(messages, list)
        assert isinstance(final_answer, str)
        assert len(final_answer) > 0
        # Should contain SystemMessage + HumanMessage + one AIMessage (no tool calls)
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        assert any(isinstance(m, HumanMessage) for m in messages)
        assert any(isinstance(m, AIMessage) for m in messages)
        # No tool messages expected for a simple hello
        assert not any(isinstance(m, ToolMessage) for m in messages)

    def test_run_time_prompt_calls_get_time(self, workspace: Config) -> None:
        """A time-related prompt triggers the get_time tool."""
        agent = Agent(config=workspace)
        messages, final_answer = asyncio.run(agent.run("What time is it?"))
        # Should have at least one ToolMessage from get_time
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        assert len(tool_msgs) >= 1
        # The tool result should look like a time string
        assert "on" in tool_msgs[0].content  # "HH:MM:SS on YYYY-MM-DD"
        # Final answer references the time
        assert "time" in final_answer.lower()

    def test_run_create_file_calls_write_then_bash(self, workspace: Config) -> None:
        """'create file' prompt triggers write_file then bash sequentially."""
        agent = Agent(config=workspace)
        messages, final_answer = asyncio.run(agent.run("create a file"))
        # Collect AIMessages with tool_calls
        ai_tool_msgs = [
            m for m in messages
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
        ]
        # Should have at least 2 tool-calling steps (write_file, bash)
        assert len(ai_tool_msgs) >= 2
        tool_names = [tc["name"] for m in ai_tool_msgs for tc in m.tool_calls]
        assert "write_file" in tool_names
        assert "bash" in tool_names
        # Verify the tool results came back successfully
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        assert len(tool_msgs) >= 2
        # The write_file result should confirm the write
        assert any("wrote" in m.content.lower() for m in tool_msgs)

    def test_run_returns_tuple(self, workspace: Config) -> None:
        """run() returns a (messages, final_answer) tuple."""
        agent = Agent(config=workspace)
        result = asyncio.run(agent.run("hello"))
        assert isinstance(result, tuple)
        assert len(result) == 2
        messages, final_answer = result
        assert isinstance(messages, list)
        assert isinstance(final_answer, str)


# ---------------------------------------------------------------------------
# max_turns enforcement
# ---------------------------------------------------------------------------


class TestAgentMaxTurns:
    """Tests for Agent max_turns enforcement."""

    def test_respects_max_turns(self, workspace: Config) -> None:
        """Agent stops after max_turns even if model keeps calling tools."""
        cfg = Config(workspace_dir=workspace.workspace_dir, max_turns=2)
        agent = Agent(config=cfg)
        # "create a file" normally takes 3 model calls (write → bash → done),
        # so capping at 2 should prevent the final "done" message.
        messages, final_answer = asyncio.run(agent.run("create a file"))
        # Count model turns (AIMessages)
        ai_msgs = [m for m in messages if isinstance(m, AIMessage)]
        assert len(ai_msgs) <= 2
