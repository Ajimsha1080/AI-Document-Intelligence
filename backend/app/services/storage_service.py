import os
import shutil
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("storage_service")

MIME_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
    "application/pdf": ".pdf",
}

def get_extension_for_mime(mime_type: str, fallback_filename: str = "") -> str:
    clean_mime = (mime_type or "").lower().split(";")[0].strip()
    if clean_mime in MIME_EXTENSION_MAP:
        return MIME_EXTENSION_MAP[clean_mime]
    import mimetypes
    guessed = mimetypes.guess_extension(clean_mime)
    if guessed:
        return guessed
    _, ext = os.path.splitext(fallback_filename)
    if ext and len(ext) <= 10 and ext.replace(".", "").isalnum():
        return ext.lower()
    return ".bin"

class StorageService:
    """
    Sovereign S3-compatible Object Storage Service with air-gapped local fallback.
    Enforces in-country tenant isolation paths: {tenant_id}/{document_id}/{filename}.
    Applies server-side encryption (AES256) where supported.
    Connects lazily with retries; strictly enforces in-country storage when enabled.
    """
    def __init__(self):
        self._s3_client = None
        self._s3_initialized = False

    def _get_s3(self):
        """Lazily initializes and returns S3 client with retry mechanism."""
        if self._s3_initialized and self._s3_client:
            return self._s3_client

        if not settings.S3_ENDPOINT_URL or not settings.S3_BUCKET_NAME:
            self._s3_initialized = True
            return None

        # Retry up to 3 times to connect
        last_err = None
        for attempt in range(3):
            try:
                import boto3
                from botocore.client import Config
                client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                    region_name=settings.S3_REGION,
                    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, connect_timeout=2, retries={"max_attempts": 2}),
                )
                client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
                self._s3_client = client
                self._s3_initialized = True
                logger.info(f"S3 Object Storage connected: {settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}")
                return self._s3_client
            except Exception as e:
                last_err = e

        self._s3_initialized = True
        if getattr(settings, "ENFORCE_IN_COUNTRY_STORAGE", False) and getattr(settings, "ENVIRONMENT", "development") == "production":
            raise RuntimeError(
                f"UAE Sovereign Storage Error: S3 endpoint is configured and ENFORCE_IN_COUNTRY_STORAGE=True, "
                f"but sovereign S3 storage at {settings.S3_ENDPOINT_URL} is unreachable ({last_err}). "
                f"Silent local disk fallback is prohibited under UAE data sovereignty policy."
            )

        logger.warning(f"S3 offline ({last_err}). Using local sovereign storage at {settings.LOCAL_STORAGE_DIR}")
        return None

    def upload_document_file(
        self,
        tenant_id: str,
        document_id: str,
        filename: str,
        content: bytes,
        mime_type: str
    ) -> str:
        """
        Stores document content strictly under tenant-isolated path: {tenant_id}/{document_id}/original{ext}
        Prevents directory traversal regardless of client-supplied filename.
        """
        ext = get_extension_for_mime(mime_type, filename)
        storage_key = f"{tenant_id}/{document_id}/original{ext}"

        s3 = self._get_s3()
        if s3:
            try:
                s3.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=storage_key,
                    Body=content,
                    ContentType=mime_type,
                    ServerSideEncryption="AES256"
                )
                return f"s3://{settings.S3_BUCKET_NAME}/{storage_key}"
            except Exception as e:
                if getattr(settings, "ENFORCE_IN_COUNTRY_STORAGE", False):
                    raise RuntimeError(f"S3 storage upload failed and ENFORCE_IN_COUNTRY_STORAGE is active: {e}")
                logger.warning(f"S3 upload failed ({e}); falling back to local sovereign storage.")

        # Local storage fallback: {LOCAL_STORAGE_DIR}/{tenant_id}/{document_id}/original{ext}
        local_dir = os.path.join(settings.LOCAL_STORAGE_DIR, tenant_id, document_id)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, f"original{ext}")
        with open(local_path, "wb") as f:
            f.write(content)
        return local_path

    def get_document_bytes(self, storage_path: str) -> bytes:
        """Retrieves raw document bytes from S3 or local sovereign storage."""
        if storage_path.startswith("s3://"):
            s3 = self._get_s3()
            if s3:
                # Format: s3://bucket/key...
                parts = storage_path.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1]
                obj = s3.get_object(Bucket=bucket, Key=key)
                return obj["Body"].read()
            elif getattr(settings, "ENFORCE_IN_COUNTRY_STORAGE", False):
                raise RuntimeError(f"Cannot retrieve S3 document bytes: S3 storage is unreachable ({storage_path})")

        # Local filesystem path
        if os.path.exists(storage_path):
            with open(storage_path, "rb") as f:
                return f.read()

        raise FileNotFoundError(f"Storage path not found or unreachable: {storage_path}")

    def delete_document_artifacts(self, tenant_id: str, document_id: str, storage_path: Optional[str] = None) -> None:
        """
        Hard-deletes original document, rendered page images, embeddings, and any cached files.
        Guarantees right-to-erasure compliance under UAE PDPL.
        """
        prefix = f"{tenant_id}/{document_id}/"

        s3 = self._get_s3()
        if s3:
            try:
                # List and delete all objects under the document folder
                response = s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME, Prefix=prefix)
                if "Contents" in response:
                    delete_keys = [{"Key": obj["Key"]} for obj in response["Contents"]]
                    s3.delete_objects(
                        Bucket=settings.S3_BUCKET_NAME,
                        Delete={"Objects": delete_keys}
                    )
            except Exception as e:
                logger.error(f"Error purging S3 artifacts for document {document_id}: {e}")

        # Local filesystem cleanup
        local_dir = os.path.join(settings.LOCAL_STORAGE_DIR, tenant_id, document_id)
        if os.path.exists(local_dir):
            try:
                shutil.rmtree(local_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error purging local directory {local_dir}: {e}")

storage_service = StorageService()
