"""
Storage client for Local/S3/MinIO
"""
from pathlib import Path
from config import get_settings
from loguru import logger
import os

settings = get_settings()


class StorageClient:
    """Object storage client (Local/S3/MinIO)"""
    
    def __init__(self):
        if settings.storage_type == "local":
            # Use /tmp for Vercel (read-only filesystem)
            if os.getenv("VERCEL"):
                self.storage_path = Path("/tmp") / "storage"
            else:
                self.storage_path = Path(settings.storage_path)
            
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using local storage: {self.storage_path}")
        
        elif settings.storage_type == "s3":
            try:
                import boto3
                from botocore.exceptions import ClientError
                self.client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                self.bucket = settings.s3_bucket_name
                logger.info(f"Using S3 storage: {self.bucket}")
            except ImportError:
                raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        else:
            raise NotImplementedError(f"Storage type {settings.storage_type} not yet implemented")
    
    def upload(self, file_content: bytes, object_key: str) -> str:
        """
        Upload file to storage
        
        Returns the storage URL
        """
        try:
            if settings.storage_type == "local":
                file_path = self.storage_path / object_key
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(file_content)
                url = str(file_path)
                logger.info(f"Saved to local storage: {url}")
                return url
            
            elif settings.storage_type == "s3":
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=object_key,
                    Body=file_content
                )
                url = f"s3://{self.bucket}/{object_key}"
                logger.info(f"Uploaded to S3: {url}")
                return url
            
        except Exception as e:
            logger.error(f"Storage upload error: {e}")
            raise
    
    def download(self, object_key: str) -> bytes:
        """Download file from storage"""
        try:
            if settings.storage_type == "local":
                file_path = self.storage_path / object_key
                return file_path.read_bytes()
            
            elif settings.storage_type == "s3":
                response = self.client.get_object(
                    Bucket=self.bucket,
                    Key=object_key
                )
                return response['Body'].read()
            
        except Exception as e:
            logger.error(f"Storage download error: {e}")
            raise
    
    def delete(self, object_key: str):
        """Delete file from storage"""
        try:
            if settings.storage_type == "local":
                file_path = self.storage_path / object_key
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted from local storage: {object_key}")
            
            elif settings.storage_type == "s3":
                self.client.delete_object(
                    Bucket=self.bucket,
                    Key=object_key
                )
                logger.info(f"Deleted from S3: {object_key}")
            
        except Exception as e:
            logger.error(f"Storage delete error: {e}")
            raise
