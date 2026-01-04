# Interactive CLI Guide

Prism now includes an interactive TUI (Text User Interface) that makes searching and exploring your dataset much easier!

## Installation

To use the `prism` command, install the package in development mode:

```bash
pip install -e .
```

This will make the `prism` command available globally.

## Usage

### Interactive Mode (Default)

Simply type `prism` to launch the interactive menu:

```bash
prism
```

This will show you a menu with options:
- **Search Dataset** - Interactive search with query input
- **View Collections** - Browse saved collections
- **View Database Stats** - See frame and collection statistics
- **Quit** - Exit the application

### Command-Line Mode

You can still use Prism from the command line:

```bash
# Initialize database
prism init

# Ingest dataset
prism ingest --path data/nuscenes

# Search (non-interactive)
prism search "pedestrian crossing" --limit 10

# Launch interactive mode explicitly
prism interactive
```

## Interactive Features

### Search Interface

1. Enter your natural language query
2. Set confidence threshold (0-100%, default: 25%)
3. Set maximum results (default: 20)
4. View results in a formatted table

### Results Viewer

- **Select a result** by entering its number (1-N)
- **View details** including:
  - Frame ID, confidence, path
  - Camera angle, weather, GPS coordinates
  - Timestamp and reasoning
- **Image actions**:
  - View image in default system viewer
  - Open file location in file manager
  - Copy path to clipboard
  - Show image information (dimensions, size, format)
- **Save collection** by pressing 's'

### Image Viewing

When viewing a result, you can:
- **View Image** - Opens in your system's default image viewer
- **Open File Location** - Opens the folder containing the image
- **Copy Path** - Copies the full file path to clipboard
- **Show Info** - Displays image metadata (size, dimensions, format)

## Keyboard Shortcuts

- **q** or **quit** - Exit from main menu
- **b** or **back** - Go back to previous screen
- **1-N** - Select result by number
- **s** - Save current results as collection

## Examples

### Example Workflow

```bash
# Launch interactive mode
prism

# Select "1" for Search Dataset
# Enter query: "car on highway"
# Set confidence: 30
# Set max results: 15

# View results, select result #3
# Choose "1" to view image in default viewer
# Press Enter to continue
# Press 'b' to go back
# Press 'q' to quit
```

## Cross-Platform Support

The image viewing features work on:
- **macOS** - Uses `open` command
- **Windows** - Uses `explorer` and `startfile`
- **Linux** - Uses `xdg-open`

Clipboard support:
- **macOS** - Uses `pbcopy`
- **Windows** - Uses `clip`
- **Linux** - Uses `xclip` or `xsel`

## Troubleshooting

### Command not found

If `prism` command is not found:
```bash
# Install in development mode
pip install -e .

# Or use Python module syntax
python -m cli.main interactive
```

### Image viewer not opening

Make sure you have a default image viewer set on your system. The command will attempt to use the system default.

### Clipboard not working (Linux)

Install `xclip` or `xsel`:
```bash
# Ubuntu/Debian
sudo apt-get install xclip

# Fedora
sudo dnf install xclip
```

