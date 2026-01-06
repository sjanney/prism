import logging
from typing import Generator
from plugins import IngestionSource
from config import config

logger = logging.getLogger(__name__)

class AzureIngestionSource(IngestionSource):
    @property
    def name(self) -> str:
        return "Azure Blob Storage"

    @property
    def description(self) -> str:
        return "Ingest images from Azure Blob Storage containers"

    def can_handle(self, path: str) -> bool:
        """Check if path is azure:// or https blob url and user is Pro."""
        is_azure = path.startswith("azure://") or (
            path.startswith("https://") and ".blob.core.windows.net" in path
        )
        
        if not is_azure:
            return False
            
        if not config.is_pro:
            logger.warning("Azure ingestion requested but user is not Pro.")
            return False
            
        return True

    def _get_client(self, container_url=None):
        from azure.storage.blob import BlobServiceClient
        
        creds = config.azure_creds
        conn_str = creds.get("connection_string")
        
        if not conn_str:
            # Try env vars or managed identity fallback if library supports it
            # But for now we rely on configured string
            return None

        if container_url:
            # Return ContainerClient directly if URL provided and we have creds
            # Parsing URL to get container name might be needed if using connection string
             pass

        return BlobServiceClient.from_connection_string(conn_str)

    def discover_files(self, path: str, max_files: int = 0) -> Generator[str, None, None]:
        """List blobs in Azure container."""
        try:
            # Client already loaded via _get_client()
            
            client = self._get_client()
            if not client:
                raise ValueError("Azure credentials not configured")

            # Parse container and prefix
            # azure://mycontainer/prefix/
            # https://account.blob.core.windows.net/mycontainer/prefix/
            
            container_name = ""
            prefix = ""
            
            if path.startswith("azure://"):
                parts = path.replace("azure://", "").split("/", 1)
                container_name = parts[0]
                prefix = parts[1] if len(parts) > 1 else ""
            elif "blob.core.windows.net" in path:
                # https://<account>.blob.core.windows.net/<container>/<prefix>
                # simplistic parsing
                path_parts = path.split(".blob.core.windows.net/")
                if len(path_parts) > 1:
                    remain = path_parts[1].split("/", 1)
                    container_name = remain[0]
                    prefix = remain[1] if len(remain) > 1 else ""

            if not container_name:
                raise ValueError(f"Could not parse container name from {path}")

            container_client = client.get_container_client(container_name)
            
            blobs_list = container_client.list_blobs(name_starts_with=prefix)

            count = 0
            for blob in blobs_list:
                name = blob.name
                if name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')):
                    # Reconstruct URL or use custom scheme
                    # Using azure:// scheme internally for consistency
                    yield f"azure://{container_name}/{name}"
                    count += 1
                    if max_files > 0 and count >= max_files:
                        return

        except Exception as e:
            logger.error(f"Azure discovery failed: {e}")
            raise

    def validate_credentials(self) -> bool:
        try:
            client = self._get_client()
            if not client: 
                return False
            # Try listing containers as a check
            next(client.list_containers(), None)
            return True
        except Exception as e:
            logger.error(f"Azure Validation failed: {e}")
            return False
