import logging
import boto3
from typing import Generator
from plugins import IngestionSource
from config import config

logger = logging.getLogger(__name__)

class S3IngestionSource(IngestionSource):
    @property
    def name(self) -> str:
        return "AWS S3"

    @property
    def description(self) -> str:
        return "Ingest images from AWS S3 buckets"

    def can_handle(self, path: str) -> bool:
        """Check if path is s3:// and user is Pro."""
        if not path.startswith("s3://"):
            return False
            
        if not config.is_pro:
            logger.warning("S3 ingestion requested but user is not Pro.")
            return False
            
        return True

    def _get_client(self):
        creds = config.aws_creds
        if not creds:
            # Fallback to env vars/profile
            return boto3.client('s3')
        
        return boto3.client(
            's3',
            aws_access_key_id=creds.get('access_key'),
            aws_secret_access_key=creds.get('secret_key'),
            region_name=creds.get('region')
        )

    def discover_files(self, path: str, max_files: int = 0) -> Generator[str, None, None]:
        """List objects in S3 bucket."""
        try:
            s3 = self._get_client()
            
            # Parse bucket and prefix
            # s3://my-bucket/prefix/ -> bucket=my-bucket, prefix=prefix/
            parts = path.replace("s3://", "").split("/", 1)
            bucket = parts[0]
            prefix = parts[1] if len(parts) > 1 else ""

            paginator = s3.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

            count = 0
            for page in page_iterator:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith(('/', '')): # Skip directories
                        continue
                        
                    # Filter for images
                    if key.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')):
                        yield f"s3://{bucket}/{key}"
                        count += 1
                        if max_files > 0 and count >= max_files:
                            return

        except Exception as e:
            logger.error(f"S3 discovery failed: {e}")
            raise

    def validate_credentials(self) -> bool:
        """Validate AWS credentials using STS."""
        try:
            creds = config.aws_creds
            if creds:
                sts = boto3.client(
                    'sts',
                    aws_access_key_id=creds.get('access_key'),
                    aws_secret_access_key=creds.get('secret_key'),
                    region_name=creds.get('region')
                )
            else:
                sts = boto3.client('sts')
            
            sts.get_caller_identity()
            return True
        except Exception as e:
            logger.error(f"S3 Validation failed: {e}")
            return False
