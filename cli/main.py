"""Prism CLI tool for dataset ingestion and semantic search."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from backend.database import get_session, init_db
from backend.ingestion import NuScenesLoader, get_registry
from backend.ingestion.config_loader_wrapper import create_loader_from_config
from backend.models import Collection, Frame
from backend.search_engine import search
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()


@click.group()
def cli():
    """Prism - Semantic search for autonomous vehicle datasets."""
    pass


# Set default command to interactive mode if no command provided
def main():
    """Main entry point - defaults to interactive mode."""
    import sys
    if len(sys.argv) == 1:
        # No arguments, run interactive mode
        from cli.interactive import run_interactive
        try:
            asyncio.run(run_interactive())
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"[bold red]✗ Error: {e}[/bold red]")
            logger.exception("Interactive mode error")
    else:
        # Has arguments, use normal CLI
        cli()


if __name__ == "__main__":
    main()


@cli.command()
def init():
    """Initialize the database (creates tables)."""
    console.print("[bold blue]Initializing Prism database...[/bold blue]")
    
    try:
        asyncio.run(init_db())
        console.print("[bold green]✓ Database initialized successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Error initializing database: {e}[/bold red]")
        raise click.Abort()


@cli.command()
def db_config():
    """Configure database connection interactively."""
    from cli.db_config import interactive_db_setup
    
    url = interactive_db_setup()
    if url:
        console.print("\n[bold green]✓ Database configuration complete![/bold green]")
    else:
        console.print("\n[yellow]Configuration cancelled.[/yellow]")


@cli.command()
def db_status():
    """Show current database configuration."""
    from cli.db_config import show_current_config
    
    show_current_config()


@cli.command()
def interactive():
    """Launch interactive TUI menu for Prism."""
    from cli.interactive import run_interactive
    
    try:
        asyncio.run(run_interactive())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        logger.exception("Interactive mode error")
        raise click.Abort()


@cli.command()
@click.option(
    "--path",
    "-p",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to dataset directory",
)
@click.option(
    "--format",
    "-f",
    "format_name",
    type=str,
    help="Dataset format (nuscenes, csv, json, or plugin:PluginName). Auto-detected if not specified.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to configuration file (required for csv/json formats)",
)
@click.option(
    "--list-formats",
    "list_formats",
    is_flag=True,
    help="List all available dataset formats and exit",
)
@click.option(
    "--create-template",
    "template_format",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    help="Create a template configuration file for the specified format",
)
def ingest(path: Path, format_name: Optional[str], config_path: Optional[Path], list_formats: bool, template_format: Optional[str]):
    """Ingest dataset and index frames in the database."""
    
    registry = get_registry()
    
    # Handle list-formats
    if list_formats:
        formats = registry.list_available()
        console.print("[bold blue]Available dataset formats:[/bold blue]")
        for fmt in formats:
            console.print(f"  - {fmt}")
        return
    
    # Handle template generation
    if template_format:
        _generate_template(template_format)
        return
    
    console.print(f"[bold blue]Ingesting dataset from: {path}[/bold blue]")
    
    try:
        # Determine format
        if format_name:
            detected_format = format_name
        else:
            # Auto-detect
            detected_format = registry.detect_format(path)
            if detected_format:
                console.print(f"[dim]Auto-detected format: {detected_format}[/dim]")
            else:
                console.print("[bold red]✗ Could not auto-detect dataset format.[/bold red]")
                console.print("[yellow]Please specify --format or add a configuration file.[/yellow]")
                raise click.Abort()
        
        # Create loader
        loader = None
        
        # Handle config-based formats
        if detected_format.startswith("config:"):
            # Config file format
            if not config_path:
                # Look for config file in dataset directory
                config_files = ["prism_config.yaml", "prism_config.yml", "prism_config.json"]
                for cfg_file in config_files:
                    cfg_path = path / cfg_file
                    if cfg_path.exists():
                        config_path = cfg_path
                        break
                
                if not config_path:
                    console.print("[bold red]✗ Config file not found. Use --config or place prism_config.yaml in dataset directory.[/bold red]")
                    raise click.Abort()
            
            loader = create_loader_from_config(str(config_path), str(path))
        elif detected_format.startswith("plugin:"):
            # Plugin format
            plugin_name = detected_format.split(":", 1)[1]
            loader_class = registry.get_loader(plugin_name)
            if not loader_class:
                console.print(f"[bold red]✗ Plugin '{plugin_name}' not found.[/bold red]")
                console.print(f"[yellow]Available plugins: {[f for f in registry.list_available() if f != 'nuscenes' and f != 'csv' and f != 'json']}[/yellow]")
                raise click.Abort()
            loader = loader_class(str(path))
        elif config_path:
            # Explicit config file provided
            loader = create_loader_from_config(str(config_path), str(path))
        else:
            # Standard format (nuscenes, csv, json)
            loader_class = registry.get_loader(detected_format)
            if not loader_class:
                console.print(f"[bold red]✗ Format '{detected_format}' not found.[/bold red]")
                console.print(f"[yellow]Available formats: {registry.list_available()}[/yellow]")
                raise click.Abort()
            
            if detected_format in ["csv", "json"]:
                console.print("[bold red]✗ CSV/JSON formats require a configuration file.[/bold red]")
                console.print("[yellow]Use --config or --create-template to generate one.[/yellow]")
                raise click.Abort()
            
            loader = loader_class(str(path))
        
        if not loader:
            console.print("[bold red]✗ Failed to create loader.[/bold red]")
            raise click.Abort()
        
        # Load metadata with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading metadata...", total=None)
            frame_metadata_list = loader.load_metadata()
            progress.update(task, completed=len(frame_metadata_list))
        
        if not frame_metadata_list:
            console.print("[bold yellow]⚠ No frames found in dataset[/bold yellow]")
            return
        
        console.print(f"[green]Loaded {len(frame_metadata_list)} frames from metadata[/green]")
        
        # Insert frames into database with progress
        async def insert_frames():
            inserted_count = 0
            async with get_session() as session:
                # Load all existing frame paths into a set for O(1) lookup
                console.print("[dim]Checking for existing frames...[/dim]")
                existing_result = await session.execute(select(Frame.frame_path))
                existing_paths = set(existing_result.scalars().all())
                console.print(f"[dim]Found {len(existing_paths)} existing frames[/dim]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("({task.completed}/{task.total})"),
                    TimeElapsedColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        "[cyan]Indexing frames...",
                        total=len(frame_metadata_list)
                    )
                    
                    for frame_meta in frame_metadata_list:
                        # Check if frame already exists (O(1) set lookup instead of DB query)
                        if frame_meta.frame_path in existing_paths:
                            progress.update(task, advance=1)
                            continue  # Skip duplicates
                        
                        frame = Frame(
                            dataset=detected_format.split(":")[0] if ":" in detected_format else detected_format,
                            frame_path=frame_meta.frame_path,
                            timestamp=frame_meta.timestamp,
                            gps_lat=frame_meta.gps_lat,
                            gps_lon=frame_meta.gps_lon,
                            weather=frame_meta.weather,
                            camera_angle=frame_meta.camera_angle,
                            sensor_type=getattr(frame_meta, "sensor_type", "camera"),
                            original_path=getattr(frame_meta, "original_path", None),
                        )
                        session.add(frame)
                        inserted_count += 1
                        progress.update(task, advance=1)
                    
                    await session.commit()
                    return inserted_count
        
        inserted = asyncio.run(insert_frames())
        console.print(f"[bold green]✓ Successfully indexed {inserted} frames![/bold green]")
        
    except FileNotFoundError as e:
        console.print(f"[bold red]✗ Dataset not found: {e}[/bold red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[bold red]✗ Error during ingestion: {e}[/bold red]")
        logger.exception("Ingestion error")
        raise click.Abort()


def _generate_template(format_type: str) -> None:
    """Generate a template configuration file."""
    import yaml
    
    if format_type.lower() == "csv":
        template = {
            "format": "csv",
            "input": {
                "path": "data/my_dataset",
                "pattern": "*.csv",
                "recursive": True,
            },
            "mapping": {
                "frame_path": "file_path",
                "timestamp": "capture_time",
                "gps_lat": "latitude",
                "gps_lon": "longitude",
                "camera_angle": "sensor_name",
                "sensor_type": "camera",
                "weather": None,
            },
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
        }
    elif format_type.lower() == "json":
        template = {
            "format": "json",
            "input": {
                "path": "data/my_dataset",
                "pattern": "*.json",
                "recursive": True,
                "array_field": "frames",
            },
            "mapping": {
                "frame_path": "metadata.file_path",
                "timestamp": "metadata.timestamp",
                "gps_lat": "location.lat",
                "gps_lon": "location.lon",
                "camera_angle": "sensor.angle",
                "sensor_type": "camera",
                "weather": "metadata.weather",
            },
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
        }
    else:
        console.print(f"[bold red]✗ Unknown format: {format_type}[/bold red]")
        return
    
    output_path = Path(f"prism_config_{format_type}.yaml")
    
    with open(output_path, "w") as f:
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)
    
    console.print(f"[bold green]✓ Template created: {output_path}[/bold green]")
    console.print("[dim]Edit the template to match your dataset structure, then use it with --config[/dim]")


@cli.command()
@click.argument("query", required=True)
@click.option(
    "--save",
    "-s",
    type=str,
    help="Save results as a collection with this name",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=50,
    help="Maximum number of results to return (default: 50)",
)
def search_cmd(query: str, save: Optional[str], limit: int):
    """Search dataset using semantic query."""
    console.print(f"[bold blue]Searching for: '{query}'[/bold blue]")
    
    try:
        # Load frames from database
        async def load_frames():
            async with get_session() as session:
                result = await session.execute(select(Frame))
                frames = result.scalars().all()
                
                # Convert to FrameMetadata objects
                from backend.ingestion import FrameMetadata
                frame_metadata_list = []
                for frame in frames:
                    frame_meta = FrameMetadata(
                        frame_id=frame.id,
                        frame_path=frame.frame_path,
                        timestamp=frame.timestamp,
                        gps_lat=frame.gps_lat,
                        gps_lon=frame.gps_lon,
                        weather=frame.weather,
                        camera_angle=frame.camera_angle,
                        sensor_type=getattr(frame, "sensor_type", "camera"),
                        original_path=getattr(frame, "original_path", None),
                    )
                    frame_metadata_list.append(frame_meta)
                return frame_metadata_list
        
        frame_metadata_list = asyncio.run(load_frames())
        
        if not frame_metadata_list:
            console.print("[bold yellow]⚠ No frames found in database. Run 'ingest' first.[/bold yellow]")
            return
        
        console.print(f"[green]Loaded {len(frame_metadata_list)} frames from database[/green]")
        
        # Progress tracking for search
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total} batches)"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Processing frames...", total=None)
            
            def update_progress(current: int, total: int):
                progress.update(task, total=total, completed=current)
            
            results = search(query, frame_metadata_list=frame_metadata_list, progress_callback=update_progress)
        
        # Limit results
        results = results[:limit]
        
        if not results:
            console.print("[bold yellow]⚠ No matches found for your query.[/bold yellow]")
            return
        
        # Display results in table
        table = Table(title=f"Search Results: '{query}'", show_header=True, header_style="bold magenta")
        table.add_column("Frame ID", style="cyan", no_wrap=True)
        table.add_column("Confidence", style="green", justify="right")
        table.add_column("Timestamp", style="yellow")
        table.add_column("Sensor", style="blue", width=8)
        table.add_column("Camera/Angle", style="cyan", width=15)
        table.add_column("Weather", style="white")
        table.add_column("Path", style="dim")
        
        for result in results:
            # Format confidence with color coding
            confidence_str = f"{result.confidence:.1f}%"
            if result.confidence >= 80:
                confidence_style = "bold green"
            elif result.confidence >= 50:
                confidence_style = "yellow"
            else:
                confidence_style = "red"
            
            timestamp_str = result.timestamp[:19] if result.timestamp else "N/A"
            path_display = result.frame_path
            if len(path_display) > 50:
                path_display = "..." + path_display[-47:]
            
            sensor_type = getattr(result, "sensor_type", "camera") if hasattr(result, "sensor_type") else "camera"
            
            table.add_row(
                str(result.frame_id) if result.frame_id else "N/A",
                f"[{confidence_style}]{confidence_str}[/{confidence_style}]",
                timestamp_str,
                sensor_type.upper(),
                result.camera_angle or "N/A",
                result.weather or "N/A",
                path_display,
            )
        
        console.print(table)
        
        # Save collection if requested
        if save:
            async def save_collection():
                from backend.models import Collection
                from uuid import uuid4
                from datetime import datetime
                
                async with get_session() as session:
                    result_ids = [r.frame_id for r in results if r.frame_id is not None]
                    avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0
                    
                    collection = Collection(
                        id=str(uuid4()),
                        name=save,
                        query=query,
                        result_ids=result_ids,
                        collection_metadata={
                            "avg_confidence": avg_confidence,
                            "total_results": len(results),
                        },
                        created_at=datetime.utcnow(),
                    )
                    session.add(collection)
                    await session.commit()
            
            asyncio.run(save_collection())
            console.print(f"[bold green]✓ Collection '{save}' saved![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error during search: {e}[/bold red]")
        logger.exception("Search error")
        raise click.Abort()