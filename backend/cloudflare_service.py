# cloudflare_service.py
import os
import boto3
import uuid
from botocore.client import Config
from botocore.exceptions import ClientError
import logging


CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_ACCESS_KEY_ID = os.getenv("CLOUDFLARE_ACCESS_KEY_ID")
CLOUDFLARE_SECRET_ACCESS_KEY = os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

# The R2 endpoint URL
R2_ENDPOINT_URL = f"https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"

logger = logging.getLogger(__name__)

class CloudflareService:
    def __init__(self):
        try:
            self.r2 = boto3.client(
                's3',
                endpoint_url=R2_ENDPOINT_URL,
                aws_access_key_id=CLOUDFLARE_ACCESS_KEY_ID,
                aws_secret_access_key=CLOUDFLARE_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4'),
                region_name='auto' # Important for R2
            )
            logger.info("Cloudflare R2 client initialized successfully.")
        except Exception as e:
            self.r2 = None
            logger.error(f"Failed to initialize Cloudflare R2 client: {e}")

    def generate_presigned_upload_url(self, file_name: str, file_type: str):
        """
        Generates a presigned URL for a client to upload a file directly to R2.
        """
        if not self.r2:
            raise ConnectionError("Cloudflare service is not available.")

        # Generate a unique key for the object in the bucket
        object_key = f"uploads/{uuid.uuid4()}-{file_name}"

        try:
            response = self.r2.generate_presigned_post(
                Bucket=R2_BUCKET_NAME,
                Key=object_key,
                Fields={"Content-Type": file_type},
                Conditions=[
                    {"Content-Type": file_type},
                    ["content-length-range", 1, 25 * 1024 * 1024] # Limit to 25MB
                ],
                ExpiresIn=3600  # URL expires in 1 hour
            )
            
            
            public_url = f"https://pub-{R2_BUCKET_NAME}.r2.dev/{object_key}"

            return {"upload_details": response, "public_url": public_url}

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None


cloudflare_service = CloudflareService()