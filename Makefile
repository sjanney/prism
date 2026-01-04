.PHONY: build install clean backend frontend

# Default target
all: build

# Build the frontend binary
build:
	@echo "--- 🔄 Generating Proto Code ---"
	./codegen.sh
	@echo "--- 🔨 Building Frontend ---"
	cd frontend && go build -o ../prism_app .

# Install dependencies for both backend and frontend
install:
	@echo "--- 📦 Installing Python Dependencies ---"
	pip install -r backend/requirements.txt
	@echo "--- 📦 Installing Go Dependencies ---"
	cd frontend && go mod download

# Run the full application
run:
	./run_prism.sh

# Clean up binaries and generated files
clean:
	rm -f prism_app
	rm -f backend.log
	rm -rf frontend/proto/*.go
	rm -f backend/*_pb2*.py
