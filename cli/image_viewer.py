"""Image viewing utilities for opening and displaying images."""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


def open_image_in_viewer(image_path: str) -> bool:
    """
    Open image in system default viewer (cross-platform).
    
    Args:
        image_path: Path to image file
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(image_path):
        console.print(f"[red]Error: Image file not found: {image_path}[/red]")
        return False
    
    try:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            subprocess.run(["open", image_path], check=True)
        elif system == "Windows":
            os.startfile(image_path)  # type: ignore
        else:  # Linux and others
            subprocess.run(["xdg-open", image_path], check=True)
        
        console.print(f"[green]✓ Opened image in default viewer[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error opening image: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error opening image: {e}[/red]")
        return False


def open_file_location(file_path: str) -> bool:
    """
    Open file location in system file manager (cross-platform).
    
    Args:
        file_path: Path to file
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        return False
    
    try:
        system = platform.system()
        file_dir = os.path.dirname(os.path.abspath(file_path))
        
        if system == "Darwin":  # macOS
            subprocess.run(["open", "-R", file_path], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", "/select,", file_path], check=True)
        else:  # Linux and others
            subprocess.run(["xdg-open", file_dir], check=True)
        
        console.print(f"[green]✓ Opened file location in file manager[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error opening file location: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error opening file location: {e}[/red]")
        return False


def copy_path_to_clipboard(file_path: str) -> bool:
    """
    Copy file path to clipboard (cross-platform).
    
    Args:
        file_path: Path to copy
        
    Returns:
        True if successful, False otherwise
    """
    try:
        system = platform.system()
        abs_path = os.path.abspath(file_path)
        
        if system == "Darwin":  # macOS
            subprocess.run(["pbcopy"], input=abs_path.encode(), check=True)
        elif system == "Windows":
            subprocess.run(["clip"], input=abs_path.encode(), check=True)
        else:  # Linux
            # Try xclip first, then xsel
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=abs_path.encode(), check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                subprocess.run(["xsel", "--clipboard", "--input"], input=abs_path.encode(), check=True)
        
        console.print(f"[green]✓ Copied path to clipboard: {abs_path}[/green]")
        return True
    except Exception as e:
        console.print(f"[yellow]⚠ Could not copy to clipboard: {e}[/yellow]")
        console.print(f"[dim]Path: {abs_path}[/dim]")
        return False


def show_image_info(image_path: str) -> None:
    """
    Display image information in a formatted table.
    
    Args:
        image_path: Path to image file
    """
    if not os.path.exists(image_path):
        console.print(f"[red]Error: Image file not found: {image_path}[/red]")
        return
    
    try:
        from PIL import Image
        
        img = Image.open(image_path)
        file_size = os.path.getsize(image_path)
        file_size_mb = file_size / (1024 * 1024)
        
        table = Table(title="Image Information", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        table.add_row("Path", image_path)
        table.add_row("Size", f"{file_size_mb:.2f} MB ({file_size:,} bytes)")
        table.add_row("Dimensions", f"{img.width} x {img.height} pixels")
        table.add_row("Format", img.format or "Unknown")
        table.add_row("Mode", img.mode)
        
        if hasattr(img, "_getexif") and img._getexif():
            exif = img._getexif()
            if exif:
                table.add_row("EXIF", "Available")
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error reading image info: {e}[/red]")


def display_image_actions(image_path: str, frame_id: Optional[int] = None) -> str:
    """
    Display image action menu and return selected action.
    
    Args:
        image_path: Path to image file
        frame_id: Optional frame ID for display
        
    Returns:
        Selected action: 'view', 'location', 'copy', 'info', or 'back'
    """
    from rich.prompt import Prompt
    
    console.print("\n")
    panel_content = f"[bold]Frame ID:[/bold] {frame_id}\n[bold]Path:[/bold] {image_path}"
    console.print(Panel(panel_content, title="Image Actions", border_style="blue"))
    
    console.print("\n[cyan]Select an action:[/cyan]")
    console.print("  [green]1[/green] - View image in default viewer")
    console.print("  [green]2[/green] - Open file location")
    console.print("  [green]3[/green] - Copy path to clipboard")
    console.print("  [green]4[/green] - Show image information")
    console.print("  [yellow]b[/yellow] - Back to results")
    
    choice = Prompt.ask("\n[bold]Choice[/bold]", default="1")
    
    if choice.lower() == "b":
        return "back"
    elif choice == "1":
        open_image_in_viewer(image_path)
        return "view"
    elif choice == "2":
        open_file_location(image_path)
        return "location"
    elif choice == "3":
        copy_path_to_clipboard(image_path)
        return "copy"
    elif choice == "4":
        show_image_info(image_path)
        return "info"
    else:
        console.print("[yellow]Invalid choice[/yellow]")
        return "back"

