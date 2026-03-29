"""S3 and local filesystem storage backends (same logical keys in Document.file_path)."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Protocol, runtime_checkable

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config import settings

logger = logging.getLogger(__name__)


def _safe_local_object_path(root: str, key: str) -> Path:
    """Resolve key under root; reject path traversal."""
    base = Path(root).resolve()
    parts = [p for p in Path(key.replace("\\", "/")).parts if p not in ("", ".", "..")]
    target = (base.joinpath(*parts)).resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"Invalid storage key (path traversal): {key!r}")
    return target


@runtime_checkable
class StorageService(Protocol):
    """Minimal interface used by upload, ingestion, and delete."""

    def upload_file(
        self, file_path: str, key: str, content_type: Optional[str] = None
    ) -> bool: ...

    def download_file(self, key: str, local_path: str) -> bool: ...

    def delete_file(self, key: str) -> bool: ...


class LocalStorageService:
    """Store objects under a local directory (e.g. repo data/)."""

    def __init__(self, root: str | None = None) -> None:
        raw = root if root is not None else settings.local_storage_root
        self.root = os.path.abspath(os.path.expanduser(raw))
        os.makedirs(self.root, exist_ok=True)
        logger.info("Local storage root: %s", self.root)

    def upload_file(
        self, file_path: str, key: str, content_type: Optional[str] = None
    ) -> bool:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        dest = _safe_local_object_path(self.root, key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)
        logger.info("Uploaded to local storage: %s", dest)
        return True

    def download_file(self, key: str, local_path: str) -> bool:
        src = _safe_local_object_path(self.root, key)
        if not src.is_file():
            raise FileNotFoundError(f"Object not found: {key}")
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, local_path)
        logger.info("Downloaded from local storage %s -> %s", key, local_path)
        return True

    def delete_file(self, key: str) -> bool:
        try:
            path = _safe_local_object_path(self.root, key)
            if path.is_file():
                path.unlink()
                logger.info("Deleted local file: %s", path)
            else:
                logger.warning("Local delete: file missing for key %s", key)
            return True
        except ValueError:
            logger.error("Invalid key for delete: %s", key)
            raise
        except Exception as e:
            logger.error("Error deleting local file %s: %s", key, e)
            raise

    def absolute_path(self, key: str) -> Path:
        """Resolved path for an object key (for authenticated download)."""
        return _safe_local_object_path(self.root, key)


class S3StorageService:
    """AWS S3 implementation (original behavior)."""

    def __init__(self) -> None:
        self.s3_client = None
        self.bucket_name = settings.aws_s3_bucket
        self._init_s3_client()

    def _init_s3_client(self) -> None:
        """Initialize S3 client with credentials"""
        try:
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region,
                )
            else:
                self.s3_client = boto3.client("s3", region_name=settings.aws_region)

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
            if e.response["Error"]["Code"] == "NoSuchBucket":
                logger.error("S3 bucket %s does not exist", self.bucket_name)
                raise
            logger.error("Error connecting to S3: %s", e)
            raise

    def upload_file(
        self, file_path: str, s3_key: str, content_type: Optional[str] = None
    ) -> bool:
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            if not content_type:
                content_type = self._get_content_type(file_path)

            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {
                        "original_filename": os.path.basename(file_path),
                        "uploaded_by": "edumate-ai",
                    },
                },
            )

            logger.info(
                "Successfully uploaded %s to s3://%s/%s",
                file_path,
                self.bucket_name,
                s3_key,
            )
            return True

        except Exception as e:
            logger.error("Error uploading file %s: %s", file_path, e)
            raise

    def upload_fileobj(
        self, file_obj: BinaryIO, s3_key: str, content_type: Optional[str] = None
    ) -> bool:
        try:
            if not content_type:
                content_type = "application/octet-stream"

            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {"uploaded_by": "edumate-ai"},
                },
            )

            logger.info(
                "Successfully uploaded file object to s3://%s/%s",
                self.bucket_name,
                s3_key,
            )
            return True

        except Exception as e:
            logger.error("Error uploading file object: %s", e)
            raise

    def download_file(self, s3_key: str, local_path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path,
            )

            logger.info(
                "Successfully downloaded s3://%s/%s to %s",
                self.bucket_name,
                s3_key,
                local_path,
            )
            return True

        except Exception as e:
            logger.error("Error downloading file %s: %s", s3_key, e)
            raise

    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str:
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error("Error generating presigned URL for %s: %s", s3_key, e)
            raise

    def delete_file(self, s3_key: str) -> bool:
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )

            logger.info(
                "Successfully deleted s3://%s/%s", self.bucket_name, s3_key
            )
            return True

        except Exception as e:
            logger.error("Error deleting file %s: %s", s3_key, e)
            raise

    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    files.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                            "etag": obj["ETag"],
                        }
                    )

            return files

        except Exception as e:
            logger.error("Error listing files with prefix %s: %s", prefix, e)
            raise

    def file_exists(self, s3_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error("Error checking file existence for %s: %s", s3_key, e)
            raise
        except Exception as e:
            logger.error(
                "Unexpected error checking file existence for %s: %s", s3_key, e
            )
            raise

    def get_file_metadata(self, s3_key: str) -> dict:
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name, Key=s3_key
            )

            metadata = {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
                "metadata": response.get("Metadata", {}),
            }

            return metadata

        except Exception as e:
            logger.error("Error getting metadata for %s: %s", s3_key, e)
            raise

    def _get_content_type(self, file_path: str) -> str:
        extension = os.path.splitext(file_path)[1].lower()

        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".html": "text/html",
            ".json": "application/json",
            ".csv": "text/csv",
        }

        return content_types.get(extension, "application/octet-stream")

    def create_folder(self, folder_path: str) -> bool:
        try:
            if not folder_path.endswith("/"):
                folder_path += "/"

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=folder_path,
                Body="",
            )

            logger.info(
                "Successfully created folder: s3://%s/%s", self.bucket_name, folder_path
            )
            return True

        except Exception as e:
            logger.error("Error creating folder %s: %s", folder_path, e)
            raise

    def copy_file(self, source_key: str, destination_key: str) -> bool:
        try:
            copy_source = {"Bucket": self.bucket_name, "Key": source_key}

            self.s3_client.copy(copy_source, self.bucket_name, destination_key)

            logger.info(
                "Successfully copied %s to %s", source_key, destination_key
            )
            return True

        except Exception as e:
            logger.error(
                "Error copying file from %s to %s: %s",
                source_key,
                destination_key,
                e,
            )
            raise


def build_storage_service() -> StorageService:
    if settings.storage_backend == "local":
        return LocalStorageService()
    return S3StorageService()
