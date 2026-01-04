"""Database connection configuration and management."""

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from backend.config import settings

console = Console()

CONFIG_DIR = Path.home() / ".prism"
CONFIG_FILE = CONFIG_DIR / "db_config.ini"


def ensure_config_dir():
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_database_url() -> str:
    """Get the current database URL from environment or config."""
    # Check environment variable first (highest priority)
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    
    # Check config file
    if CONFIG_FILE.exists():
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            if config.has_section("database") and config.has_option("database", "url"):
                return config.get("database", "url")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read config file: {e}[/yellow]")
    
    # Return default
    return settings.database_url


def save_database_url(url: str) -> bool:
    """Save database URL to config file."""
    try:
        ensure_config_dir()
        import configparser
        config = configparser.ConfigParser()
        
        if CONFIG_FILE.exists():
            config.read(CONFIG_FILE)
        
        if not config.has_section("database"):
            config.add_section("database")
        
        config.set("database", "url", url)
        
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
        
        return True
    except Exception as e:
        console.print(f"[red]Error saving config: {e}[/red]")
        return False


def test_connection(url: str) -> bool:
    """Test if database connection works."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        import asyncio
        
        engine = create_async_engine(url, echo=False)
        
        async def test():
            try:
                async with engine.begin() as conn:
                    await conn.execute("SELECT 1")
                return True
            except Exception:
                return False
            finally:
                await engine.dispose()
        
        return asyncio.run(test())
    except Exception as e:
        console.print(f"[dim]Connection test error: {e}[/dim]")
        return False


def interactive_db_setup() -> Optional[str]:
    """Interactive database connection setup wizard."""
    console.clear()
    console.print(Panel(
        "[bold cyan]🗄️  Database Connection Setup[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2),
    ))
    console.print()
    
    console.print("[cyan]Choose database type:[/cyan]")
    console.print("  [green]1[/green] - SQLite (local file, default)")
    console.print("  [green]2[/green] - PostgreSQL (remote or local)")
    console.print("  [green]3[/green] - Custom connection string")
    console.print("  [yellow]c[/yellow] - Cancel")
    console.print()
    
    choice = Prompt.ask("[bold cyan]Select option[/bold cyan]", default="1")
    
    if choice.lower() == "c":
        return None
    
    url = None
    
    if choice == "1":
        # SQLite setup
        console.print()
        db_path = Prompt.ask(
            "[bold cyan]Database file path[/bold cyan]",
            default="prism.db"
        )
        if not db_path.endswith(".db"):
            db_path += ".db"
        
        # Resolve to absolute path
        db_path_obj = Path(db_path)
        if not db_path_obj.is_absolute():
            db_path_obj = Path.cwd() / db_path_obj
        
        url = f"sqlite+aiosqlite:///{db_path_obj}"
        console.print(f"[dim]Connection string: {url}[/dim]")
        
    elif choice == "2":
        # PostgreSQL setup
        console.print()
        host = Prompt.ask("[bold cyan]Host[/bold cyan]", default="localhost")
        port = Prompt.ask("[bold cyan]Port[/bold cyan]", default="5432")
        database = Prompt.ask("[bold cyan]Database name[/bold cyan]", default="prism")
        username = Prompt.ask("[bold cyan]Username[/bold cyan]")
        password = Prompt.ask("[bold cyan]Password[/bold cyan]", password=True)
        
        url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
        console.print(f"[dim]Connection string: {url.replace(password, '***')}[/dim]")
        
    elif choice == "3":
        # Custom connection string
        console.print()
        console.print("[yellow]Enter a full database URL (e.g., postgresql+asyncpg://user:pass@host:port/db)[/yellow]")
        url = Prompt.ask("[bold cyan]Connection string[/bold cyan]")
        
    if url:
        console.print()
        console.print("[cyan]Testing connection...[/cyan]")
        if test_connection(url):
            console.print("[green]✓ Connection successful![/green]")
            if Confirm.ask("\n[bold cyan]Save this connection?[/bold cyan]", default=True):
                if save_database_url(url):
                    console.print("[green]✓ Configuration saved![/green]")
                    console.print(f"[dim]Config file: {CONFIG_FILE}[/dim]")
                    console.print()
                    console.print("[yellow]⚠ Note: You may need to restart the application for changes to take effect.[/yellow]")
                    console.print("[yellow]   Or set DATABASE_URL environment variable to override config file.[/yellow]")
                else:
                    console.print("[red]✗ Failed to save configuration[/red]")
            return url
        else:
            console.print("[red]✗ Connection failed. Please check your settings.[/red]")
            if Confirm.ask("\n[bold cyan]Use this connection anyway?[/bold cyan]", default=False):
                return url
    
    return None


def show_current_config():
    """Display current database configuration."""
    url = get_database_url()
    
    # Mask password in URL for display
    display_url = url
    if "@" in url and "://" in url:
        try:
            parts = url.split("://", 1)
            if "@" in parts[1]:
                auth_part, rest = parts[1].split("@", 1)
                if ":" in auth_part:
                    username = auth_part.split(":")[0]
                    display_url = f"{parts[0]}://{username}:***@{rest}"
        except Exception:
            pass
    
    console.print(Panel(
        f"[bold cyan]Current Database Configuration[/bold cyan]\n\n"
        f"[green]Connection:[/green] {display_url}\n\n"
        f"[dim]Config file: {CONFIG_FILE}[/dim]\n"
        f"[dim]Environment variable: DATABASE_URL (if set)[/dim]",
        border_style="bright_blue",
        padding=(1, 2),
    ))
    console.print()

