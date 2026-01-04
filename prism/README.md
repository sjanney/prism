# Prism
### Local Semantic Search for AV Datasets (YOLO + SigLIP)

Prism is an open-source tool designed to bring "Google Photos" style search to your local autonomous vehicle datasets. It indexes your raw drive folders, using **YOLOv8** to detect objects (Cars, Pedestrians, Traffic Lights) and **SigLIP** to generate rich semantic embeddings. 

![Banner](https://via.placeholder.com/800x200?text=Prism+Banner)

## 🚀 Installation & Usage

### 1. Backend (Python/AI)
The brain of Prism runs locally.
```bash
cd backend
pip install -r requirements.txt
# Run the server
python server.py
```

### 2. Frontend (Go TUI)
A lightweight Terminal User Interface to interact with your data.
```bash
cd frontend
go run .
```

### 3. Usage
1.  **Index**: Point Prism to a folder of images. It will crunch through them (GPU recommended).
2.  **Search**: Type queries like "red tesla turning left" or "pedestrian extending arm".
3.  **Explore**: Arrow key through results, hit Enter to open the raw file.

## 💡 Why I built this
As a Data Engineer working with AV data, I found myself constantly `grep`ing through logs or manually scrolling through thousands of images to find specific edge cases (e.g., "construction cones at night"). Cloud solutions are too slow to upload terabytes of raw data to, and existing local tools lacked semantic understanding.

Prism bridges that gap by running SOTA vision models locally on your metal, giving you instant semantic search over your dataset without data leaving your machine.

## 🛠️ Stack
*   **Frontend**: Go (Bubbletea TUI)
*   **Backend**: Python (gRPC)
*   **AI**: 
    *   **YOLOv8** (Object Detection/Cropping)
    *   **Google SigLIP** (semantic embeddings)
*   **Storage**: SQLite + Vector Embeddings (JSON/Blob)
