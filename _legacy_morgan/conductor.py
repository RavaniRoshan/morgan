"""Morgan conductor module — long-horizon planning + orchestration."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from morgan.agent import Agent
from morgan.config import Config
from morgan.memory import Memory, MemoryCompiler

logger = logging.getLogger("morgan.conductor")

class Conductor:
    """Plans and orchestrates multi-step tasks, spawning sub-agents as needed."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.memory = Memory(config=self.config)
        self.memory_compiler = MemoryCompiler(memory=self.memory, config=self.config)
        
        # We instantiate a base agent for LLM access during decomposition
        self._base_agent = Agent(config=self.config)

    async def decompose(self, goal: str) -> list[str]:
        """Use an LLM to decompose the goal into high-level tasks."""
        if not self._base_agent._llm:
            logger.warning("No LLM available for task decomposition. Falling back to a single task.")
            return ["Complete the goal."]

        system_prompt = (
            "You are the Morgan Conductor. Break down the user's goal into a logical, "
            "sequential list of high-level tasks. Focus on architecture, implementation, "
            "and verification. Output ONLY a bulleted list of tasks, one per line. "
            "If multiple tasks can be safely executed concurrently without depending on "
            "each other, prefix them with '[parallel]'. Do not number them."
        )
        
        try:
            response = await self._base_agent._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Goal: {goal}")
            ])
            tasks = [t.strip().lstrip("-* ").strip() for t in response.content.splitlines() if t.strip()]
            return tasks if tasks else ["Complete the goal."]
        except Exception as e:
            logger.error("Decomposition failed: %s", e)
            return ["Complete the goal."]

    async def run(self, goal: str) -> str:
        """Decompose *goal* into a plan, execute it, and return a summary."""
        self.memory.init()
        
        # Check if there is already an active plan
        frontmatter = self.memory.get_frontmatter("PLAN.md")
        if frontmatter.get("status") == "in_progress":
            logger.info("Resuming existing plan.")
        else:
            logger.info("Creating new plan for goal: %s", goal)
            tasks = await self.decompose(goal)
            
            new_frontmatter = "---\nstatus: in_progress\ngoal_id: current\n---\n"
            content = f"# Goal\n\n{goal}\n\n## Tasks\n\n"
            for t in tasks:
                content += f"- [ ] {t}\n"
            
            self.memory.write("PLAN.md", new_frontmatter + content)

        # Execution loop
        max_tasks = 20
        task_count = 0
        all_messages = []
        import asyncio
        
        while task_count < max_tasks:
            plan_content = self.memory.read("PLAN.md")
            lines = plan_content.splitlines()
            
            parallel_group = []
            
            for i, line in enumerate(lines):
                if line.strip().startswith("- [ ]"):
                    task_str = line.strip()[5:].strip()
                    if task_str.startswith("[parallel]"):
                        parallel_group.append((i, task_str))
                    else:
                        if not parallel_group:
                            parallel_group.append((i, task_str))
                        break

            if not parallel_group:
                logger.info("No more uncompleted tasks found.")
                break
                
            task_count += len(parallel_group)
            
            if len(parallel_group) == 1:
                idx, task = parallel_group[0]
                logger.info("Executing task: %s", task)
                agent = Agent(config=self.config)
                prompt = f"Goal: {goal}\n\nCurrent Task: {task}\n\nPlease complete this task."
                messages, _ = await agent.run(prompt)
                all_messages.extend(messages)
                lines[idx] = lines[idx].replace("- [ ]", "- [x]", 1)
            else:
                logger.info("Executing %d parallel tasks.", len(parallel_group))
                
                async def _run_agent(t: str) -> list:
                    agent = Agent(config=self.config)
                    prompt = f"Goal: {goal}\n\nCurrent Task: {t}\n\nPlease complete this task."
                    msgs, _ = await agent.run(prompt)
                    return msgs
                
                results = await asyncio.gather(*[_run_agent(t) for _, t in parallel_group])
                for msgs in results:
                    all_messages.extend(msgs)
                
                for idx, _ in parallel_group:
                    lines[idx] = lines[idx].replace("- [ ]", "- [x]", 1)
            
            self.memory.write("PLAN.md", "\n".join(lines) + "\n")
            
        # Update plan status to completed
        plan_content = self.memory.read("PLAN.md")
        plan_content = plan_content.replace("status: in_progress", "status: completed")
        self.memory.write("PLAN.md", plan_content)
        
        # Compile memory
        logger.info("Compiling memory for the session.")
        notes = await self.memory_compiler.compile_memory(goal, all_messages)
        
        return f"Conductor finished executing goal: {goal}\n\nLessons Learned:\n{notes}"
