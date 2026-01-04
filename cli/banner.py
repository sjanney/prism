"""ASCII art banner for Prism CLI."""

from rich.console import Console
from rich.panel import Panel

console = Console()


PRISM_BANNER = r"""
$$$$$$$\            $$\                         
$$  __$$\           \__|                        
$$ |  $$ | $$$$$$\  $$\  $$$$$$$\ $$$$$$\$$$$\  
$$$$$$$  |$$  __$$\ $$ |$$  _____|$$  _$$  _$$\ 
$$  ____/ $$ |  \__|$$ |\$$$$$$\  $$ / $$ / $$ |
$$ |      $$ |      $$ | \____$$\ $$ | $$ | $$ |
$$ |      $$ |      $$ |$$$$$$$  |$$ | $$ | $$ |
\__|      \__|      \__|\_______/ \__| \__| \__|
"""


def print_banner():
    """Print the Prism ASCII art banner in a styled panel."""
    console.print(
        Panel(
            PRISM_BANNER.strip("\n"),
            title="[bold cyan]Prism[/bold cyan]",
            subtitle="[dim]Semantic Search for Autonomous Vehicle Datasets[/dim]",
            border_style="bright_blue",
            padding=(1, 2),
            expand=False,
        ),
        justify="center",
    )
    console.print()  # Add spacing after banner

