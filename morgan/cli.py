"""Morgan CLI - terminal interface for the agent."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import rich
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
import typer
from pydantic import ValidationError

from morgan.agent import Agent
from morgan.config import Config, TrustMode

console = Console()
app = typer.Typer(
    name="morgan",
    help="AI agent with file and shell tools",
    epilog="Run without a prompt to enter interactive REPL mode",
)


def load_config(trust_mode: Optional[str] = None) -> Config:
    """Load configuration from environment or defaults."""
    try:
        workspace_dir = Path("workspace")

        if workspace_dir.exists():
            config = Config(
                workspace_dir=workspace_dir,
                trust_mode=TrustMode(trust_mode or "default"),
            )
        else:
            config = Config(trust_mode=TrustMode(trust_mode or "default"))
            console.print(
                f"[yellow]Creating workspace at: {config.workspace_dir}[/yellow]"
            )
            config.workspace_dir.mkdir(exist_ok=True)

        return config

    except (ValueError, ValidationError) as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        return Config()


@app.command()
def morgan(
    prompt: Optional[str] = typer.Argument(
        None, help="User prompt for the agent"
    ),
    trust_mode: Optional[str] = typer.Option(
        None,
        "--trust-mode",
        "-t",
        help="Trust mode: default, safe, or full-access",
        case_sensitive=False,
        callback=lambda v: TrustMode(v) if v else None,
    ),
):
    """Run the Morgan agent.

    The agent will process your prompt using available tools and return the final response.
    """
    config = load_config(trust_mode)

    if not prompt:
        # Interactive REPL mode
        console.print("[bold green]Morgan Agent REPL[/bold green]")
        console.print("Type your prompts or 'exit' to quit:\n")
        console.print("[dim]Example: 'create a hello.txt file with content \"Hello World\"'[/dim]\n")

        while True:
            user_input = Prompt.ask("[cyan]You[/]").strip()

            if not user_input or user_input.lower() in {"exit", "quit", "q"}:
                console.print("\n[green]Goodbye![/green]")
                break

            try:
                asyncio.run(run_agent_with_prompt(config, user_input))
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        return

    # Run agent with provided prompt
    asyncio.run(run_agent_with_prompt(config, prompt))


async def run_agent_with_prompt(config: Config, prompt: str) -> None:
    """Run the agent and display the response."""
    from morgan.conductor import Conductor
    conductor = Conductor(config=config)

    try:
        console.print(f"\n[bold yellow]Prompt:[/bold yellow] {prompt}")
        console.print("[bold green]Morgan:[/bold green] Processing...\n")

        final_answer = await conductor.run(prompt)

        console.print("[bold green]=== FINAL RESPONSE ===[/bold green]\n")
        if final_answer:
            if "```" in final_answer or final_answer.startswith("#"):
                console.print(Markdown(final_answer))
            else:
                console.print(final_answer)

        console.print("\n[dim]Run completed successfully.[/dim]\n")

    except Exception as e:
        console.print(f"[red]Agent error: {e}[/red]")
        raise


if __name__ == "__main__":
    app()
