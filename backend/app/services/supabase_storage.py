import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

class SupabaseStorageService:
    def __init__(self):
        self.url = f"{settings.SUPABASE_URL}/storage/v1"
        self.headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "apiKey": settings.SUPABASE_ANON_KEY
        }

    async def initialize_bucket(self, bucket: str = "resumes") -> None:
        """Create the storage bucket if it does not already exist."""
        async with httpx.AsyncClient() as client:
            try:
                # Try getting the bucket
                resp = await client.get(
                    f"{self.url}/bucket/{bucket}",
                    headers=self.headers
                )
                if resp.status_code == 200:
                    logger.info("Supabase storage bucket verified", bucket=bucket)
                    return
                
                # If not found, create it
                create_data = {
                    "id": bucket,
                    "name": bucket,
                    "public": False,
                    "file_size_limit": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
                    "allowed_mime_types": ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
                }
                resp_create = await client.post(
                    f"{self.url}/bucket",
                    json=create_data,
                    headers=self.headers
                )
                if resp_create.status_code in (200, 201):
                    logger.info("Supabase storage bucket created successfully", bucket=bucket)
                else:
                    logger.warning("Failed to create storage bucket, might already exist", bucket=bucket, response=resp_create.text)
            except Exception as e:
                logger.error("Error initializing storage bucket", error=str(e))

    async def upload_file(self, bucket: str, path: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload raw bytes to Supabase Storage."""
        async with httpx.AsyncClient() as client:
            headers = {**self.headers, "Content-Type": content_type}
            # Upload endpoint
            resp = await client.post(
                f"{self.url}/object/{bucket}/{path}",
                content=content,
                headers=headers
            )
            if resp.status_code == 400 and "Already exists" in resp.text:
                # Try PUT request (update) if it already exists
                resp_put = await client.put(
                    f"{self.url}/object/{bucket}/{path}",
                    content=content,
                    headers=headers
                )
                if resp_put.status_code == 200:
                    logger.info("File updated in Supabase Storage", bucket=bucket, path=path)
                    return f"{bucket}/{path}"
                raise Exception(f"Failed to overwrite file in Supabase Storage: {resp_put.text}")
                
            if resp.status_code not in (200, 201):
                raise Exception(f"Failed to upload to Supabase Storage: {resp.text}")
                
            logger.info("File uploaded to Supabase Storage", bucket=bucket, path=path)
            return f"{bucket}/{path}"

    async def download_file(self, bucket: str, path: str) -> bytes:
        """Download file content bytes from Supabase Storage."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.url}/object/authenticated/{bucket}/{path}",
                headers=self.headers
            )
            if resp.status_code != 200:
                raise Exception(f"Failed to download from Supabase Storage: {resp.text}")
            return resp.content

    async def delete_file(self, bucket: str, path: str) -> None:
        """Delete file from Supabase Storage."""
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.url}/object/{bucket}/{path}",
                headers=self.headers
            )
            if resp.status_code not in (200, 204):
                logger.warning("Failed to delete file from Supabase Storage", bucket=bucket, path=path, response=resp.text)
            else:
                logger.info("File deleted from Supabase Storage", bucket=bucket, path=path)

_storage_service = None

def get_storage_service() -> SupabaseStorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = SupabaseStorageService()
    return _storage_service
