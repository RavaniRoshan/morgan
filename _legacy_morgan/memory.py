"""Morgan memory module — memory compiler + .md file manager."""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.messages import BaseMessage

from morgan.config import Config

logger = logging.getLogger("morgan.memory")

class Memory:
    """Read and write memory files (PLAN.md, NOTES.md, etc.) in the workspace."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.workspace_dir = self.config.workspace_dir

    def init(self) -> None:
        """Initialize default memory files if they don't exist."""
        plan_path = self.workspace_dir / "PLAN.md"
        notes_path = self.workspace_dir / "NOTES.md"

        if not plan_path.exists():
            plan_path.write_text(
                "---\nstatus: pending\n---\n# Plan\n\nNo active plan.\n",
                encoding="utf-8"
            )
            logger.info("Initialized PLAN.md")

        if not notes_path.exists():
            notes_path.write_text(
                "# Memory & Notes\n\nPersistent knowledge and lessons learned across sessions.\n",
                encoding="utf-8"
            )
            logger.info("Initialized NOTES.md")

    def read(self, name: str) -> str:
        """Read a memory file by name (e.g. 'PLAN.md') and return its content."""
        path = self.workspace_dir / name
        if not path.is_file():
            return f"Error: Memory file '{name}' does not exist."
        return path.read_text(encoding="utf-8")

    def write(self, name: str, content: str) -> None:
        """Write *content* to a memory file identified by *name*."""
        path = self.workspace_dir / name
        path.write_text(content, encoding="utf-8")

    def get_frontmatter(self, name: str) -> dict[str, str]:
        """Extract basic YAML frontmatter from a memory file if present."""
        content = self.read(name)
        if content.startswith("Error:"):
            return {}
        
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}
        
        frontmatter = {}
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                break
            if ":" in line:
                k, v = line.split(":", 1)
                frontmatter[k.strip()] = v.strip()
        return frontmatter


class MemoryCompiler:
    """Compiles session transcripts into long-term lessons in NOTES.md."""

    def __init__(self, memory: Memory, config: Config | None = None) -> None:
        self.memory = memory
        self.config = config or Config()

    async def compile_memory(self, goal: str, messages: list[BaseMessage]) -> str:
        """Extract lessons from the session and update NOTES.md.
        
        Since this runs asynchronously at the end of a session, it uses the 
        fastest/cheapest model available to summarize what was learned.
        """
        # We will use the same LLM detection logic as Agent, or ideally a cheaper tier
        from morgan.agent import Agent
        
        # Instantiate an agent just to borrow its LLM 
        agent = Agent(config=self.config)
        llm = agent._llm
        if not llm:
            logger.warning("No LLM available to compile memory.")
            return "No LLM available."

        # Simplify the conversation transcript
        transcript_lines = []
        for msg in messages:
            role = msg.type
            content = str(msg.content)[:500]  # truncate huge outputs
            if content.strip():
                transcript_lines.append(f"{role.upper()}: {content}")
                
        transcript = "\n".join(transcript_lines)

        prompt = (
            "You are the Morgan memory compiler. Your job is to extract key architectural "
            "decisions, rules, preferences, and lessons learned from the following session "
            "transcript and formulate them into a concise set of notes. Do not include trivial "
            "details or code snippets unless they are important patterns.\n\n"
            f"Goal: {goal}\n\n"
            f"Transcript:\n{transcript}\n\n"
            "Respond with only the markdown notes to append to NOTES.md."
        )

        try:
            # We don't need tool binding for this LLM call
            from langchain_core.messages import HumanMessage
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            new_notes = response.content.strip()
            
            if new_notes:
                current_notes = self.memory.read("NOTES.md")
                if current_notes.startswith("Error:"):
                    current_notes = "# Memory & Notes\n"
                    
                updated_notes = f"{current_notes}\n\n## Lessons from '{goal}'\n{new_notes}\n"
                self.memory.write("NOTES.md", updated_notes)
                logger.info("NOTES.md updated with compiled memory.")
                return new_notes
            return "No notes generated."
        except Exception as e:
            logger.error("Failed to compile memory: %s", e)
            return f"Error: {e}"
