import boto3
import os
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.s3_client = None
        self.bucket_name = settings.aws_s3_bucket
        self._init_s3_client()
    
    def _init_s3_client(self):
        """Initialize S3 client with credentials"""
        try:
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
            else:
                # Try to use default credentials (IAM roles, etc.)
                self.s3_client = boto3.client('s3', region_name=settings.aws_region)

            if settings.s3_verify_bucket_on_init:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(
                    "Successfully connected to S3 bucket: %s", self.bucket_name
                )
            else:
                logger.warning(
                    "S3 client created without bucket verification "
                    "(S3_VERIFY_BUCKET_ON_INIT=false)"
                )
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                logger.error(f"S3 bucket {self.bucket_name} does not exist")
                raise
            else:
                logger.error(f"Error connecting to S3: {e}")
                raise
    
    def upload_file(self, file_path: str, s3_key: str, content_type: Optional[str] = None) -> bool:
        """Upload a file to S3"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Determine content type if not provided
            if not content_type:
                content_type = self._get_content_type(file_path)
            
            # Upload file
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'original_filename': os.path.basename(file_path),
                        'uploaded_by': 'edumate-ai'
                    }
                }
            )
            
            logger.info(f"Successfully uploaded {file_path} to s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            raise
    
    def upload_fileobj(self, file_obj: BinaryIO, s3_key: str, content_type: Optional[str] = None) -> bool:
        """Upload a file object to S3"""
        try:
            # Determine content type if not provided
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Upload file object
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'uploaded_by': 'edumate-ai'
                    }
                }
            )
            
            logger.info(f"Successfully uploaded file object to s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file object: {e}")
            raise
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Download a file from S3"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            logger.info(f"Successfully downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file {s3_key}: {e}")
            raise
    
    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for file access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL for {s3_key}: {e}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Successfully deleted s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {s3_key}: {e}")
            raise
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """List files in S3 bucket with optional prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag']
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            raise
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking file existence for {s3_key}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error checking file existence for {s3_key}: {e}")
            raise
    
    def get_file_metadata(self, s3_key: str) -> dict:
        """Get metadata for a file in S3"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            metadata = {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting metadata for {s3_key}: {e}")
            raise
    
    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
        
        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.json': 'application/json',
            '.csv': 'text/csv'
        }
        
        return content_types.get(extension, 'application/octet-stream')
    
    def create_folder(self, folder_path: str) -> bool:
        """Create a folder in S3 (S3 doesn't have real folders, but we can create empty objects)"""
        try:
            # Ensure folder path ends with /
            if not folder_path.endswith('/'):
                folder_path += '/'
            
            # Create an empty object to represent the folder
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=folder_path,
                Body=''
            )
            
            logger.info(f"Successfully created folder: s3://{self.bucket_name}/{folder_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating folder {folder_path}: {e}")
            raise
    
    def copy_file(self, source_key: str, destination_key: str) -> bool:
        """Copy a file within the same S3 bucket"""
        try:
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key
            }
            
            self.s3_client.copy(copy_source, self.bucket_name, destination_key)
            
            logger.info(f"Successfully copied {source_key} to {destination_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file from {source_key} to {destination_key}: {e}")
            raise
