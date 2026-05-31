import sys
from pathlib import Path
from enum import Enum

import typer
from rich.console import Console

from .parser import parse, ParseError
from .analyzer import analyze, AnalysisError
from .formatter import format_terminal, format_json

app = typer.Typer(
    name="iac-explain",
    help="Explain a Terraform file in plain English — what it provisions, what it costs, and what risks it carries.",
    add_completion=False,
)

err_console = Console(stderr=True)


class OutputFormat(str, Enum):
    terminal = "terminal"
    json = "json"


@app.command()
def explain(
    terraform_file: Path = typer.Argument(
        ...,
        help="Path to the .tf file to analyse.",
        exists=True,
        readable=True,
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.terminal,
        "--format",
        "-f",
        help="Output format: terminal (default) or json.",
    ),
) -> None:
    """Analyse a Terraform file and explain what it provisions, estimate costs, and flag security risks."""
    try:
        raw_hcl, parsed_resources = parse(terraform_file)
    except ParseError as exc:
        err_console.print(f"[bold red]Parse error:[/bold red] {exc}")
        raise typer.Exit(1)

    if not parsed_resources:
        err_console.print(
            "[yellow]Warning:[/yellow] No resource blocks found in the file. "
            "Make sure it contains at least one `resource` block."
        )
        raise typer.Exit(1)

    try:
        if format == OutputFormat.terminal:
            with err_console.status("[dim]Analysing with Claude…[/dim]"):
                analysis = analyze(raw_hcl, parsed_resources)
        else:
            analysis = analyze(raw_hcl, parsed_resources)
    except AnalysisError as exc:
        err_console.print(f"[bold red]Analysis error:[/bold red] {exc}")
        raise typer.Exit(1)

    if format == OutputFormat.json:
        typer.echo(format_json(analysis))
    else:
        format_terminal(analysis)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
