"""Services for Intelligence app."""
from .models import OCRJob


def create_ocr_job(org_id, image_url, created_by_id=None) -> OCRJob:
    """Create a new OCR processing job."""
    return OCRJob.objects.create(
        org_id=org_id,
        image_url=image_url,
        created_by_id=created_by_id,
    )
