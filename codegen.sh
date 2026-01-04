#!/bin/bash

# Ensure we are in the directory where this script lives (prism/)
cd "$(dirname "$0")"

# Compile for Python Backend
echo "Generating Python gRPC code..."
# Check if python3 exists, else try python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

$PYTHON_CMD -m grpc_tools.protoc -Iproto --python_out=backend --grpc_python_out=backend proto/prism.proto || echo "Failed to generate Python code. Do you have grpcio-tools installed? (pip install grpcio-tools)"

# Compile for Go Frontend
echo "Generating Go gRPC code..."

# Ensure Go plugins are installed
if ! command -v protoc-gen-go &> /dev/null; then
    echo "protoc-gen-go not found. Installing..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
fi
if ! command -v protoc-gen-go-grpc &> /dev/null; then
    echo "protoc-gen-go-grpc not found. Installing..."
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
fi

# Add (go env GOPATH)/bin to PATH just in case
export PATH=$PATH:$(go env GOPATH)/bin

mkdir -p frontend/proto
protoc --go_out=frontend --go_opt=paths=source_relative \
    --go-grpc_out=frontend --go-grpc_opt=paths=source_relative \
    -I. proto/prism.proto || echo "Failed to generate Go code."

echo "Done."
