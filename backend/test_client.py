import grpc
import sys
import os

# Ensure we can import the generated protobufs
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# These imports will fail until codegen.sh is run
try:
    import prism_pb2
    import prism_pb2_grpc
except ImportError:
    print("Error: Could not import generated protobufs. Did you run './prism/codegen.sh'?")
    sys.exit(1)

def run():
    print("Connecting to Prism server at localhost:50051...")
    try:
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = prism_pb2_grpc.PrismServiceStub(channel)
            
            # 1. Connect Database
            print("\n--- Testing ConnectDatabase ---")
            db_resp = stub.ConnectDatabase(prism_pb2.ConnectDatabaseRequest(db_path="prism_test.db"))
            print(f"Connected: {db_resp.success}, Message: {db_resp.message}")

            # 2. Get Stats
            print("\n--- Testing GetStats ---")
            stats = stub.GetStats(prism_pb2.GetStatsRequest())
            print("Stats Response:")
            print(f"  Total Frames: {stats.metadata.total_frames}")
            print(f"  Total Embeddings: {stats.metadata.total_embeddings}")
            print(f"  Last Indexed: {stats.metadata.last_indexed}")
            print(f"  DB Path: {stats.metadata.db_path}")

            # 3. Simple Search
            print("\n--- Testing Search (Ping) ---")
            response = stub.Search(prism_pb2.SearchRequest(query_text="ping"))
            print(f"Search successfully returned {len(response.results)} results (expected 0 if empty DB).")
            
    except grpc.RpcError as e:
        print(f"gRPC Error: {e.code()} - {e.details()}")
        print("Is the server running? (python prism/backend/server.py)")

if __name__ == '__main__':
    run()
