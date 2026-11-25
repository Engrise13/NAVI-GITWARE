import sys
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax

from logic import (
    check_git_diff,
    get_embedding,
    get_push_diff,
    update_cache,
    vector_compare,
)

GATE_TITLE = "NAVI GITWARE"

console = Console(stderr=True)
console.rule(f"[bold cyan]{GATE_TITLE}[/]")

try:
    diff = get_push_diff()
    if not diff or not diff.strip():
        console.print("[bold green]PASSED![/] [dim](empty diff)[/]")
        sys.exit(0)

    base_dir = Path(__file__).resolve().parent.parent
    reports_dir = base_dir / "reports"
    cache_file = base_dir / "reports_cache.json"

    if not reports_dir.exists():
        console.print(
            "[bold yellow]no security reports folder found, skipping check...[/]"
        )
        sys.exit(0)

    cache = update_cache(reports_dir, cache_file)
    console.print(
        f"report scan & cache: [bold green]OK[/], loaded reports: [bold yellow]{len(cache)}[/]"
    )

    if not cache:
        console.print("[yellow]no security reports found, skipping check...[/]")
        sys.exit(0)

    diff_vector = get_embedding(diff)
    console.print("git diff to vector conversion: [bold green]OK[/]")

    scored_reports = []

    for report in cache.values():
        score = vector_compare(diff_vector, report["report_embedding"])
        scored_reports.append((score, report))

    best_score, best_report = max(scored_reports)
    console.print("finding best possible match: [bold green]OK[/]")

    with console.status(
        "[bold cyan]AI vulnerability checking...[/]", spinner="aesthetic"
    ):
        answer = check_git_diff(diff, best_report["report_text"])

    console.print("AI vulnerability checking: [bold green]OK[/]")

    if answer.vulnerable:
        if "." in answer.file:
            ext = answer.file.split(".")[-1]
        else:
            ext = "text"

        code_block = Syntax(
            answer.snippet,
            ext,
            theme="monokai",
            line_numbers=False,
        )

        console.print(
            Panel(
                Group(
                    f"[bold red]REASON:[/] [dim]{answer.reason}[/]",
                    f"[bold red]MATCHED REPORT:[/] [dim]{best_report['report_filename']}[/]",
                    f"[bold red]FILE:[/] [dim]{answer.file}[/]",
                    "[bold red]VULNERABLE CODE:[/]",
                    code_block,
                ),
                title="[bold]PUSH BLOCKED[/]",
                subtitle=f"[bold]{GATE_TITLE}[/]",
                border_style="red",
            )
        )
        sys.exit(1)

    console.print("[bold green]PASSED! pushing...[/]")

except Exception as error:  # noqa: BLE001
    console.print(f"[bold red]{error}[/]")
    sys.exit(1)
