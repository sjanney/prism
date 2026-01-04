"""Interactive TUI menu for Prism CLI."""

import asyncio
import logging
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.columns import Columns
from rich.align import Align

from backend.database import get_session
from backend.ingestion import FrameMetadata
from backend.models import Collection, Frame
from backend.search_engine import search
from cli.banner import print_banner
from cli.image_viewer import display_image_actions
from cli.styled_input import styled_prompt
from sqlalchemy import select, func

logger = logging.getLogger(__name__)
console = Console()


def show_main_menu() -> str:
    """Display main menu and return user choice."""
    console.clear()
    print_banner()
    
    menu_options = Panel(
        "[bold cyan]Main Menu[/bold cyan]\n\n"
        "  [bold green]1[/bold green] - 🔍 Search Dataset\n"
        "  [bold green]2[/bold green] - 📁 View Collections\n"
        "  [bold green]3[/bold green] - 📊 View Database Stats\n"
        "  [bold yellow]q[/bold yellow] - 🚪 Quit",
        border_style="bright_blue",
        padding=(1, 2),
        title="[bold white]Navigation[/bold white]",
    )
    console.print(Align.center(menu_options))
    console.print()
    
    choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="1", choices=["1", "2", "3", "q", "Q"])
    return choice.lower()


async def load_frames_from_db() -> List[FrameMetadata]:
    """Load all frames from database."""
    async with get_session() as session:
        result = await session.execute(select(Frame))
        frames = result.scalars().all()
        
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


async def interactive_search() -> None:
    """Interactive search interface."""
    console.clear()
    print_banner()
    
    console.print(Panel(
        "[bold cyan]🔍 Search Dataset[/bold cyan]",
        border_style="bright_blue",
        padding=(0, 1),
    ))
    console.print()
    
    # Check if database has frames
    frame_metadata_list = await load_frames_from_db()
    if not frame_metadata_list:
        error_panel = Panel(
            "[bold yellow]⚠ No frames found in database.[/bold yellow]\n\n"
            "Run [cyan]prism ingest --path <dataset_path>[/cyan] first.",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(error_panel)
        console.print()
        Prompt.ask("[dim]Press Enter to continue[/dim]")
        return
    
    info_panel = Panel(
        f"[bold green]✓ Loaded {len(frame_metadata_list)} frames from database[/bold green]",
        border_style="green",
        padding=(0, 1),
    )
    console.print(info_panel)
    console.print()
    
    # Get search query with styled input
    query = styled_prompt("Enter search query")
    if not query:
        console.print("[yellow]No query provided, returning to menu[/yellow]")
        return
    
    # Get sensor type filter
    sensor_panel = Panel(
        "[cyan]Filter by sensor type (optional):[/cyan]\n\n"
        "  [green]1[/green] - All sensors\n"
        "  [green]2[/green] - 📷 Camera only\n"
        "  [green]3[/green] - 🔄 LiDAR only\n"
        "  [green]4[/green] - 📡 Radar only",
        border_style="cyan",
        padding=(1, 2),
        title="[bold]Sensor Filter[/bold]",
    )
    console.print(sensor_panel)
    console.print()
    sensor_filter_choice = styled_prompt("Sensor filter", default="1", choices=["1", "2", "3", "4"])
    
    sensor_filter = None
    if sensor_filter_choice == "2":
        sensor_filter = "camera"
    elif sensor_filter_choice == "3":
        sensor_filter = "lidar"
    elif sensor_filter_choice == "4":
        sensor_filter = "radar"
    
    # Filter frames by sensor type if requested
    if sensor_filter:
        original_count = len(frame_metadata_list)
        frame_metadata_list = [
            fm for fm in frame_metadata_list 
            if getattr(fm, "sensor_type", "camera") == sensor_filter
        ]
        console.print(f"[dim]Filtered to {len(frame_metadata_list)} {sensor_filter} frames (from {original_count} total)[/dim]")
    
    # Get confidence threshold
    console.print()
    try:
        confidence_str = styled_prompt("Confidence threshold (0-100)", default="25")
        confidence = float(confidence_str)
        min_similarity = max(0.0, min(1.0, confidence / 100.0))
    except ValueError:
        console.print("[yellow]Invalid confidence, using default (25%)[/yellow]")
        min_similarity = 0.25
    
    # Get max results
    console.print()
    try:
        max_results_str = styled_prompt("Maximum results", default="20")
        max_results = int(max_results_str)
    except ValueError:
        console.print("[yellow]Invalid number, using default (20)[/yellow]")
        max_results = 20
    
    # Run search with progress
    console.print()
    search_panel = Panel(
        "[bold cyan]🔍 Running semantic search...[/bold cyan]",
        border_style="bright_blue",
        padding=(0, 1),
    )
    console.print(search_panel)
    console.print()
    
    def update_progress(current: int, total: int):
        if current % 10 == 0 or current == total:
            console.print(f"[dim cyan]Processing batch {current}/{total}...[/dim cyan]")
    
    results = search(
        query,
        frame_metadata_list=frame_metadata_list,
        min_similarity=min_similarity,
        progress_callback=update_progress,
    )
    
    # Limit results
    results = results[:max_results]
    
    if not results:
        console.print()
        no_results_panel = Panel(
            "[bold yellow]⚠ No matches found for your query.[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(no_results_panel)
        console.print()
        Prompt.ask("[dim]Press Enter to continue[/dim]")
        return
    
    # Display results
    display_search_results(results, query)


def display_search_results(results: List, query: str) -> None:
    """Display search results in an interactive table."""
    while True:
        console.clear()
        print_banner()
        
        console.print(Panel(
            f"[bold cyan]🔍 Search Results[/bold cyan]\n[dim]Query: '{query}'[/dim]",
            border_style="bright_blue",
            padding=(1, 2),
            title="[bold white]Results[/bold white]",
        ))
        console.print()
        
        # Create results table
        table = Table(
            show_header=True,
            header_style="bold bright_blue",
            border_style="blue",
            row_styles=["", "dim"],
            show_lines=False,
        )
        table.add_column("#", style="cyan", width=4, justify="right")
        table.add_column("Frame ID", style="cyan", width=10)
        table.add_column("Confidence", style="green", width=12, justify="right")
        table.add_column("Sensor", style="blue", width=10)
        table.add_column("Type/Angle", style="cyan", width=15)
        table.add_column("Weather", style="yellow", width=12)
        table.add_column("Timestamp", style="dim", width=20)
        
        for idx, result in enumerate(results, 1):
            # Color code confidence
            confidence_str = f"{result.confidence:.1f}%"
            if result.confidence >= 80:
                confidence_style = "bold green"
            elif result.confidence >= 50:
                confidence_style = "yellow"
            else:
                confidence_style = "red"
            
            timestamp_str = result.timestamp[:19] if result.timestamp else "N/A"
            
            # Get sensor type from frame metadata if available
            sensor_type = getattr(result, "sensor_type", "camera") if hasattr(result, "sensor_type") else "camera"
            sensor_display = sensor_type.upper()
            
            table.add_row(
                str(idx),
                str(result.frame_id) if result.frame_id else "N/A",
                f"[{confidence_style}]{confidence_str}[/{confidence_style}]",
                sensor_display,
                result.camera_angle or "N/A",
                result.weather or "N/A",
                timestamp_str,
            )
        
        console.print(table)
        console.print()
        
        stats_panel = Panel(
            f"[bold green]✓ Found {len(results)} results[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
        console.print(stats_panel)
        console.print()
        
        options_panel = Panel(
            f"[cyan]Options:[/cyan]\n\n"
            f"  [bold green]1-{len(results)}[/bold green] - View result details\n"
            "  [bold yellow]s[/bold yellow] - 💾 Save as collection\n"
            "  [bold yellow]b[/bold yellow] - 🔙 Back to main menu",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(options_panel)
        console.print()
        
        choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]")
        
        if choice.lower() == "b":
            break
        elif choice.lower() == "s":
            save_collection_interactive(results, query)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                view_result_details(results[idx])
            else:
                console.print("[red]Invalid selection[/red]")
                Prompt.ask("[dim]Press Enter to continue[/dim]")
        else:
            console.print("[red]Invalid choice[/red]")
            Prompt.ask("[dim]Press Enter to continue[/dim]")


def view_result_details(result) -> None:
    """View detailed information about a search result."""
    while True:
        console.clear()
        print_banner()
        
        console.print(Panel(
            "[bold cyan]📋 Frame Details[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 2),
            title="[bold white]Details[/bold white]",
        ))
        console.print()
        
        # Create details table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="green")
        
        sensor_type = getattr(result, "sensor_type", "camera") if hasattr(result, "sensor_type") else "camera"
        original_path = getattr(result, "original_path", None) if hasattr(result, "original_path") else None
        
        table.add_row("Frame ID", str(result.frame_id) if result.frame_id else "N/A")
        table.add_row("Confidence", f"{result.confidence:.2f}%")
        table.add_row("Sensor Type", sensor_type.upper())
        table.add_row("Path", result.frame_path)
        if original_path and original_path != result.frame_path:
            table.add_row("Original Path", original_path)
        table.add_row("Sensor Angle/Type", result.camera_angle or "N/A")
        table.add_row("Weather", result.weather or "N/A")
        table.add_row("GPS", f"({result.gps_lat}, {result.gps_lon})" if result.gps_lat and result.gps_lon else "N/A")
        table.add_row("Timestamp", result.timestamp or "N/A")
        if result.reasoning:
            table.add_row("Reasoning", result.reasoning)
        
        console.print("\n")
        console.print(table)
        
        # Image/sensor data actions
        # For LiDAR, show original path option; for camera, show image viewer
        display_path = result.frame_path
        if original_path and sensor_type == "lidar":
            # For LiDAR, allow viewing both visualization and original point cloud
            console.print(f"\n[cyan]LiDAR Data:[/cyan]")
            console.print(f"  Visualization: {result.frame_path}")
            console.print(f"  Original: {original_path}")
            choice = Prompt.ask("\nView [1] visualization image, [2] original path, or [b] back", default="1")
            if choice == "2":
                display_path = original_path
            elif choice.lower() == "b":
                break
        
        if display_path:
            action = display_image_actions(display_path, result.frame_id)
            if action == "back":
                break
            else:
                Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        else:
            console.print("\n[yellow]No path available[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
            break


async def save_collection_interactive(results: List, query: str) -> None:
    """Save search results as a collection interactively."""
    console.print()
    save_panel = Panel(
        "[bold cyan]💾 Save Collection[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2),
    )
    console.print(save_panel)
    console.print()
    
    name = styled_prompt("Collection name")
    if not name:
        console.print("[yellow]Collection name required[/yellow]")
        return
    
    try:
        async with get_session() as session:
            # Get frame IDs from results
            result_ids = [r.frame_id for r in results if r.frame_id is not None]
            
            if not result_ids:
                console.print("[yellow]No frame IDs to save[/yellow]")
                return
            
            # Calculate metadata
            avg_confidence = sum(r.confidence for r in results) / len(results)
            metadata = {
                "avg_confidence": avg_confidence,
                "total_results": len(results),
                "query": query,
            }
            
            collection = Collection(
                name=name,
                query=query,
                result_ids=result_ids,
                collection_metadata=metadata,
            )
            session.add(collection)
            await session.commit()
            
            console.print(f"\n[green]✓ Saved collection '{name}' (ID: {collection.id})[/green]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
    except Exception as e:
        console.print(f"[red]Error saving collection: {e}[/red]")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")


async def view_collections() -> None:
    """View all saved collections."""
    console.clear()
    print_banner()
    
    console.print(Panel(
        "[bold cyan]📁 Saved Collections[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2),
        title="[bold white]Collections[/bold white]",
    ))
    console.print()
    
    try:
        async with get_session() as session:
            result = await session.execute(select(Collection).order_by(Collection.created_at.desc()))
            collections = result.scalars().all()
            
            if not collections:
                no_collections_panel = Panel(
                    "[yellow]No collections found.[/yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                )
                console.print(no_collections_panel)
                console.print()
                Prompt.ask("[dim]Press Enter to continue[/dim]")
                return
            
            table = Table(
                show_header=True,
                header_style="bold bright_blue",
                border_style="blue",
                row_styles=["", "dim"],
            )
            table.add_column("#", style="cyan", width=4, justify="right")
            table.add_column("Name", style="green", width=30)
            table.add_column("Query", style="yellow", width=40)
            table.add_column("Results", style="cyan", width=10, justify="right")
            table.add_column("Created", style="dim", width=20)
            
            for idx, collection in enumerate(collections, 1):
                result_count = len(collection.result_ids) if collection.result_ids else 0
                created_str = collection.created_at.strftime("%Y-%m-%d %H:%M") if collection.created_at else "N/A"
                query_display = collection.query[:37] + "..." if len(collection.query) > 40 else collection.query
                
                table.add_row(
                    str(idx),
                    collection.name,
                    query_display,
                    str(result_count),
                    created_str,
                )
            
            console.print(table)
            console.print()
            
            stats_panel = Panel(
                f"[bold green]✓ Total collections: {len(collections)}[/bold green]",
                border_style="green",
                padding=(0, 1),
            )
            console.print(stats_panel)
            console.print()
            
            Prompt.ask("[dim]Press Enter to continue[/dim]")
    except Exception as e:
        console.print(f"[red]Error loading collections: {e}[/red]")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")


async def view_database_stats() -> None:
    """Display database statistics."""
    console.clear()
    print_banner()
    
    console.print(Panel(
        "[bold cyan]📊 Database Statistics[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2),
        title="[bold white]Statistics[/bold white]",
    ))
    console.print()
    
    try:
        async with get_session() as session:
            # Frame stats
            frame_result = await session.execute(select(Frame))
            frames = frame_result.scalars().all()
            
            # Collection stats
            collection_result = await session.execute(select(Collection))
            collections = collection_result.scalars().all()
            
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Metric", style="cyan", width=30)
            table.add_column("Value", style="green")
            
            table.add_row("Total Frames", str(len(frames)))
            table.add_row("Total Collections", str(len(collections)))
            
            # Sensor type distribution
            if frames:
                sensor_counts = {}
                for frame in frames:
                    sensor_type = getattr(frame, "sensor_type", "camera") or "camera"
                    sensor_counts[sensor_type] = sensor_counts.get(sensor_type, 0) + 1
                
                table.add_row("", "")  # Spacer
                table.add_row("[bold]Sensor Types[/bold]", "")
                sensor_icons = {"camera": "📷", "lidar": "🔄", "radar": "📡"}
                for sensor_type in sorted(sensor_counts.keys()):
                    icon = sensor_icons.get(sensor_type, "📦")
                    count = sensor_counts[sensor_type]
                    table.add_row(f"  {icon} {sensor_type.upper()}", str(count))
            
            # Camera angle distribution
            if frames:
                camera_counts = {}
                for frame in frames:
                    camera = frame.camera_angle or "Unknown"
                    camera_counts[camera] = camera_counts.get(camera, 0) + 1
                
                table.add_row("", "")  # Spacer
                table.add_row("[bold]Camera Angles[/bold]", "")
                for camera, count in sorted(camera_counts.items()):
                    table.add_row(f"  {camera}", str(count))
            
            # Weather distribution
            if frames:
                weather_counts = {}
                for frame in frames:
                    weather = frame.weather or "Unknown"
                    weather_counts[weather] = weather_counts.get(weather, 0) + 1
                
                table.add_row("", "")  # Spacer
                table.add_row("[bold]Weather Conditions[/bold]", "")
                for weather, count in sorted(weather_counts.items()):
                    table.add_row(f"  {weather}", str(count))
            
            console.print(table)
            console.print()
            
            Prompt.ask("[dim]Press Enter to continue[/dim]")
    except Exception as e:
        console.print(f"[red]Error loading stats: {e}[/red]")
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")


async def run_interactive() -> None:
    """Main interactive loop."""
    while True:
        choice = show_main_menu()
        
        if choice == "q" or choice == "quit":
            console.clear()
            print_banner()
            goodbye_panel = Panel(
                "[bold cyan]👋 Thank you for using Prism![/bold cyan]",
                border_style="bright_blue",
                padding=(1, 2),
            )
            console.print(goodbye_panel)
            console.print()
            break
        elif choice == "1":
            await interactive_search()
        elif choice == "2":
            await view_collections()
        elif choice == "3":
            await view_database_stats()
        else:
            console.print("[yellow]Invalid choice. Please try again.[/yellow]")
            await asyncio.sleep(1)

