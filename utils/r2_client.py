import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Optional, List
import urllib.parse
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class R2Client:
    """Cloudflare R2 client for screenshot storage and retrieval"""
    
    def __init__(self):
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID") 
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        self.token = os.getenv("R2_TOKEN")
        self.endpoint_url = os.getenv("R2_ENDPOINT_URL")
        
        self.client = None
        self._is_configured = False
        
        # Validate configuration
        self._validate_configuration()
        
        if self._is_configured:
            self._initialize_client()
    
    def _validate_configuration(self):
        """Validate R2 configuration"""
        required_vars = {
            "R2_ACCOUNT_ID": self.account_id,
            "R2_ACCESS_KEY_ID": self.access_key_id,
            "R2_SECRET_ACCESS_KEY": self.secret_access_key,
            "R2_BUCKET_NAME": self.bucket_name
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            logger.warning(f"R2 configuration incomplete. Missing: {', '.join(missing_vars)}")
            self._is_configured = False
        else:
            # Validate and fix endpoint URL
            if self.endpoint_url:
                # Check if endpoint URL incorrectly includes bucket name
                if self.endpoint_url.endswith(f"/{self.bucket_name}"):
                    logger.warning(f"Endpoint URL includes bucket name - correcting it")
                    logger.warning(f"Original: {self.endpoint_url}")
                    self.endpoint_url = self.endpoint_url[:-len(f"/{self.bucket_name}")]
                    logger.warning(f"Corrected: {self.endpoint_url}")
                    logger.warning(f"Please update your R2_ENDPOINT_URL environment variable to: {self.endpoint_url}")
                elif f"/{self.bucket_name}/" in self.endpoint_url:
                    # Handle cases where bucket name is in the middle
                    parts = self.endpoint_url.split(f"/{self.bucket_name}")
                    self.endpoint_url = parts[0]
                    logger.warning(f"Endpoint URL included bucket name - corrected to: {self.endpoint_url}")
            
            # Auto-construct endpoint URL if not provided or if it doesn't match expected format
            expected_endpoint = f"https://{self.account_id}.r2.cloudflarestorage.com"
            if not self.endpoint_url:
                self.endpoint_url = expected_endpoint
                logger.info(f"Auto-constructed R2 endpoint URL: {self.endpoint_url}")
            elif self.endpoint_url != expected_endpoint:
                logger.warning(f"Endpoint URL format might be incorrect")
                logger.warning(f"Current: {self.endpoint_url}")
                logger.warning(f"Expected: {expected_endpoint}")
            
            self._is_configured = True
            logger.info("R2 configuration validated successfully")
    
    def _initialize_client(self):
        """Initialize the R2 S3-compatible client"""
        try:
            # Create boto3 client for R2 (S3-compatible)
            self.client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='auto'  # R2 requires 'auto' as the region
            )
            
            # Test connection with a simple operation
            self._test_connection()
            logger.info("R2 client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {e}")
            self._is_configured = False
            self.client = None
    
    def _test_connection(self):
        """Test R2 connection by checking if bucket is accessible"""
        try:
            # Try to list objects in the bucket (limit to 1 for efficiency)
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=1
            )
            logger.debug("R2 connection test successful - bucket accessible")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchBucket':
                logger.error(f"R2 bucket '{self.bucket_name}' not found")
                logger.error(f"Please verify the bucket name and ensure it exists in account {self.account_id}")
            elif error_code == 'AccessDenied':
                logger.error(f"Access denied to R2 bucket '{self.bucket_name}'")
                logger.error("Please check your R2 API token has the correct permissions")
            else:
                logger.error(f"R2 connection test failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during R2 connection test: {e}")
            raise
    
    def is_configured(self) -> bool:
        """Check if R2 is properly configured"""
        return self._is_configured and self.client is not None
    
    def get_screenshot_url(self, screenshot_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for a screenshot in R2
        
        Args:
            screenshot_path: Path to the screenshot in R2 (e.g., "uploads/folder/file.png")
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string or None if error
        """
        if not self.is_configured():
            logger.error("R2 client not configured")
            return None
        
        try:
            # Normalize path - remove leading slash if present
            screenshot_path = screenshot_path.lstrip('/')
            
            # Generate presigned URL
            presigned_url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': screenshot_path},
                ExpiresIn=expires_in
            )
            
            logger.debug(f"Generated presigned URL for {screenshot_path}")
            return presigned_url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                logger.warning(f"Object not found in R2: {screenshot_path}")
            else:
                logger.error(f"Failed to generate presigned URL for {screenshot_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL for {screenshot_path}: {e}")
            return None
    
    def batch_get_screenshot_urls(self, screenshot_paths: List[str], expires_in: int = 3600) -> Dict[str, Optional[str]]:
        """
        Generate presigned URLs for multiple screenshots
        
        Args:
            screenshot_paths: List of screenshot paths
            expires_in: URL expiration time in seconds
            
        Returns:
            Dictionary mapping screenshot paths to their presigned URLs
        """
        if not self.is_configured():
            logger.error("R2 client not configured")
            return {path: None for path in screenshot_paths}
        
        result = {}
        for path in screenshot_paths:
            result[path] = self.get_screenshot_url(path, expires_in)
        
        return result
    
    def check_object_exists(self, object_key: str) -> bool:
        """Check if an object exists in R2"""
        if not self.is_configured():
            return False
        
        try:
            object_key = object_key.lstrip('/')
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code in ['NoSuchKey', '404']:
                return False
            else:
                logger.warning(f"Error checking object existence for {object_key}: {e}")
                return False
        except Exception as e:
            logger.warning(f"Unexpected error checking object existence for {object_key}: {e}")
            return False
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict]:
        """List objects in R2 bucket with optional prefix filter"""
        if not self.is_configured():
            logger.error("R2 client not configured")
            return []
        
        try:
            kwargs = {
                'Bucket': self.bucket_name,
                'MaxKeys': max_keys
            }
            
            if prefix:
                kwargs['Prefix'] = prefix
            
            response = self.client.list_objects_v2(**kwargs)
            
            objects = response.get('Contents', [])
            return [
                {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                }
                for obj in objects
            ]
            
        except ClientError as e:
            logger.error(f"Failed to list objects with prefix '{prefix}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing objects with prefix '{prefix}': {e}")
            return []
    
    def get_connection_info(self) -> Dict:
        """Get R2 connection information for debugging"""
        return {
            "configured": self._is_configured,
            "account_id": self.account_id[:8] + "..." if self.account_id else None,
            "bucket_name": self.bucket_name,
            "endpoint_url": self.endpoint_url,
            "access_key_id": self.access_key_id[:8] + "..." if self.access_key_id else None,
            "auto_constructed_endpoint": not os.getenv("R2_ENDPOINT_URL") and self.account_id
        }

# Global R2 client instance
_r2_client = None

def get_r2_client() -> R2Client:
    """Get the global R2 client instance"""
    global _r2_client
    if _r2_client is None:
        _r2_client = R2Client()
    return _r2_client

def is_r2_configured() -> bool:
    """Check if R2 is properly configured"""
    return get_r2_client().is_configured() 