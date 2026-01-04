"""Styled input prompts for better UX."""

from typing import Optional, List

from rich.console import Console
from rich.prompt import Prompt

console = Console()


def styled_prompt(
    prompt: str,
    default: Optional[str] = None,
    choices: Optional[List[str]] = None,
) -> str:
    """
    Create a styled text input prompt with a clean, modern look.
    
    Args:
        prompt: The prompt text to display
        default: Default value (optional)
        choices: List of valid choices (optional)
    
    Returns:
        User input string
    """
    # Build the prompt text with arrow and styling
    prompt_label = f"[bold cyan]→ {prompt}[/bold cyan]"
    if default:
        prompt_label += f" [dim][{default}][/dim]"
    
    # Use Rich's Prompt with the styled label
    # This creates a clean, modern input prompt
    result = Prompt.ask(
        prompt_label,
        default=default,
        choices=choices,
    )
    
    return result
