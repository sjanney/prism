# 🌈 Prism

### Semantic Search for Local Datasets (YOLO + SigLIP)

Prism is a high-performance, terminal-based tool that brings "Google Photos" style search to your local image datasets. It indexes your folders, detects objects (Cars, Pedestrians, Traffic Lights) using **YOLOv8**, and generates rich semantic embeddings with **SigLIP**.

![Prism Banner](https://via.placeholder.com/800x200?text=Prism+Search)

## ✨ Features

*   **Semantic Search**: Query your data with natural language (e.g., "red car under street light").
*   **Local-First**: No data ever leaves your machine. Everything runs on your metal.
*   **Object Detection**: Context-aware indexing using YOLOv8.
*   **Fast TUI**: A beautiful terminal interface built with Go and Bubbletea.
*   **Vector Search**: Uses cosine similarity over high-dimensional embeddings.

---

## 🚀 Quick Start

### Prerequisites

*   **Python 3.9+** (GPU recommended for indexing)
*   **Go 1.21+**
*   **Protoc** (for code generation)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sjanney/prism.git
   cd prism
   ```

2. **Install Dependencies**
   ```bash
   make install
   ```

3. **Build & Run**
   ```bash
   make build
   ./run_prism.sh
   ```

## 📦 Distribution

### Homebrew (Coming Soon)
We are working on bringing Prism to the official Homebrew core. For now, you can install it via our tap:
```bash
brew install sjanney/tap/prism
```

### Manual Installation
You can move the built binary and scripts to your `/usr/local/bin`:
```bash
make build
cp prism_app /usr/local/bin/prism
```

## 💡 Why Prism?

In the world of autonomous vehicles and robotics, we deal with petabytes of data. Traditional tools for exploring this data are either:
1.  **Cloud-based**: Slow, expensive, and require privacy-breaking uploads.
2.  **Greppable Metadata**: Limited to what's already tagged.

Prism allows you to find "un-tagged" edge cases like *"a dog crossing the road in the rain"* by understanding the visual content of every frame.

## 🛠️ Tech Stack

- **TUI Frontend**: [Go](https://go.dev/) + [Bubbletea](https://github.com/charmbracelet/bubbletea)
- **AI Backend**: [Python](https://www.python.org/) + [PyTorch](https://pytorch.org/)
- **Communication**: [gRPC](https://grpc.io/)
- **Models**: YOLOv8 (Detection) + Google SigLIP (Embeddings)

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.
