<p align="center">
  <img src="assets/prism_demo.gif" alt="Prism Demo" width="800"/>
</p>

<h1 align="center">Prism</h1>
<p align="center">
  <strong>Semantic Search for Autonomous Vehicle & Robotics Datasets</strong><br>
  <em>Find any frame in terabytes of sensor data with natural language. 100% local.</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#why-local-first">Why Local-First?</a> •
  <a href="#features">Features</a> •
  <a href="docs/">Docs</a>
</p>

---

## What is Prism?

Prism is a **local-first semantic search engine** built for engineers working with autonomous vehicles, robotics, and computer vision.

**Example:** Instead of grepping logs or manually tagging frames, just type:

> *"red car turning left at intersection"*

Prism finds matching frames instantly using vision AI (YOLOv8 + SigLIP) running **entirely on your machine**—no cloud, no upload, no limits.

---

## Quick Start

**Requirements:** Python 3.9+, Go 1.21+

```bash
# Clone and install (takes ~2 min)
git clone https://github.com/sjanney/prism.git && cd prism
make install && make build

# Run Prism
./run_prism.sh

# Try with included sample data:
# 1. Select "Index New Data" → type "data/sample" → Enter
# 2. Select "Search Dataset" → type "car" → Enter
```

**That's it.** You're searching images with natural language.

> 💡 **GPU recommended** for production datasets (CUDA or Apple MPS). CPU works for testing.

---

## Why Local-First?

| Problem | Prism Solution |
|---------|----------------|
| Proprietary AV data can't leave your network | All processing on your machine |
| Terabyte datasets are expensive to upload | Index locally, no egress fees |
| Cloud latency kills iteration speed | Instant search, sub-second queries |
| Compliance & IP concerns | Your data never touches a server |

---

## Features

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Query with natural language: "pedestrian crossing street at night" |
| **Video Support** | Index MP4/AVI/MOV files with smart frame extraction (1fps) |
| **Object Detection** | YOLOv8-powered context-aware indexing |
| **GPU Accelerated** | CUDA, Apple MPS, or CPU fallback |
| **Beautiful TUI** | Terminal interface with real-time progress |
| **gRPC API** | Integrate into your pipelines |

### Pro Features (Coming Soon)

- Unlimited indexing (free tier: 5,000 images)
- S3/GCP/Azure ingestion
- Remote GPU server mode
- YOLO/COCO export

---

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Full installation guide |
| [Architecture](docs/architecture.md) | How Prism works |
| [Configuration](docs/configuration.md) | Customization options |
| [Benchmarks](docs/benchmarks.md) | Performance diagnostics |
| [API Reference](docs/api-reference.md) | gRPC integration |

---

## Tech Stack

- **Frontend:** Go + [Bubbletea](https://github.com/charmbracelet/bubbletea)
- **Backend:** Python + PyTorch
- **Models:** [YOLOv8](https://github.com/ultralytics/ultralytics) + [Google SigLIP](https://huggingface.co/google/siglip-so400m-patch14-384)
- **Storage:** SQLite + NumPy vectors

---

## License

Apache 2.0. See [LICENSE](LICENSE).

<p align="center">
  <sub>Built by <a href="https://github.com/sjanney">Shane Janney</a></sub>
</p>
