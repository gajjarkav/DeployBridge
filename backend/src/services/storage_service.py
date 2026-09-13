import cloudinary
import cloudinary.uploader
from ..core.config import get_settings
from ..core.logger import logger

settings = get_settings()

# Initialize Cloudinary configuration
# We configure it directly or let it pull from CLOUDINARY_URL if available
cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", None)
api_key = getattr(settings, "CLOUDINARY_API_KEY", None)
api_secret = getattr(settings, "CLOUDINARY_API_SECRET", None)

if cloud_name and api_key and api_secret:
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )
    CLOUDINARY_CONFIGURED = True
else:
    CLOUDINARY_CONFIGURED = False

class StorageService:
    @staticmethod
    def upload_pdf(pdf_bytes: bytes, repo_full_name: str, report_id: str) -> str | None:
        """
        Uploads a PDF byte array to Cloudinary and returns the secure URL.
        Returns None if Cloudinary is not configured or upload fails.
        """
        if not CLOUDINARY_CONFIGURED:
            logger.info("Cloudinary is not configured. Skipping PDF upload.")
            return None

        try:
            # We must use upload_stream since we have bytes in memory, not a file on disk
            # Cloudinary uploader doesn't natively take bytes, so we can upload as string or using unsigned
            result = cloudinary.uploader.upload(
                pdf_bytes,
                resource_type="raw",
                public_id=f"reports/{repo_full_name}/{report_id}.pdf",
                format="pdf"
            )
            
            return result.get("secure_url")
            
        except Exception as e:
            logger.error(f"Failed to upload PDF to Cloudinary: {str(e)}")
            return None
