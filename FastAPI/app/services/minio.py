import uuid
from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException
from app.config import get_settings

settings = get_settings()

# Allowed image types
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def get_minio_client() -> Minio:
    """Get MinIO client instance."""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )


def ensure_bucket_exists(client: Minio) -> None:
    """Create bucket if it doesn't exist."""
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")


def validate_image(file: UploadFile) -> None:
    """Validate image file type and size."""
    # Check file extension
    if file.filename:
        extension = file.filename.split(".")[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
    else:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Check content type
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")


async def upload_image(file: UploadFile) -> str:
    """
    Upload image to MinIO.
    Returns the object name (filename in bucket).
    """
    validate_image(file)
    
    # Generate unique filename
    extension = file.filename.split(".")[-1].lower() if file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{extension}"
    
    client = get_minio_client()
    ensure_bucket_exists(client)
    
    try:
        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )
        
        # Reset file pointer for MinIO
        from io import BytesIO
        file_data = BytesIO(content)
        
        # Upload to MinIO
        client.put_object(
            settings.MINIO_BUCKET,
            unique_filename,
            file_data,
            length=len(content),
            content_type=file.content_type or "image/jpeg"
        )
        
        return unique_filename
        
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


def get_image_url(object_name: str) -> str:
    """
    Generate URL for accessing the image.
    Returns a presigned URL or public URL based on configuration.
    """
    client = get_minio_client()
    
    try:
        # Generate presigned URL (valid for 7 days)
        from datetime import timedelta
        url = client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_name,
            expires=timedelta(days=7)
        )
        return url
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to get image URL: {str(e)}")


def delete_image(object_name: str) -> bool:
    """Delete image from MinIO."""
    client = get_minio_client()
    
    try:
        client.remove_object(settings.MINIO_BUCKET, object_name)
        return True
    except S3Error as e:
        # Log error but don't raise - image might already be deleted
        print(f"Warning: Failed to delete image {object_name}: {str(e)}")
        return False
