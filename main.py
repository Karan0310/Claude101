#!/usr/bin/env python3
"""
Resume-Job Matcher Agent — CLI Entry Point

Usage:
  python main.py analyze <resume_file>
  python main.py analyze <resume_file> --location "New York" --max-results 10
  python main.py web
"""
import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich import box

from agent.orchestrator import ResumeJobMatcherAgent
from agent.feedback_loop import format_evaluation_report
from models.schemas import FeedbackRating, SearchRequest, UserFeedback

console = Console()


def fit_color(score: float) -> str:
    if score >= 85:
        return "bright_green"
    elif score >= 70:
        return "green"
    elif score >= 50:
        return "yellow"
    elif score >= 30:
        return "dark_orange"
    return "red"


def fit_label(score: float) -> str:
    if score >= 85:
        return "Excellent Match"
    elif score >= 70:
        return "Good Match"
    elif score >= 50:
        return "Partial Match"
    elif score >= 30:
        return "Stretch Role"
    return "Poor Match"


async def _progress_callback(msg: str):
    console.print(f"  [dim]→[/dim] {msg}")


@click.group()
def cli():
    """Resume-Job Matcher Agent powered by Claude AI."""
    pass


@cli.command()
@click.argument("resume_path", type=click.Path(exists=True, readable=True))
@click.option("--location", "-l", default=None, help="Preferred job location (e.g. 'New York' or 'Remote')")
@click.option("--max-results", "-n", default=10, show_default=True, help="Number of jobs to find (1-30)")
@click.option("--remote/--no-remote", default=True, show_default=True, help="Include remote jobs")
@click.option("--keywords", "-k", default="", help="Comma-separated extra keywords")
@click.option("--min-fit", default=0, type=float, show_default=True, help="Minimum fit % to display")
def analyze(resume_path, location, max_results, remote, keywords, min_fit):
    """Analyze a resume and find matching jobs."""
    console.print(Panel.fit(
        "[bold cyan]Resume-Job Matcher Agent[/bold cyan]\n"
        "[dim]Powered by Claude AI[/dim]",
        border_style="cyan",
    ))

    path = Path(resume_path)
    console.print(f"\n[bold]Resume:[/bold] {path.name}")

    search_request = SearchRequest(
        location=location,
        remote_ok=remote,
        max_results=max(1, min(30, max_results)),
        additional_keywords=[k.strip() for k in keywords.split(",") if k.strip()],
    )

    agent = ResumeJobMatcherAgent()

    async def run():
        with console.status("[bold green]Running agent pipeline...[/bold green]"):
            file_content = path.read_bytes()
            matches = await agent.run(
                file_content,
                path.name,
                search_request,
                on_progress=_progress_callback,
            )
        return matches

    matches = asyncio.run(run())

    # Profile summary
    profile = agent.profile
    console.print()
    console.print(Panel(
        f"[bold]{profile.name or 'Candidate'}[/bold]\n"
        f"Skills: {', '.join(profile.skills[:8])}\n"
        f"Experience: {profile.experience_years or '?'} years\n"
        f"Target roles: {', '.join(profile.preferred_roles[:3])}",
        title="[bold]Resume Profile[/bold]",
        border_style="blue",
    ))

    # Filter by min fit
    filtered = [m for m in matches if m.fit_score >= min_fit]
    console.print(f"\n[bold]{len(filtered)} Jobs Found[/bold] (sorted by fit %):\n")

    for i, match in enumerate(filtered, 1):
        score = match.fit_score
        color = fit_color(score)
        label = fit_label(score)

        console.print(f"[bold]{i}. {match.job.title}[/bold] — {match.job.company}")
        console.print(f"   [{color}]■ {score:.0f}% — {label}[/{color}]")
        if match.job.location:
            console.print(f"   📍 {match.job.location}")
        if match.job.salary_range:
            console.print(f"   💰 {match.job.salary_range}")

        if match.match_reasons:
            console.print(f"   [green]✓[/green] {match.match_reasons[0]}")
        if match.gap_reasons:
            console.print(f"   [yellow]⚠[/yellow] {match.gap_reasons[0]}")
        if match.apply_url:
            console.print(f"   🔗 {match.job.apply_url}")
        console.print()

    # Interactive feedback
    if click.confirm("\nWould you like to rate these recommendations? (helps evaluate quality)", default=False):
        _interactive_feedback(agent, filtered)

    console.print(Panel.fit(
        f"Session ID: [bold]{agent.session_id}[/bold]\n"
        "Run [bold]python main.py web[/bold] for the full web experience.",
        border_style="dim",
    ))


def _interactive_feedback(agent: ResumeJobMatcherAgent, matches):
    """Interactively collect feedback from the user."""
    rating_choices = {
        "1": FeedbackRating.VERY_RELEVANT,
        "2": FeedbackRating.RELEVANT,
        "3": FeedbackRating.SOMEWHAT_RELEVANT,
        "4": FeedbackRating.NOT_RELEVANT,
        "s": None,  # skip
    }

    console.print("\n[bold]Rating Options:[/bold]")
    console.print("  1 = 🌟 Perfect match   2 = 👍 Good   3 = 🤔 Maybe   4 = 👎 Not relevant   s = skip")
    console.print()

    for match in matches[:10]:
        console.print(f"[bold]{match.job.title}[/bold] at {match.job.company} — {match.fit_score:.0f}% fit")
        choice = click.prompt("  Rate (1/2/3/4/s)", default="s").strip().lower()

        if choice in rating_choices and rating_choices[choice] is not None:
            applied = click.confirm("  Did you apply?", default=False)
            feedback = UserFeedback(
                job_id=match.job.id or "",
                job_title=match.job.title,
                company=match.job.company,
                rating=rating_choices[choice],
                applied=applied,
                predicted_fit=match.fit_score,
            )
            agent.submit_feedback(feedback)
            console.print("  [green]✓ Feedback saved[/green]\n")
        else:
            console.print("  [dim]Skipped[/dim]\n")

    if agent.feedback:
        console.print("[bold]Running evaluation...[/bold]")
        report = asyncio.run(agent.get_evaluation_report())
        console.print(report)


@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload for development")
def web(host, port, reload):
    """Start the web server."""
    import uvicorn
    console.print(Panel.fit(
        f"[bold cyan]Starting Resume-Job Matcher Web App[/bold cyan]\n"
        f"Open [link]http://{host}:{port}[/link] in your browser",
        border_style="cyan",
    ))
    uvicorn.run("app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
