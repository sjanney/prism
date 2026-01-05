# Getting Started with Prism

This guide will help you install Prism and run your first semantic search.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | macOS 12+, Ubuntu 20.04+, Windows 10+ | macOS 14+, Ubuntu 22.04+ |
| **Python** | 3.9 | 3.11 |
| **Go** | 1.21 | 1.22 |
| **RAM** | 8 GB | 16 GB+ |
| **GPU** | None (CPU fallback) | Apple M1+, NVIDIA GTX 1080+ |

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/sjanney/prism.git
cd prism
```

### 2. Install Dependencies

```bash
make install
```

This will:
- Install Python dependencies (`torch`, `transformers`, `ultralytics`, etc.)
- Download Go modules

### 3. Build the Application

```bash
make build
```

This generates `prism_app` (the TUI binary) and compiles the gRPC code.

### 4. Run Prism

```bash
./run_prism.sh
```

You should see the Prism loading screen, followed by the main dashboard.

---

## First Index

1. Navigate to **Index New Data** using the arrow keys.
2. Press **Enter**.
3. Press **`o`** to open the native folder picker, or type a path manually.
4. Press **Enter** to begin indexing.

**Note:** The first indexing run will download model weights (~1.5 GB for SigLIP, ~50 MB for YOLOv8). This is a one-time download.

---

## First Search

1. After indexing, press **Tab** to go to the **Search** tab.
2. Type a query like `red car` or `person crossing street`.
3. Press **Enter**.
4. Use **Up/Down** arrows to navigate results on the current page.
5. Use **Left/Right** arrows (`h`/`l`) to switch result pages (if more than 15 results).
6. Press **Enter** to open the file in your default viewer.

---

## Troubleshooting

If you encounter issues, see [Error Codes](error-codes.md) for common problems and solutions.

| Error Code | Meaning |
|------------|---------|
| `PSM-1001` | Backend connection failed |
| `PSM-2001` | Model loading timeout |
| `PSM-3001` | Database dimension mismatch |

---

## Next Steps

- [Configuration](configuration.md) - Customize Prism's behavior
- [Architecture](architecture.md) - Understand how Prism works
- [API Reference](api-reference.md) - Integrate Prism into your tools
