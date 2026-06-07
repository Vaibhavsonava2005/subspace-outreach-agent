#!/usr/bin/env python3
"""
Subspace Cold Outreach Agent - CLI Entry Point
Created by Vaibhav Sonava

Beautiful terminal interface for the fully automated cold outreach pipeline.
Pipeline: Domain -> Ocean.io -> Prospeo -> Eazyreach -> Brevo -> Emails Sent
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import load_config
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.exporter import ResultExporter

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
# Force UTF-8 output on Windows to avoid charmap encoding errors
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(force_terminal=True)

BANNER = """
[bold cyan]+================================================================+[/]
[bold cyan]|[/]  [bold white] ____  _   _ ____  ____  ____   _    ____ _____            [/]  [bold cyan]|[/]
[bold cyan]|[/]  [bold white]/ ___|| | | | __ )/ ___||  _ \\ / \\  / ___| ____|           [/]  [bold cyan]|[/]
[bold cyan]|[/]  [bold white]\\___ \\| | | |  _ \\\\___ \\| |_) / _ \\| |   |  _|             [/]  [bold cyan]|[/]
[bold cyan]|[/]  [bold white] ___) | |_| | |_) |___) |  __/ ___ \\ |___| |___            [/]  [bold cyan]|[/]
[bold cyan]|[/]  [bold white]|____/ \\___/|____/|____/|_| /_/   \\_\\____|_____|           [/]  [bold cyan]|[/]
[bold cyan]|[/]                                                                [bold cyan]|[/]
[bold cyan]|[/]  [bold green]COLD OUTREACH AGENT[/]                                        [bold cyan]|[/]
[bold cyan]|[/]  [dim]Automated Pipeline:[/] [yellow]Ocean > Prospeo > Brevo[/]                 [bold cyan]|[/]
[bold cyan]|[/]  [dim]Created by[/] [bold magenta]Vaibhav Sonava[/]                                   [bold cyan]|[/]
[bold cyan]+================================================================+[/]
"""

STAGE_LABELS = [
    ("Stage 1", "Ocean.io - Similar Company Discovery"),
    ("Stage 2", "Prospeo - Decision Maker Discovery"),
    ("Stage 3", "Brevo - Email Delivery"),
]


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subspace-outreach-agent",
        description="Fully automated cold outreach pipeline - Subspace / Vocallabs assignment.",
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Target company domain (e.g. hubspot.com)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview the pipeline without actually sending emails.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory to save results (default: output/).",
    )
    return parser


def _print_config_table(cfg: dict) -> None:
    """Render a table showing which API keys are configured."""
    table = Table(
        title="Configuration Status",
        box=box.ROUNDED,
        title_style="bold white",
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Service", style="bold white", min_width=16)
    table.add_column("Key", style="dim")
    table.add_column("Status", justify="center")

    rows = [
        ("Ocean.io", "ocean_api_key"),
        ("Prospeo", "prospeo_api_key"),
        ("Brevo", "brevo_api_key"),
        ("Sender Email", "sender_email"),
        ("Sender Name", "sender_name"),
    ]
    for label, key in rows:
        value = cfg.get(key)
        if value and value not in ("", "your_ocean_api_key_here", "your_prospeo_api_key_here",
                                    "your_brevo_api_key_here",
                                    "your_verified_sender@example.com"):
            masked = value[:4] + "****" if len(value) > 4 else "****"
            status = "[bold green]Configured[/]"
        else:
            masked = "-"
            status = "[bold red]Missing[/]"
        table.add_row(label, masked, status)

    console.print()
    console.print(table)
    console.print()


def _print_summary(result, stage_times: dict, dry_run: bool) -> None:
    """Print a beautiful post-pipeline summary table."""
    table = Table(
        title="Pipeline Summary",
        box=box.HEAVY_HEAD,
        title_style="bold white",
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Metric", style="bold white", min_width=28)
    table.add_column("Value", justify="right", style="bold yellow", min_width=20)

    table.add_row("Input Domain", result.input_domain)
    table.add_row("Companies Found", str(len(result.companies_found)))
    table.add_row("Decision Makers Discovered", str(len(result.decision_makers)))
    table.add_row("Emails Enriched", str(len(result.emails_enriched)))
    table.add_row(
        "Emails Sent" if not dry_run else "Emails Drafted (dry-run)",
        str(len(result.emails_sent)),
    )
    table.add_row("", "")

    for stage_name, elapsed in result.stage_timings.items():
        table.add_row(f"  {stage_name}", f"{elapsed:.3f}s")

    table.add_row("", "")
    table.add_row("[bold]Total Duration[/]", f"[bold green]{result.total_duration:.2f}s[/]")

    console.print()
    console.print(table)
    console.print()


def _print_email_drafts(result, dry_run: bool) -> None:
    """Show each generated email draft inside a Rich Panel."""
    drafts = result.emails_sent
    if not drafts:
        console.print("[dim]No email drafts to display.[/dim]")
        return

    label = "Email Drafts (DRY RUN - not sent)" if dry_run else "Emails Sent"
    console.print(f"\n[bold white]{label}[/]\n")

    for idx, draft in enumerate(drafts, start=1):
        header_text = f"To: {draft.to_name} <{draft.to_email}>  |  Subject: {draft.subject}"

        # Strip HTML tags for terminal preview
        import re
        body_preview = re.sub(r'<[^>]+>', '', draft.body_html)
        body_preview = body_preview.strip()[:500]

        console.print(
            Panel(
                f"[bold cyan]{header_text}[/]\n\n{body_preview}",
                title=f"[bold yellow]Email #{idx}[/]",
                border_style="cyan",
                padding=(1, 2),
            )
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # -- Banner --
    console.print(BANNER)

    # -- Dry-run warning --
    if args.dry_run:
        console.print(
            Panel(
                "[bold yellow]DRY-RUN MODE - No emails will actually be sent.[/]",
                border_style="yellow",
                box=box.DOUBLE,
            )
        )

    # -- Load configuration --
    console.print("[bold white]Loading configuration...[/]")
    cfg = load_config()
    _print_config_table(cfg)

    # -- Ensure output directory --
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg["output_dir"] = str(output_dir)

    # -- Run the full pipeline --
    console.rule("[bold cyan]Starting Pipeline[/]")
    console.print()

    orchestrator = PipelineOrchestrator(cfg)
    result = orchestrator.run(domain=args.domain, dry_run=args.dry_run)

    console.rule("[bold green]Pipeline Complete[/]")

    # -- Summary table --
    _print_summary(result, result.stage_timings, args.dry_run)

    # -- Email drafts --
    _print_email_drafts(result, args.dry_run)

    # -- Export results --
    try:
        json_path = ResultExporter.to_json(result, str(output_dir))
        csv_path = ResultExporter.to_csv(result, str(output_dir))
        console.print(
            Panel(
                f"[bold green]Results saved:[/]\n  JSON: {json_path}\n  CSV:  {csv_path}",
                border_style="green",
            )
        )
    except Exception as exc:
        console.print(f"[bold red]Failed to export results: {exc}[/]")

    # -- Final footer --
    console.print()
    console.print(
        Align.center(
            Text.from_markup(
                "[dim]Subspace Cold Outreach Agent -- Created by [bold]Vaibhav Sonava[/bold][/dim]"
            )
        )
    )
    console.print()


if __name__ == "__main__":
    main()
