"""Storage Service - Handles file uploads to Cloudinary with compression"""
import cloudinary
import cloudinary.uploader
from PIL import Image
import io
import base64
from fastapi import UploadFile, HTTPException, status
from core.config import settings
from core.logging import logger

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def upload_image(file: UploadFile) -> str:
    """Upload and compress image to Cloudinary"""
    
    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read and compress image
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    try:
        # Compress image using PIL
        img = Image.open(io.BytesIO(content))
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Resize if too large (max 1920px width)
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # Save compressed image to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        compressed_content = output.getvalue()
        
        # Upload to Cloudinary with additional optimization
        result = cloudinary.uploader.upload(
            compressed_content,
            folder="sarees",
            resource_type="image",
            transformation=[
                {"quality": "auto:good", "fetch_format": "auto"}
            ]
        )
        
        public_url = result["secure_url"]
        logger.info(f"Image uploaded to Cloudinary: {result['public_id']}")
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )

async def delete_image(image_url: str) -> bool:
    """Delete image from Cloudinary"""
    try:
        # Extract public_id from URL
        public_id = image_url.split("/")[-1].split(".")[0]
        public_id = f"sarees/{public_id}"
        cloudinary.uploader.destroy(public_id)
        logger.info(f"Image deleted from Cloudinary: {public_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete image from Cloudinary: {str(e)}")
        return False


async def upload_base64_image(base64_data: str) -> str:
    """Upload a base64 encoded image to Cloudinary"""
    try:
        # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_data)
        
        # Check file size
        if len(image_data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Compress image using PIL
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Resize if too large (max 1920px width)
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # Save compressed image to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        compressed_content = output.getvalue()
        
        # Upload to Cloudinary with additional optimization
        result = cloudinary.uploader.upload(
            compressed_content,
            folder="sarees",
            resource_type="image",
            transformation=[
                {"quality": "auto:good", "fetch_format": "auto"}
            ]
        )
        
        public_url = result["secure_url"]
        logger.info(f"Base64 image uploaded to Cloudinary: {result['public_id']}")
        return public_url
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload base64 image to Cloudinary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )
