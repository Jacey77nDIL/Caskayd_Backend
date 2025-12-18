"""
Unified Brief & Cloudflare Service
Manages:
- Cloudflare R2 setup and configuration
- Brief uploads from businesses
- Brief downloads for creators
- Brief sharing through messages
"""

import os
import boto3
import uuid
import logging
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
from datetime import datetime

# Environment variables
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_ACCESS_KEY_ID = os.getenv("CLOUDFLARE_ACCESS_KEY_ID")
CLOUDFLARE_SECRET_ACCESS_KEY = os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

# The R2 endpoint URL
R2_ENDPOINT_URL = f"https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"

logger = logging.getLogger(__name__)

# File type and size constraints
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.xlsx', '.xls', '.pptx', '.ppt'}
BRIEF_PREFIX = "briefs"
ARCHIVE_PREFIX = "archive"


class BriefCloudflareService:
    """
    Unified service for managing briefs and Cloudflare R2 operations.
    """
    
    def __init__(self):
        """Initialize Cloudflare R2 client."""
        try:
            # Validate environment variables
            if not all([CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ACCESS_KEY_ID, 
                       CLOUDFLARE_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
                missing = []
                if not CLOUDFLARE_ACCOUNT_ID:
                    missing.append("CLOUDFLARE_ACCOUNT_ID")
                if not CLOUDFLARE_ACCESS_KEY_ID:
                    missing.append("CLOUDFLARE_ACCESS_KEY_ID")
                if not CLOUDFLARE_SECRET_ACCESS_KEY:
                    missing.append("CLOUDFLARE_SECRET_ACCESS_KEY")
                if not R2_BUCKET_NAME:
                    missing.append("R2_BUCKET_NAME")
                raise ValueError(f"Missing environment variables: {', '.join(missing)}")
            
            logger.info(f"Initializing R2 Service - Account: {CLOUDFLARE_ACCOUNT_ID}, Bucket: {R2_BUCKET_NAME}")
            logger.info(f"R2 Endpoint: {R2_ENDPOINT_URL}")
            
            self.r2 = boto3.client(
                's3',
                endpoint_url=R2_ENDPOINT_URL,
                aws_access_key_id=CLOUDFLARE_ACCESS_KEY_ID,
                aws_secret_access_key=CLOUDFLARE_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4'),
                region_name='auto'
            )
            
            logger.info("Cloudflare R2 client initialized successfully.")
            self._test_connection()
            
        except Exception as e:
            self.r2 = None
            logger.error(f"Failed to initialize Cloudflare R2 client: {e}")
            raise

    def _test_connection(self):
        """Test R2 connection by checking if the configured bucket is accessible."""
        if not R2_BUCKET_NAME:
            logger.warning("R2_BUCKET_NAME not configured")
            return
            
        try:
            # Try to head the bucket instead of listing all buckets
            # This only requires access to the specific bucket, not ListBuckets permission
            self.r2.head_bucket(Bucket=R2_BUCKET_NAME)
            logger.info(f"R2 bucket '{R2_BUCKET_NAME}' is accessible")
        except Exception as e:
            logger.warning(f"Could not verify R2 bucket access: {e}")

    def _validate_file(self, file_name: str, file_size: int, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate file before upload.
        
        Args:
            file_name: Name of the file
            file_size: Size of the file in bytes
            content_type: MIME type of the file
            
        Returns:
            Dictionary with validation result and error message if any
        """
        errors = []
        
        # Check file name
        if not file_name or len(file_name.strip()) == 0:
            errors.append("File name is required")
            return {"valid": False, "errors": errors}
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            errors.append(f"File size exceeds {MAX_FILE_SIZE / (1024*1024):.0f}MB limit")
        
        if file_size == 0:
            errors.append("File is empty")
        
        # Check file extension
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext and file_ext not in ALLOWED_EXTENSIONS:
            errors.append(f"File type '{file_ext}' not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "file_extension": file_ext,
            "file_name_clean": os.path.basename(file_name)
        }

    def upload_brief(self, file_name: str, file_content: bytes, content_type: str, business_id: int) -> Dict[str, Any]:
        """
        Upload a brief file from a business.
        
        Args:
            file_name: Original file name
            file_content: File content as bytes
            content_type: MIME type
            business_id: ID of the business uploading the brief
            
        Returns:
            Dictionary with upload details including public URL
            
        Raises:
            Exception: If upload fails
        """
        if not self.r2:
            raise ConnectionError("Cloudflare R2 service is not available.")
        
        # Validate file
        validation = self._validate_file(file_name, len(file_content), content_type)
        if not validation["valid"]:
            raise ValueError(f"File validation failed: {', '.join(validation['errors'])}")
        
        try:
            # Generate unique object key
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_ext = validation["file_extension"]
            object_key = f"{BRIEF_PREFIX}/business_{business_id}/{timestamp}_{unique_id}_{file_name}"
            
            # Upload to R2
            self.r2.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=object_key,
                Body=file_content,
                ContentType=content_type or "application/octet-stream"
            )
            
            # Generate public URL
            public_url = f"https://pub-{R2_BUCKET_NAME}.r2.dev/{object_key}"
            
            logger.info(f"Brief uploaded successfully by business {business_id}: {object_key}")
            
            return {
                "success": True,
                "public_url": public_url,
                "object_key": object_key,
                "file_name": file_name,
                "file_size": len(file_content),
                "content_type": content_type,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            logger.error(f"Failed to upload brief: {e}")
            raise Exception(f"Upload failed: {str(e)}")

    def generate_download_url(self, object_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned download URL for a brief.
        
        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned download URL
        """
        if not self.r2:
            raise ConnectionError("Cloudflare R2 service is not available.")
        
        try:
            presigned_url = self.r2.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': R2_BUCKET_NAME,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Download URL generated for: {object_key}")
            return presigned_url
            
        except ClientError as e:
            logger.error(f"Failed to generate download URL: {e}")
            raise Exception(f"Failed to generate download URL: {str(e)}")

    def get_brief_metadata(self, object_key: str) -> Dict[str, Any]:
        """
        Get metadata for a brief file.
        
        Args:
            object_key: S3 object key
            
        Returns:
            Dictionary with file metadata
        """
        if not self.r2:
            raise ConnectionError("Cloudflare R2 service is not available.")
        
        try:
            response = self.r2.head_object(Bucket=R2_BUCKET_NAME, Key=object_key)
            
            return {
                "file_size": response.get('ContentLength'),
                "content_type": response.get('ContentType'),
                "last_modified": response.get('LastModified'),
                "etag": response.get('ETag')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"Brief not found: {object_key}")
            logger.error(f"Failed to get brief metadata: {e}")
            raise Exception(f"Failed to get brief metadata: {str(e)}")

    def delete_brief(self, object_key: str) -> bool:
        """
        Delete a brief file.
        
        Args:
            object_key: S3 object key
            
        Returns:
            True if deletion was successful
        """
        if not self.r2:
            raise ConnectionError("Cloudflare R2 service is not available.")
        
        try:
            self.r2.delete_object(Bucket=R2_BUCKET_NAME, Key=object_key)
            logger.info(f"Brief deleted successfully: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete brief: {e}")
            raise Exception(f"Failed to delete brief: {str(e)}")

    def archive_brief(self, object_key: str) -> Dict[str, Any]:
        """
        Archive a brief by copying to archive prefix.
        
        Args:
            object_key: S3 object key
            
        Returns:
            Dictionary with archive details
        """
        if not self.r2:
            raise ConnectionError("Cloudflare R2 service is not available.")
        
        try:
            # Create archive key
            archive_key = object_key.replace(BRIEF_PREFIX, ARCHIVE_PREFIX)
            
            # Copy object to archive
            self.r2.copy_object(
                CopySource={'Bucket': R2_BUCKET_NAME, 'Key': object_key},
                Bucket=R2_BUCKET_NAME,
                Key=archive_key
            )
            
            logger.info(f"Brief archived: {object_key} -> {archive_key}")
            
            return {
                "success": True,
                "original_key": object_key,
                "archive_key": archive_key
            }
            
        except ClientError as e:
            logger.error(f"Failed to archive brief: {e}")
            raise Exception(f"Failed to archive brief: {str(e)}")

    def list_briefs(self, business_id: Optional[int] = None, prefix: str = BRIEF_PREFIX) -> list:
        """
        List briefs in storage.
        
        Args:
            business_id: Optional business ID to filter briefs
            prefix: S3 prefix to search under
            
        Returns:
            List of brief metadata
        """
        if not self.r2:
            raise ConnectionError("Cloudflare R2 service is not available.")
        
        try:
            search_prefix = prefix
            if business_id:
                search_prefix = f"{prefix}/business_{business_id}/"
            
            response = self.r2.list_objects_v2(
                Bucket=R2_BUCKET_NAME,
                Prefix=search_prefix
            )
            
            briefs = []
            for obj in response.get('Contents', []):
                briefs.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "storage_class": obj['StorageClass']
                })
            
            logger.info(f"Listed {len(briefs)} briefs with prefix: {search_prefix}")
            return briefs
            
        except ClientError as e:
            logger.error(f"Failed to list briefs: {e}")
            raise Exception(f"Failed to list briefs: {str(e)}")


# Singleton instance
brief_cloudflare_service = BriefCloudflareService()
