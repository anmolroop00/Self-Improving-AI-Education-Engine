"""Main entry point for the Self-Improving AI Education Engine."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agents.orchestrator import Orchestrator
from .config import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("ai_edu_engine")
app = typer.Typer(help="Self-Improving AI Education Engine CLI")
console = Console()


@app.command()
def run(
    topic: Optional[str] = typer.Option(None, help="Override topic to teach"),
    dry_run: bool = typer.Option(False, help="Generate content but don't produce video"),
    loop: bool = typer.Option(False, help="Run continuously (daily schedule)"),
):
    """Run the daily content pipeline."""
    orchestrator = Orchestrator()
    
    if loop:
        logger.info("Starting continuous loop mode...")
        # TODO: Implement scheduling logic
        logger.warning("Continuous loop not yet implemented, running once.")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task_id = progress.add_task("Running pipeline...", total=None)
        
        try:
            result = orchestrator.run_daily_pipeline(topic=topic, dry_run=dry_run)
            
            if result.success:
                progress.update(task_id, description="[green]Pipeline completed successfully![/green]")
                console.print("\n[bold green]SUCCESS![/bold green]")
                console.print(f"Lesson: {result.lesson.subtopic}")
                console.print(f"Script words: {result.lesson.word_count}")
                
                if result.final_video_path:
                    console.print(f"Video saved to: {result.final_video_path}")
            else:
                progress.update(task_id, description="[red]Pipeline failed[/red]")
                console.print(f"\n[bold red]FAILED:[/bold red] {result.error}")
                console.print(f"Failed at stage: {result.stage_reached}")
                
        except Exception as e:
            console.print_exception()
            sys.exit(1)


@app.command()
def optimize():
    """Run manual strategy optimization."""
    orchestrator = Orchestrator()
    console.print("[bold blue]Running strategy optimization...[/bold blue]")
    orchestrator.run_optimization_cycle()
    console.print("[green]Optimization cycle complete[/green]")


@app.command()
def status():
    """Show system status and curriculum progress."""
    orchestrator = Orchestrator()
    status = orchestrator.get_status()
    console.print(status)


@app.command()
def init():
    """Initialize system (create data dirs, verify keys)."""
    settings.ensure_directories()
    console.print("[green]Directories initialized[/green]")
    # TODO: explicit key verification


if __name__ == "__main__":
    app()
