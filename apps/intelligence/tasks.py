"""Celery tasks for Intelligence app."""
from celery import shared_task
from .models import OCRJob


@shared_task
def process_ocr_job(job_id):
    """
    Process an OCR job using Google Cloud Vision.
    This is a placeholder - actual implementation will integrate with GCV.
    """
    try:
        job = OCRJob.objects.get(id=job_id)
        job.status = 'PROCESSING'
        job.save()
        
        # TODO: Integrate with Google Cloud Vision API
        # 1. Download image from job.image_url
        # 2. Send to Google Cloud Vision
        # 3. Parse response to extract total, date, merchant
        # 4. Update job with extracted data
        
        job.status = 'COMPLETED'
        job.save()
    except OCRJob.DoesNotExist:
        pass
    except Exception as e:
        job.status = 'FAILED'
        job.save()
        raise
