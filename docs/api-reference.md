# Prism gRPC API Reference

Prism exposes a gRPC API that allows you to integrate semantic search into your own tools and pipelines.

## Connection

**Default Endpoint:** `localhost:50051`

**Protocol:** gRPC (HTTP/2)

**Proto File:** [`proto/prism.proto`](../proto/prism.proto)

---

## Service Definition

```protobuf
service PrismService {
  rpc Index(IndexRequest) returns (stream IndexProgress) {}
  rpc Search(SearchRequest) returns (SearchResponse) {}
  rpc OpenResult(OpenRequest) returns (OpenResponse) {}
  rpc ConnectDatabase(ConnectDatabaseRequest) returns (ConnectDatabaseResponse) {}
  rpc GetStats(GetStatsRequest) returns (GetStatsResponse) {}
  rpc GetSystemInfo(GetSystemInfoRequest) returns (GetSystemInfoResponse) {}
  rpc ActivateLicense(ActivateLicenseRequest) returns (ActivateLicenseResponse) {}
  rpc PickFolder(PickFolderRequest) returns (PickFolderResponse) {}
}
```

---

## RPCs

### Index

**Description:** Index a folder of images. Returns a stream of progress updates.

**Request:**
```protobuf
message IndexRequest {
  string path = 1;  // Absolute path to folder
}
```

**Response (Stream):**
```protobuf
message IndexProgress {
  int64 current = 1;       // Current image number
  int64 total = 2;         // Total images found
  string status_message = 3;  // e.g., "Indexed image.jpg"
}
```

**Example (Python):**
```python
import grpc
import prism_pb2
import prism_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = prism_pb2_grpc.PrismServiceStub(channel)

request = prism_pb2.IndexRequest(path="/path/to/images")
for progress in stub.Index(request):
    print(f"{progress.current}/{progress.total}: {progress.status_message}")
```

---

### Search

**Description:** Search the indexed dataset with natural language.

**Request:**
```protobuf
message SearchRequest {
  string query_text = 1;  // e.g., "red car turning left"
}
```

**Response:**
```protobuf
message SearchResponse {
  repeated SearchResult results = 1;
}

message SearchResult {
  string path = 1;           // File path
  float confidence = 2;      // 0.0 to 1.0 similarity score
  string reasoning = 3;      // Match description
  string resolution = 4;     // e.g., "1920x1080"
  string file_size = 5;      // e.g., "2.4 MB"
  string date_modified = 6;  // ISO timestamp
  repeated string detected_objects = 7;
}
```

**Example (Python):**
```python
response = stub.Search(prism_pb2.SearchRequest(query_text="pedestrian at crosswalk"))
for result in response.results:
    print(f"{result.path}: {result.confidence:.2%}")
```

---

### GetStats

**Description:** Get statistics about the current dataset.

**Request:** Empty message.

**Response:**
```protobuf
message GetStatsResponse {
  DatasetMetadata metadata = 1;
}

message DatasetMetadata {
  int64 total_frames = 1;      // Number of indexed images
  int64 total_embeddings = 2;  // Number of vectors (images + crops)
  string last_indexed = 3;     // ISO timestamp
  string db_path = 4;          // Database file path
}
```

---

### GetSystemInfo

**Description:** Get system and model information.

**Response:**
```protobuf
message GetSystemInfoResponse {
  string device = 1;          // "cuda", "mps", or "cpu"
  string siglip_model = 2;    // Model status
  string yolo_model = 3;      // Model status
  string backend_version = 4; // e.g., "v2.3.1-stable"
  int32 cpu_count = 5;        // Number of CPU cores
  string memory_usage = 6;    // e.g., "8.2GB / 16.0GB"
  bool is_pro = 7;            // True if Pro is activated
}
```

---

### ConnectDatabase

**Description:** Connect to a different SQLite database.

**Request:**
```protobuf
message ConnectDatabaseRequest {
  string db_path = 1;  // Path to .db file
}
```

**Response:**
```protobuf
message ConnectDatabaseResponse {
  bool success = 1;
  string message = 2;
}
```

---

### OpenResult

**Description:** Open an image file in the system's default viewer.

**Request:**
```protobuf
message OpenRequest {
  string file_path = 1;
}
```

**Response:**
```protobuf
message OpenResponse {
  bool success = 1;
  string message = 2;
}
```

---

### ActivateLicense

**Description:** Activate a Prism Pro license.

**Request:**
```protobuf
message ActivateLicenseRequest {
  string license_key = 1;  // e.g., "PRISM-PRO-XXXX-XXXX"
}
```

**Response:**
```protobuf
message ActivateLicenseResponse {
  bool success = 1;
  string message = 2;
}
```

---

### PickFolder

**Description:** Open a native folder picker dialog.

**Request:**
```protobuf
message PickFolderRequest {
  string prompt = 1;  // Dialog title
}
```

**Response:**
```protobuf
message PickFolderResponse {
  bool success = 1;
  string path = 2;     // Selected folder path
  string message = 3;  // Error message if failed
}
```

---

## Generating Client Code

To generate client stubs for your language:

```bash
# Python
python -m grpc_tools.protoc -Iproto --python_out=. --grpc_python_out=. proto/prism.proto

# Go
protoc --go_out=. --go-grpc_out=. proto/prism.proto

# Other languages: See grpc.io/docs/languages/
```

---

## Error Handling

All RPCs may return standard gRPC error codes:

| Code | Meaning |
|------|---------|
| `UNAVAILABLE` | Backend not running (PSM-1001) |
| `DEADLINE_EXCEEDED` | Request timed out (PSM-1002) |
| `NOT_FOUND` | Path doesn't exist (PSM-4001) |
| `INTERNAL` | Server error (check backend.log) |

See [Error Codes](error-codes.md) for detailed troubleshooting.
