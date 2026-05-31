import json
from typing import TYPE_CHECKING
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from .schemas import Analysis, Severity

console = Console()

_SEVERITY_COLOUR: dict[Severity, str] = {
    Severity.info: "dim",
    Severity.low: "cyan",
    Severity.medium: "yellow",
    Severity.high: "bold red",
    Severity.critical: "bold white on red",
}

_SEVERITY_ICON: dict[Severity, str] = {
    Severity.info: "·",
    Severity.low: "▸",
    Severity.medium: "▲",
    Severity.high: "✖",
    Severity.critical: "✖✖",
}

_SEVERITY_ORDER: dict[Severity, int] = {s: i for i, s in enumerate(Severity)}


def _badge(sev: Severity) -> Text:
    return Text(f"{_SEVERITY_ICON[sev]} {sev.value.upper()}", style=_SEVERITY_COLOUR[sev])


def format_terminal(analysis: Analysis) -> None:
    console.print()

    # ── Summary ───────────────────────────────────────────────────────────────
    console.print(
        Panel(
            f"  {analysis.summary}",
            title="[bold]Infrastructure Summary[/bold]",
            border_style="blue",
        )
    )

    # ── Resources ─────────────────────────────────────────────────────────────
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold", expand=True)
    tbl.add_column("Type", style="cyan", no_wrap=True)
    tbl.add_column("Name", style="green", no_wrap=True)
    tbl.add_column("Purpose")

    for r in analysis.resources:
        tbl.add_row(r.resource_type, r.name, r.purpose)

    console.print(Panel(tbl, title="[bold]Resources[/bold]", border_style="blue"))

    # ── Cost Estimate ─────────────────────────────────────────────────────────
    cost = analysis.cost
    cost_tbl = Table(box=box.SIMPLE_HEAD, show_header=False, expand=False)
    cost_tbl.add_column("Key", style="bold", no_wrap=True)
    cost_tbl.add_column("Value")

    cost_tbl.add_row(
        "Monthly estimate",
        f"${cost.low_usd_monthly:.2f} – ${cost.high_usd_monthly:.2f}",
    )
    cost_tbl.add_row("Confidence", _badge(cost.confidence))
    for i, caveat in enumerate(cost.caveats):
        cost_tbl.add_row("Caveats" if i == 0 else "", Text(caveat, style="dim"))

    console.print(Panel(cost_tbl, title="[bold]Cost Estimate[/bold]", border_style="blue"))

    # ── Security Findings ─────────────────────────────────────────────────────
    worst = analysis.overall_risk
    border = _SEVERITY_COLOUR.get(worst, "yellow").split()[-1]  # strip bold modifier

    title_text = (
        f"[bold]Security Findings[/bold]  "
        f"Overall risk: [{_SEVERITY_COLOUR[worst]}]{_SEVERITY_ICON[worst]} {worst.value.upper()}[/{_SEVERITY_COLOUR[worst]}]"
    )

    if not analysis.security_findings:
        console.print(
            Panel(
                Text("  No security findings.", style="green"),
                title=title_text,
                border_style="green",
            )
        )
    else:
        from rich.columns import Columns
        from rich.rule import Rule

        rows: list[RenderableType] = []
        for finding in sorted(
            analysis.security_findings,
            key=lambda f: _SEVERITY_ORDER[f.severity],
            reverse=True,
        ):
            colour = _SEVERITY_COLOUR[finding.severity].split()[-1]
            header = Text()
            header.append_text(_badge(finding.severity))
            header.append(f"  {finding.resource}", style=f"bold {colour}")

            body = Table.grid(padding=(0, 1))
            body.add_column(style="dim", no_wrap=True)
            body.add_column()
            body.add_row("Issue", finding.issue)
            body.add_row("Fix", finding.recommendation)

            rows.append(header)
            rows.append(body)
            rows.append(Rule(style="dim"))

        # drop the trailing rule
        if rows and isinstance(rows[-1], Rule):
            rows.pop()

        from rich.console import Group
        console.print(Panel(Group(*rows), title=title_text, border_style=border))

    console.print()


def format_json(analysis: Analysis) -> str:
    return analysis.model_dump_json(indent=2)
