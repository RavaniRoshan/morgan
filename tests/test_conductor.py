"""Tests for the conductor module."""

import asyncio
from morgan.config import Config
from morgan.conductor import Conductor

def test_conductor_decompose_fallback(workspace: Config) -> None:
    """Test decompose falls back to a single task if no LLM is available."""
    conductor = Conductor(config=workspace)
    # The agent mock model is not used for decomposition (it checks for _llm)
    # So it should fall back to ["Complete the goal."]
    tasks = asyncio.run(conductor.decompose("build a game"))
    assert tasks == ["Complete the goal."]

def test_conductor_run_creates_plan(workspace: Config) -> None:
    """Test that run creates a PLAN.md and executes the task."""
    conductor = Conductor(config=workspace)
    
    # Since there's no LLM, it will decompose to "Complete the goal."
    # Then it delegates to Agent. The mock agent should return a generic response.
    summary = asyncio.run(conductor.run("test goal"))
    
    assert "Conductor finished executing goal: test goal" in summary
    
    # Check that PLAN.md was created and updated
    plan_content = conductor.memory.read("PLAN.md")
    assert "status: completed" in plan_content
    assert "- [x] Complete the goal." in plan_content
    
    # Check that NOTES.md was NOT updated since no LLM is available
    notes_content = conductor.memory.read("NOTES.md")
    assert "Lessons from 'test goal'" not in notes_content
    
    # Check that summary mentions the fallback message
    assert "No LLM available" in summary
