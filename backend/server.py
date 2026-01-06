import grpc
from concurrent import futures
import os
import sys
import subprocess
import platform
import logging
import time


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

# Cloud Plugins (if dependencies exist)
try:
    from s3_ingestion import S3IngestionSource
    plugin_manager.register_ingestion_source(S3IngestionSource())
except ImportError:
    pass

try:
    from azure_ingestion import AzureIngestionSource
    plugin_manager.register_ingestion_source(AzureIngestionSource())
except ImportError:
    pass

plugin_manager.load_plugins()

class PrismServicer(prism_pb2_grpc.PrismServiceServicer):
    def __init__(self):
        self.db = Database()
        self.engine = LocalSearchEngine()
        self.benchmarker = Benchmarker(self.engine, self.db)

    def Index(self, request, context):
        root_path = request.path
        start_time = time.time()
        
        # 1. Resolve Ingestion Source
        ingestor = plugin_manager.get_ingestion_source_for_path(root_path)
        
        if not ingestor:
            if root_path.startswith("s3://"):
                 if not config.is_pro:
                     context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                     context.set_details("S3 ingestion is a Pro feature.")
                     return
                 context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                 context.set_details("S3 plugin not loaded or credentials missing.")
                 return
            
            if root_path.startswith("azure://") or "blob.core.windows.net" in root_path:
                 if not config.is_pro:
                     context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                     context.set_details("Azure ingestion is a Pro feature.")
                     return
                 context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                 context.set_details("Azure plugin not loaded or credentials missing.")
                 return
            
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"[PSM-4001] Path not found or no suitable ingestor: {root_path}")
            return
        
        logger.info(f"Using ingestor: {ingestor.name} for {root_path}")

        # 2. Discovery Phase
        max_files = 0 if config.is_pro else config.settings['max_free_images']
        files_to_process = []
        
        try:
             limit = max_files if max_files > 0 else 1_000_000 
             for f in ingestor.discover_files(root_path, max_files=limit):
                 files_to_process.append(f)
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Discovery failed: {str(e)}")
            return

        total_files = len(files_to_process)
        
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

        # 3. Batch Processing phase with deduplication tracking
        # Use engine's optimal batch size for the device (8-32)
        BATCH_SIZE = self.engine.optimal_batch_size
        logger.info(f"Using batch size: {BATCH_SIZE} for {self.engine.device}")
        
        processed_count = 0
        skipped_count = 0
        error_count = 0
        batch_start_time = time.time()
        
        for i in range(0, len(files_to_process), BATCH_SIZE):
            batch_files = files_to_process[i : i + BATCH_SIZE]
            
            try:
                # Pass db for deduplication checks
                batch_results = self.engine.process_batch(batch_files, db_connection=self.db)
                
                for res in batch_results:
                    if res.get('skipped', False):
                        skipped_count += 1
                        reason = res.get('reason', 'unknown')
                        if reason == 'duplicate':
                            status_msg = f"Skipped (duplicate): {os.path.basename(res['path'])}"
                        else:
                            error_count += 1
                            status_msg = f"Error: {os.path.basename(res['path'])}"
                    else:
                        # Save to database with file hash
                        self.db.save_frame_and_embeddings(
                            res["path"], 
                            res["width"], 
                            res["height"], 
                            res["embeddings"],
                            file_hash=res.get("file_hash")
                        )
                        status_msg = f"Indexed: {os.path.basename(res['path'])}"
                    
                    processed_count += 1
                    
                    # Calculate ETA
                    elapsed = time.time() - start_time
                    if processed_count > 0:
                        eta_seconds = int((elapsed / processed_count) * (total_files - processed_count))
                    else:
                        eta_seconds = 0
                    
                    yield prism_pb2.IndexProgress(
                        current=processed_count,
                        total=total_files,
                        status_message=status_msg,
                        skipped=skipped_count,
                        eta_seconds=eta_seconds
                    )
                
                self.engine.invalidate_cache()

            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                error_count += 1
                yield prism_pb2.IndexProgress(
                    current=processed_count,
                    total=total_files,
                    status_message=f"Batch Error: {str(e)}",
                    skipped=skipped_count
                )
        
        # Final summary
        elapsed_total = time.time() - start_time
        yield prism_pb2.IndexProgress(
            current=total_files,
            total=total_files,
            status_message=f"Complete! {processed_count - skipped_count} indexed, {skipped_count} skipped, {error_count} errors ({elapsed_total:.1f}s)",
            skipped=skipped_count
        )


        
    # ... Helper to avoid deleting large chunks ...
    # Wait, I should use multi_replace or use a better insertion point.
    # The prompt asked me to replace up to line 373. I need to be precise.
    # The user instruction was to register plugins and implement RPCs.
    # I should insert the registration at the top and the RPCs at the bottom of the class.

    def SaveCloudCredentials(self, request, context):
        logger.info(f"Saving credentials for {request.provider}")
        try:
            creds = config.load_credentials()
            
            if request.provider == "aws":
                creds["aws"] = {
                    "access_key": request.aws_access_key,
                    "secret_key": request.aws_secret_key,
                    "region": request.aws_region
                }
            elif request.provider == "azure":
                 creds["azure"] = {
                     "connection_string": request.azure_connection_string
                 }
            else:
                 return prism_pb2.SaveCloudCredentialsResponse(success=False, message="Unknown provider")
            
            config.save_credentials(creds)
            return prism_pb2.SaveCloudCredentialsResponse(success=True, message="Credentials saved securely.")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            return prism_pb2.SaveCloudCredentialsResponse(success=False, message=str(e))

    def GetCloudCredentials(self, request, context):
        creds = config.load_credentials()
        
        if request.provider == "aws":
            aws = creds.get("aws", {})
            key = aws.get("access_key", "")
            masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
            return prism_pb2.GetCloudCredentialsResponse(
                configured=bool(key),
                aws_access_key_masked=masked if key else "",
                aws_region=aws.get("region", "")
            )
        elif request.provider == "azure":
            azure = creds.get("azure", {})
            conn = azure.get("connection_string", "")
            # Extract AccountName from connection string
            account = "Unknown"
            if "AccountName=" in conn:
                for part in conn.split(";"):
                    if part.startswith("AccountName="):
                        account = part.split("=", 1)[1]
            
            return prism_pb2.GetCloudCredentialsResponse(
                configured=bool(conn),
                azure_account_name=account if conn else ""
            )
        
        return prism_pb2.GetCloudCredentialsResponse(configured=False)

    def ValidateCloudCredentials(self, request, context):
        # We can use the ingestion source logic to validate
        try:
            if request.provider == "aws":
                from s3_ingestion import S3IngestionSource
                source = S3IngestionSource()
                if source.validate_credentials():
                     return prism_pb2.ValidateCloudCredentialsResponse(success=True, message="AWS connection successful!")
                else:
                     return prism_pb2.ValidateCloudCredentialsResponse(success=False, message="Validation failed. Check credentials.")
            
            elif request.provider == "azure":
                from azure_ingestion import AzureIngestionSource
                source = AzureIngestionSource()
                if source.validate_credentials():
                     return prism_pb2.ValidateCloudCredentialsResponse(success=True, message="Azure connection successful!")
                else:
                     return prism_pb2.ValidateCloudCredentialsResponse(success=False, message="Validation failed. Check connection string.")

        except Exception as e:
            return prism_pb2.ValidateCloudCredentialsResponse(success=False, message=str(e))
            
        return prism_pb2.ValidateCloudCredentialsResponse(success=False, message="Unknown provider")


    def Search(self, request, context):
        query = request.query_text
        logger.info(f"Searching for: {query}")
        
        search_start = time.time()
        
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
                        size_bytes = os.path.getsize(path)
                        file_size = f"{size_bytes / 1024:.1f} KB"
                        if size_bytes > 1024 * 1024:
                            file_size = f"{size_bytes / (1024 * 1024):.1f} MB"
                    except Exception as meta_e:
                        logger.warning(f"Metadata extraction failed for {path}: {meta_e}")

                # Include detected objects from the search result
                detected_objects = res.get('detected_objects', [])
                
                response_results.append(prism_pb2.SearchResult(
                    path=path,
                    confidence=res['confidence'],
                    reasoning=res['reasoning'],
                    resolution=resolution,
                    file_size=file_size,
                    date_modified=date_mod,
                    detected_objects=detected_objects,
                    match_type=res.get('match_type', 'full_image')
                ))
            
            search_time = time.time() - search_start
            logger.info(f"Search completed in {search_time:.3f}s, returning {len(response_results)} results")
                
            return prism_pb2.SearchResponse(
                results=response_results,
                search_time_ms=int(search_time * 1000),
                total_count=len(response_results)
            )
            
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
                developer_mode=config.settings.get('developer_mode', False),
                license_email=config.license_email,
                license_expires=config.license_expires
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
                developer_mode=False,
                license_email="",
                license_expires=""
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


def start_license_checker():
    """Background thread to validate license periodically."""
    import threading
    
    def check_loop():
        logger.info("Starting license validation loop...")
        while True:
            try:
                # Force validation by checking property
                # If cache is expired (1 hour), this triggers an API call
                is_valid = config.is_pro
                email = config.license_email
                logger.info(f"Periodic license check: Valid={is_valid}, Email={email}")
            except Exception as e:
                logger.error(f"License check failed: {e}")
            
            # Check every hour + 5 minutes to ensure we hit the cache expiry
            time.sleep(3900)

    thread = threading.Thread(target=check_loop, daemon=True)
    thread.start()

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
    
    # Start background tasks
    start_license_checker()
    
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()

