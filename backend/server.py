import grpc
from concurrent import futures
import os
import sys
import subprocess
import platform
import logging

# Add current directory to path so imports work if running from backend/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import prism_pb2
    import prism_pb2_grpc
except ImportError:
    # Fallback if generated files are not yet in path or distinct folder
    logging.warning("Protobuf modules not found directly. Run proto generation first.")
    # Assuming they will be here eventually.
    pass

from database import Database
from engine import LocalSearchEngine
from config import config
from plugins import plugin_manager
from benchmark import Benchmarker
import local_ingestion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Plugins
local_ingestion.register()
plugin_manager.load_plugins()

class PrismServicer(prism_pb2_grpc.PrismServiceServicer):
    def __init__(self):
        self.db = Database()
        self.engine = LocalSearchEngine()
        self.benchmarker = Benchmarker(self.engine, self.db)

    def Index(self, request, context):
        root_path = request.path
        
        # 1. Resolve Ingestion Source
        ingestor = plugin_manager.get_ingestion_source_for_path(root_path)
        
        if not ingestor:
            if root_path.startswith("s3://") or root_path.startswith("gs://"):
                 context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                 context.set_details("[PSM-5003] Cloud ingestion requires Prism Pro. Upgrade to enable S3/GCP support.")
                 return
            
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"[PSM-4001] Path not found or no suitable ingestor: {root_path}")
            return

        logger.info(f"Using ingestor: {ingestor.name} for {root_path}")

        # 2. Discovery Phase
        max_files = 0 if config.is_pro else config.settings['max_free_images']
        files_to_process = []
        
        # We collect all first to count (for progress bar), though scraping huge buckets might need streaming.
        # For now, list-then-process is safer for the progress bar.
        try:
             # If not pro, we cap discovery early to avoid long waits
             limit = max_files if max_files > 0 else 1_000_000 
             
             for f in ingestor.discover_files(root_path, max_files=limit):
                 files_to_process.append(f)
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Discovery failed: {str(e)}")
            return

        total_files = len(files_to_process)
        
        # Freemium Limit Check (Redundant but safe)
        if not config.is_pro and total_files >= config.settings['max_free_images']:
            logger.warning(f"Free version limit hit/reached. Indexed {total_files} items.")
            yield prism_pb2.IndexProgress(
                current=0,
                total=total_files,
                status_message=f"NOTICE: Free limit ({config.settings['max_free_images']}). Upgrade for unlimited."
            )

        if total_files == 0:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"[PSM-4002] No images found in: {root_path}")
            return

        logger.info(f"Processing {total_files} images from {root_path}")

        # 3. Batch Processing phase
        BATCH_SIZE = 8
        processed_count = 0

        for i in range(0, len(files_to_process), BATCH_SIZE):
            batch_files = files_to_process[i : i + BATCH_SIZE]
            
            try:
                # Returns list of dicts: {path, width, height, embeddings}
                batch_results = self.engine.process_batch(batch_files)
                
                for res in batch_results:
                    if res.get("embeddings"):
                        self.db.save_frame_and_embeddings(
                            res["path"], 
                            res["width"], 
                            res["height"], 
                            res["embeddings"]
                        )
                    processed_count += 1
                    
                    yield prism_pb2.IndexProgress(
                        current=processed_count,
                        total=total_files,
                        status_message=f"Indexed {os.path.basename(res['path'])}"
                    )
                
                # Invalidate cache periodically, or at end
                self.engine.invalidate_cache()

            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                yield prism_pb2.IndexProgress(
                    current=processed_count,
                    total=total_files,
                    status_message=f"Batch Error: {str(e)}"
                )

    def Search(self, request, context):
        query = request.query_text
        logger.info(f"Searching for: {query}")
        
        try:
            results = self.engine.search(query, self.db)
            
            response_results = []
            for res in results:
                path = res['path']
                
                # Use DB metadata for resolution and indexed date
                resolution = f"{res.get('width', 0)}x{res.get('height', 0)}"
                date_mod = res.get('indexed_at', "Unknown")
                file_size = "Unknown"
                
                if os.path.exists(path):
                    try:
                        # Size is quick to check
                        size_bytes = os.path.getsize(path)
                        file_size = f"{size_bytes / 1024:.1f} KB"
                        if size_bytes > 1024 * 1024:
                            file_size = f"{size_bytes / (1024 * 1024):.1f} MB"
                            
                    except Exception as meta_e:
                        logger.warning(f"Metadata extraction failed for {path}: {meta_e}")

                response_results.append(prism_pb2.SearchResult(
                    path=path,
                    confidence=res['confidence'],
                    reasoning=res['reasoning'],
                    resolution=resolution,
                    file_size=file_size,
                    date_modified=date_mod,
                    detected_objects=[] 
                ))
                
            return prism_pb2.SearchResponse(results=response_results)
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return prism_pb2.SearchResponse()

    def OpenResult(self, request, context):
        file_path = request.file_path
        logger.info(f"Opening file: {file_path}")
        
        try:
            if not os.path.exists(file_path):
                return prism_pb2.OpenResponse(success=False, message="File not found")

            system_platform = platform.system()
            
            if system_platform == 'Darwin':       # macOS
                subprocess.run(['open', file_path], check=True)
            elif system_platform == 'Windows':    # Windows
                os.startfile(file_path)
            elif system_platform == 'Linux':      # Linux
                subprocess.run(['xdg-open', file_path], check=True)
            else:
                return prism_pb2.OpenResponse(success=False, message=f"Unsupported platform: {system_platform}")

            return prism_pb2.OpenResponse(success=True, message="File opened")
            
        except Exception as e:
            return prism_pb2.OpenResponse(success=False, message=str(e))

    def ConnectDatabase(self, request, context):
        db_path = request.db_path
        logger.info(f"Connecting to database: {db_path}")
        try:
            self.db = Database(db_path)
            return prism_pb2.ConnectDatabaseResponse(success=True, message=f"Connected to {db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database {db_path}: {e}")
            return prism_pb2.ConnectDatabaseResponse(success=False, message=str(e))

    def GetSystemInfo(self, request, context):
        try:
            # Gather system info
            import psutil
            mem = psutil.virtual_memory()
            mem_usage = f"{mem.used / (1024**3):.1f}GB / {mem.total / (1024**3):.1f}GB"
            
            return prism_pb2.GetSystemInfoResponse(
                device=self.engine.device,
                siglip_model="SigLIP-SO400M (Lazy Loaded)" if self.engine.model is None else "SigLIP-SO400M (Active)",
                yolo_model="YOLOv8-Medium (Lazy Loaded)" if self.engine.yolo is None else "YOLOv8-Medium (Active)",
                backend_version="v2.3.1-stable",
                cpu_count=os.cpu_count(),
                memory_usage=mem_usage,
                is_pro=config.is_pro,
                developer_mode=config.settings.get('developer_mode', False)
            )
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return prism_pb2.GetSystemInfoResponse(
                device="unknown",
                siglip_model="error",
                yolo_model="error",
                backend_version="error",
                memory_usage="error",
                is_pro=False,
                developer_mode=False
            )

    def ActivateLicense(self, request, context):
        key = request.license_key
        logger.info(f"Attempting to activate license: {key}")
        
        # Simple validation for demo
        if key.startswith("PRISM-PRO-"):
            config.settings['license_key'] = key
            config.save()
            return prism_pb2.ActivateLicenseResponse(success=True, message="Prism Pro Activated! Thank you for your support.")
        else:
            return prism_pb2.ActivateLicenseResponse(success=False, message="Invalid license key. Keys start with 'PRISM-PRO-'.")

    def PickFolder(self, request, context):
        logger.info("Opening native folder picker...")
        try:
            system_platform = platform.system()
            if system_platform == 'Darwin':
                # macOS AppleScript
                cmd = ["osascript", "-e", f'POSIX path of (choose folder with prompt "{request.prompt}")']
                result = subprocess.check_output(cmd).decode('utf-8').strip()
                return prism_pb2.PickFolderResponse(success=True, path=result)
            elif system_platform == 'Windows':
                # Windows PowerShell
                ps_cmd = f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); $objForm = New-Object System.Windows.Forms.FolderBrowserDialog; $objForm.Description = '{request.prompt}'; if($objForm.ShowDialog() -eq 'OK') {{ $objForm.SelectedPath }}"
                cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
                result = subprocess.check_output(cmd).decode('utf-8').strip()
                if result:
                    return prism_pb2.PickFolderResponse(success=True, path=result)
                else:
                    return prism_pb2.PickFolderResponse(success=False, message="Selection cancelled")
            else:
                return prism_pb2.PickFolderResponse(success=False, message=f"Native picker not supported on {system_platform}")
        except Exception as e:
            logger.error(f"Folder picker failed: {e}")
            return prism_pb2.PickFolderResponse(success=False, message=str(e))

    def GetStats(self, request, context):
        try:
            stats = self.db.get_stats()
            # Handle potential None if never indexed
            last = stats['last_indexed'] if stats['last_indexed'] else "Never"
            
            return prism_pb2.GetStatsResponse(
                metadata=prism_pb2.DatasetMetadata(
                    total_frames=stats['total_frames'],
                    total_embeddings=stats['total_embeddings'],
                    last_indexed=str(last),
                    db_path=stats['db_path']
                )
            )
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return prism_pb2.GetStatsResponse()

    def RunBenchmark(self, request, context):
        """Run a full benchmark and stream progress updates."""
        sample_path = request.sample_path if request.sample_path else "data/sample"
        logger.info(f"Running benchmark with sample path: {sample_path}")
        
        try:
            for progress in self.benchmarker.run_full_benchmark(sample_path):
                yield prism_pb2.BenchmarkProgress(
                    phase=progress.get("phase", ""),
                    current=progress.get("current", 0),
                    total=progress.get("total", 0),
                    message=progress.get("message", "")
                )
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))

    def GetBenchmarkReport(self, request, context):
        """Return the last benchmark report."""
        report = self.benchmarker.get_last_report()
        
        if not report:
            return prism_pb2.BenchmarkReport(
                timestamp="",
                prism_version="",
                device="",
                os=""
            )
        
        def to_proto_metric(m):
            return prism_pb2.BenchmarkMetric(
                name=m.get("name", ""),
                value=m.get("value", 0.0),
                unit=m.get("unit", ""),
                context=m.get("context", "")
            )
        
        return prism_pb2.BenchmarkReport(
            timestamp=report.timestamp,
            prism_version=report.prism_version,
            device=report.device,
            os=report.os,
            indexing_metrics=[to_proto_metric(m) for m in report.indexing_metrics],
            search_metrics=[to_proto_metric(m) for m in report.search_metrics],
            system_metrics=[to_proto_metric(m) for m in report.system_metrics]
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # We delay adding the servicer until we are sure imports worked, or we handle ImportError above
    # Assuming successful import for runtime:
    try:
        prism_pb2_grpc.add_PrismServiceServicer_to_server(PrismServicer(), server)
    except NameError:
        logger.error("Could not add servicer - protobuf modules likely missing.")
        return

    server.add_insecure_port('[::]:50051')
    logger.info("Server starting on port 50051...")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
