# Prism - Complete Technical Documentation

> **Prism** is a local-first, privacy-preserving visual search engine for autonomous vehicle datasets, built with an Open Core architecture.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Directory Structure](#directory-structure)
5. [Backend Components](#backend-components)
6. [Frontend Components](#frontend-components)
7. [Protocol Buffers & gRPC](#protocol-buffers--grpc)
8. [Licensing System](#licensing-system)
9. [Data Flow](#data-flow)
10. [Configuration](#configuration)
11. [Testing](#testing)
12. [CI/CD](#cicd)
13. [Deployment](#deployment)

---

## Project Overview

### What is Prism?

Prism is a **visual search engine** designed for autonomous vehicle (AV) datasets. It enables users to:

- **Index** large collections of images and video frames locally
- **Search** using natural language queries (e.g., "car turning left at intersection")
- **Detect** objects within images using YOLO
- **Preserve privacy** by running entirely on local hardware

### All Features Free

Prism is **completely free** with no feature restrictions:

| Feature | Status |
|---------|--------|
| Local indexing | ✓ Unlimited |
| Natural language search | ✓ |
| Object detection | ✓ |
| Video indexing | ✓ |
| S3 ingestion | ✓ |
| Azure Blob ingestion | ✓ |

> **Secret Features**: Enter a secret code in the hidden menu to unlock experimental features! 🔮

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PRISM ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐         gRPC          ┌──────────────────────┐    │
│  │   Go Frontend   │◄────────────────────►│    Python Backend     │    │
│  │   (Bubble Tea)  │      localhost:50051  │                      │    │
│  │                 │                       │  ┌────────────────┐  │    │
│  │  • TUI Renderer │                       │  │  LocalSearch   │  │    │
│  │  • Key Handler  │                       │  │    Engine      │  │    │
│  │  • gRPC Client  │                       │  │                │  │    │
│  └─────────────────┘                       │  │ • SigLIP Model │  │    │
│                                            │  │ • YOLO Model   │  │    │
│                                            │  └────────────────┘  │    │
│                                            │                      │    │
│                                            │  ┌────────────────┐  │    │
│                                            │  │    Database    │  │    │
│                                            │  │   (SQLite)     │  │    │
│                                            │  └────────────────┘  │    │
│                                            │                      │    │
│                                            │  ┌────────────────┐  │    │
│                                            │  │ Plugin System  │  │    │
│                                            │  │ • Local FS     │  │    │
│                                            │  │ • S3           │  │    │
│                                            │  │ • Azure        │  │    │
│                                            │  └────────────────┘  │    │
│                                            └──────────────────────┘    │
│                                                       │                │
│                                                       ▼                │
│                                            ┌──────────────────────┐    │
│                                            │    License API       │    │
│                                            │  (Cloudflare Worker) │    │
│                                            └──────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Language | Responsibility |
|-----------|----------|----------------|
| Frontend | Go | Terminal UI, user interaction, gRPC client |
| Backend | Python | ML inference, database, gRPC server |
| Proto | Protobuf | Service/message definitions |
| Licensing Worker | TypeScript | License validation, RSA signing |
| Database | SQLite | Frame metadata, embeddings storage |

---

## Technology Stack

### Backend (Python 3.11+)

| Technology | Purpose |
|------------|---------|
| **gRPC** | High-performance RPC framework for backend-frontend communication |
| **PyTorch** | Deep learning framework for model inference |
| **SigLIP** | Google's vision-language model for image embeddings (SO400M-patch14-384) |
| **YOLO v8** | Real-time object detection (Medium variant) |
| **SQLite** | Local database for embeddings and metadata |
| **Transformers** | Hugging Face library for SigLIP model |
| **Pillow** | Image loading and manipulation |
| **NumPy** | Vectorized operations for similarity search |
| **boto3** | AWS S3 SDK for cloud ingestion |
| **azure-storage-blob** | Azure Blob SDK |
| **cryptography** | RSA signature verification for licensing |

### Frontend (Go 1.21+)

| Technology | Purpose |
|------------|---------|
| **Bubble Tea** | Elm-inspired TUI framework |
| **Lip Gloss** | Styling and layout for terminal UI |
| **gRPC-Go** | gRPC client implementation |
| **protoc-gen-go** | Protocol buffer code generation |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **Cloudflare Workers** | Serverless license validation API |
| **Cloudflare KV** | Key-value storage for license data |
| **GitHub Actions** | CI/CD pipeline |
| **Protocol Buffers** | Interface definition language |

---

## Directory Structure

```
prism/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI configuration
│
├── admin-scripts/              # License administration tools
│   ├── admin.py                # CLI for license management
│   ├── admin_requirements.txt  # Admin script dependencies
│   └── README.md               # Admin documentation
│
├── assets/                     # Static assets
│   └── screenshot.png          # README screenshot
│
├── backend/                    # Python backend
│   ├── tests/                  # Unit tests (pytest)
│   │   ├── __init__.py
│   │   ├── test_config.py      # Config/license tests
│   │   └── test_database.py    # Database tests
│   │
│   ├── config.py               # Configuration & licensing
│   ├── database.py             # SQLite operations
│   ├── engine.py               # ML engine (SigLIP, YOLO)
│   ├── server.py               # gRPC server implementation
│   ├── plugins.py              # Plugin system
│   ├── local_ingestion.py      # Local file system ingestion
│   ├── s3_ingestion.py         # AWS S3 ingestion
│   ├── azure_ingestion.py      # Azure Blob ingestion
│   ├── video_utils.py          # Video frame extraction
│   ├── benchmark.py            # Performance benchmarking
│   ├── errors.py               # Structured error codes
│   ├── prism_pb2.py            # Generated protobuf code
│   ├── prism_pb2_grpc.py       # Generated gRPC code
│   ├── requirements.txt        # Python dependencies
│   └── test_client.py          # Basic gRPC test client
│
├── docs/                       # User documentation
│   ├── getting-started.md
│   ├── architecture.md
│   ├── configuration.md
│   ├── api-reference.md
│   ├── error-codes.md
│   └── benchmarks.md
│
├── frontend/                   # Go frontend
│   ├── main.go                 # TUI application
│   ├── go.mod                  # Go module definition
│   ├── go.sum                  # Dependency checksums
│   └── proto/                  # Generated Go protobuf code
│       ├── prism.pb.go
│       └── prism_grpc.pb.go
│
├── licensing-worker/           # Cloudflare Worker
│   ├── src/
│   │   └── index.ts            # Worker implementation
│   ├── wrangler.toml           # Cloudflare configuration
│   ├── package.json            # Node dependencies
│   └── tsconfig.json           # TypeScript config
│
├── proto/                      # Protocol definitions
│   └── prism.proto             # gRPC service/message definitions
│
├── codegen.sh                  # Protobuf code generation script
├── run_prism.sh                # Main application launcher
├── run_backend.sh              # Backend-only launcher
├── run_frontend.sh             # Frontend-only launcher
├── Makefile                    # Build automation
├── README.md                   # Project README
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # Open Source License
└── VERSION                     # Version number
```

---

## Backend Components

### 1. Engine (`engine.py`)

The **LocalSearchEngine** is the core ML component:

```python
class LocalSearchEngine:
    def __init__(self, use_fp16: bool = True):
        # Device detection (CUDA > MPS > CPU)
        self.device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        
        # Dynamic batch sizing for optimal GPU utilization
        self.optimal_batch_size = 32 if self.device == "cuda" else 16 if self.device == "mps" else 8
        
        # FP16 for faster inference (2x speedup on GPU)
        self.use_fp16 = use_fp16 and self.device in ["cuda", "mps"]
```

**Key Methods:**
- `compute_image_embedding(image)` - Single image → 1152-dim vector
- `compute_batch_embeddings(images)` - Batch of images → vectors
- `compute_text_embedding(text)` - Text query → 1152-dim vector
- `process_batch(files, db)` - Full pipeline: load → detect → embed → save
- `search(query, db)` - Vectorized cosine similarity search

**Models:**
- **SigLIP SO400M-patch14-384** - Vision-language model (384px input, 1152-dim embeddings)
- **YOLOv8m** - Object detection (80 COCO classes, focus on vehicles/people)

### 2. Database (`database.py`)

SQLite database with two main tables:

```sql
-- Frames table (image metadata)
CREATE TABLE frames (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,
    timestamp TEXT,
    source TEXT,
    scenario TEXT,
    detected_objects TEXT,    -- JSON array
    file_hash TEXT,           -- MD5 for deduplication
    source_type TEXT          -- local, s3, azure, video
);

-- Embeddings table (vector storage)
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    frame_id INTEGER,
    type TEXT,                -- image, object_crop
    vector BLOB,              -- NumPy array as bytes
    box TEXT,                 -- Bounding box JSON
    label TEXT,               -- YOLO class label
    confidence REAL           -- Detection confidence
);

-- Performance indexes
CREATE INDEX idx_frames_path ON frames(path);
CREATE INDEX idx_frames_hash ON frames(file_hash);
CREATE INDEX idx_embeddings_frame_id ON embeddings(frame_id);
```

**Key Methods:**
- `save_frame()` / `save_embedding()` - Persist data
- `get_column_vectors()` - Load all embeddings for search
- `get_metadata_by_ids()` - Retrieve frame details
- `file_exists_by_hash()` - Deduplication check
- `get_stats()` - Database statistics

### 3. Server (`server.py`)

gRPC server implementing the `PrismService`:

```python
class PrismServicer(prism_pb2_grpc.PrismServiceServicer):
    """gRPC service implementation."""
    
    def Index(self, request, context):
        """Stream indexing progress."""
        # 1. Resolve ingestion source (local, S3, Azure)
        # 2. Discover files with deduplication
        # 3. Batch process with progress updates
        # 4. Yield IndexProgress messages
    
    def Search(self, request, context):
        """Execute semantic search."""
        # 1. Compute text embedding
        # 2. Vectorized cosine similarity
        # 3. Return ranked results with metadata
    
    def ConnectDatabase(self, request, context):
        """Connect to SQLite database."""
```

### 4. Config (`config.py`)

Configuration and licensing management:

```python
class Config:
    # Config file: ~/.prism/config.yaml
    # Credentials: ~/.prism/credentials.yaml (chmod 600)
    # License cache: ~/.prism/license.cache
    
    @property
    def is_pro(self) -> bool:
        """Always True - all features are free."""
        return True
    
    @property
    def has_secret_features(self) -> bool:
        """Check if user unlocked secret features via license key."""
        info = self._get_license_info()
        return info.get("valid", False) and info.get("tier", "") in ["pro", "enterprise", "secret"]
    
    def _verify_signature(self, data: dict) -> bool:
        """RSA signature verification against embedded public key."""
```

### 5. Plugin System (`plugins.py`)

Extensible ingestion source system:

```python
class IngestionSource(ABC):
    """Base class for all ingestion sources."""
    
    @abstractmethod
    def can_ingest(self, path: str) -> bool: ...
    
    @abstractmethod
    def discover_files(self, path: str, max_files: int) -> Generator[str, None, None]: ...
    
    @abstractmethod
    def validate_credentials(self) -> bool: ...

# Registered sources:
# - LocalIngestionSource (always available)
# - S3IngestionSource (free)
# - AzureIngestionSource (free)
```

---

## Frontend Components

### Main Application (`main.go`)

The frontend is a **Bubble Tea** TUI application:

```go
type model struct {
    // State management
    state           state           // Dashboard, Search, Index, Settings...
    
    // gRPC client
    client          pb.PrismServiceClient
    
    // UI components
    searchInput     textinput.Model
    pathInput       textinput.Model
    progress        progress.Model
    spinner         spinner.Model
    
    // Data
    results         []SearchResult
    sysInfo         *pb.SystemInfo
    notifications   []Notification
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    // Handle keyboard input, gRPC responses, window resize
}

func (m model) View() string {
    // Render current state to terminal
}
```

**States:**
- `stateLoading` - Initial connection
- `stateHome` - Dashboard with menu
- `stateSearch` - Query input and results
- `stateIndex` - File indexing with progress
- `stateSettings` - System info
- `stateCloudConfig` - AWS/Azure credentials
- `statePro` - Secret features activation

---

## Protocol Buffers & gRPC

### Service Definition (`prism.proto`)

```protobuf
service PrismService {
    // Core operations
    rpc Index(IndexRequest) returns (stream IndexProgress) {}
    rpc Search(SearchRequest) returns (SearchResponse) {}
    rpc ConnectDatabase(DatabaseRequest) returns (StatusResponse) {}
    rpc GetStats(Empty) returns (DatasetStats) {}
    rpc GetSystemInfo(Empty) returns (SystemInfo) {}
    
    // License management
    rpc ActivateLicense(LicenseRequest) returns (LicenseResponse) {}
    
    // Cloud credentials (Pro)
    rpc SaveCloudCredentials(SaveCloudCredentialsRequest) returns (SaveCloudCredentialsResponse) {}
    rpc ValidateCloudCredentials(ValidateCloudCredentialsRequest) returns (ValidateCloudCredentialsResponse) {}
    
    // Benchmarking
    rpc RunBenchmark(BenchmarkRequest) returns (stream BenchmarkProgress) {}
}
```

### Key Messages

```protobuf
message SearchResult {
    string path = 1;
    float confidence = 2;
    string reasoning = 3;
    repeated string detected_objects = 4;
    string match_type = 5;  // "Full Image" or "Object Crop"
}

message IndexProgress {
    int64 current = 1;
    int64 total = 2;
    string status = 3;
    int64 skipped = 4;      // Duplicates skipped
    int32 eta_seconds = 5;  // Estimated time remaining
}
```

---

## Licensing System

### Architecture

```
┌──────────────┐     HTTPS      ┌─────────────────────┐
│   Backend    │───────────────►│  Cloudflare Worker  │
│  (Python)    │                │  (prism-licensing)  │
│              │◄───────────────│                     │
│  Verify RSA  │   Signed JSON  │  Sign with Private  │
│  Public Key  │                │  Key (RSA-2048)     │
└──────────────┘                └─────────────────────┘
                                         │
                                         ▼
                                ┌─────────────────────┐
                                │   Cloudflare KV     │
                                │   (License Store)   │
                                └─────────────────────┘
```

### Security Features

1. **RSA-2048 Signatures** - All license responses are cryptographically signed
2. **Public key embedded** in backend (private key in Cloudflare secret)
3. **HMAC cache integrity** - Detect local cache tampering
4. **Secret features** - `has_secret_features` unlocks hidden functionality
5. **Rate limiting** - 20 requests/minute per IP
6. **Offline fallback** - Signed cache works without network

### License Flow

```
1. User enters license key in TUI
2. Backend calls /validate?key=XXXX
3. Worker validates key in KV store
4. Worker signs response with private RSA key
5. Backend verifies signature with public key
6. Valid license cached locally with HMAC
7. Future checks use offline cache
```

---

## Data Flow

### Indexing Pipeline

```
┌─────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────┐
│  Files  │───►│  Discovery │───►│ Dedup Check │───►│  Batch   │
│(Local/  │    │ (Glob/S3)  │    │ (File Hash) │    │ Loader   │
│ Cloud)  │    └────────────┘    └─────────────┘    └──────────┘
└─────────┘                                               │
                                                          ▼
┌─────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────┐
│  Save   │◄───│  Embed     │◄───│ YOLO Detect │◄───│  Images  │
│(SQLite) │    │ (SigLIP)   │    │ (Crops)     │    │ (PIL)    │
└─────────┘    └────────────┘    └─────────────┘    └──────────┘
```

### Search Pipeline

```
┌─────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────┐
│  Query  │───►│ Text Embed │───►│  Load All   │───►│ Cosine   │
│ (Text)  │    │ (SigLIP)   │    │  Vectors    │    │ Simil.   │
└─────────┘    └────────────┘    └─────────────┘    └──────────┘
                                                          │
                                                          ▼
                                 ┌─────────────┐    ┌──────────┐
                                 │  Metadata   │◄───│   Top K  │
                                 │  Lookup     │    │  Results │
                                 └─────────────┘    └──────────┘
```

---

## Configuration

### Config File (`~/.prism/config.yaml`)

```yaml
backend_port: 50051
default_db: /Users/you/.prism/prism.db
developer_mode: false
device: auto  # auto, cuda, mps, cpu
license_api: https://prism-licensing.prism-sjanney.workers.dev
license_key: PRISM-PRO-XXXX-XXXX-XXXX-XXXX
max_free_images: 5000

models:
  siglip: google/siglip-so400m-patch14-384
  yolo: yolov8m.pt

video:
  enabled: true
  frames_per_second: 1.0
  max_frames_per_video: 300
```

### Credentials File (`~/.prism/credentials.yaml`)

```yaml
# chmod 600 for security
aws:
  access_key: AKIAIOSFODNN7EXAMPLE
  secret_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  region: us-east-1

azure:
  connection_string: DefaultEndpointsProtocol=https;AccountName=...
```

---

## Testing

### Unit Tests

```bash
# Run all tests
cd backend && pytest tests/ -v

# Test coverage:
# - test_config.py (15 tests) - Config, licensing, cache integrity
# - test_database.py (12 tests) - Schema, hashing, source detection
```

### Integration Test

```bash
# Basic gRPC connectivity test
cd backend && python test_client.py
```

---

## CI/CD

### GitHub Actions (`.github/workflows/ci.yml`)

```yaml
jobs:
  backend:
    - Install Python 3.11
    - pip install requirements.txt
    - ruff check (linting)
    - Import check
    - pytest tests/ (unit tests)
  
  frontend:
    - Install Go 1.21
    - Generate protobuf
    - gofmt check
    - go build
  
  proto-sync:
    - Regenerate proto files
    - Check for uncommitted changes
```

---

## Deployment

### Local Development

```bash
# Install dependencies
pip install -r backend/requirements.txt
cd frontend && go mod download

# Generate protobuf code
./codegen.sh

# Run application
./run_prism.sh
```

### Licensing Worker

```bash
cd licensing-worker
npm install
npx wrangler secret put PRIVATE_KEY_PEM
npx wrangler deploy
```

### Production Release

```bash
# Build frontend binary
cd frontend && go build -o ../prism_app .

# Version bump
echo "1.1.0" > VERSION

# Tag and push
git tag v1.1.0
git push origin v1.1.0
```

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Indexing speed | ~15 images/sec (M1 Pro) |
| Search latency | ~50ms (10k vectors) |
| Memory usage | ~2GB (model loaded) |
| Database size | ~10KB per image |
| Embedding dimension | 1152 (SigLIP) |

### Optimizations

- **FP16 inference** - 2x faster on GPU
- **Dynamic batch sizing** - 8-32 based on device
- **Parallel file loading** - 8 worker threads
- **Vectorized cosine similarity** - NumPy broadcasting
- **Deduplication** - Skip already-indexed files

---

## License

Prism is licensed under the **Server Side Public License (SSPL)**. See [LICENSE](LICENSE) for details.

---

*Last updated: January 2026*
