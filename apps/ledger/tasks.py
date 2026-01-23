from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from apps.governance.models import DocumentRequest, RequestStatus
from apps.ledger.report_service import generate_financial_document
import logging

logger = logging.getLogger(__name__)

@shared_task
def generate_document_task(request_id):
    """
    Generate PDF for approved document request.
    """
    try:
        doc_request = DocumentRequest.objects.get(id=request_id)
        
        if doc_request.status != RequestStatus.APPROVED:
            logger.warning(f"Request {request_id} is not APPROVED. Skipping generation.")
            return

        logger.info(f"Generating document for request {request_id} ({doc_request.document_type})")
        
        pdf_content = generate_financial_document(doc_request)
        
        # Save file to S3 or Media
        # Since we use URLField, we might need to save to storage and get URL.
        # For simplicity in this setup, we assume we can save to a default storage logic if FileField
        # But here generated_file IS a URLField. 
        # Usually implies external storage or serve view.
        # Let's save creating a simple file name and assume local media serve.
        
        filename = f"{doc_request.document_type}_{doc_request.id}.pdf"
        # We need to save this content to MEDIA_ROOT/documents/... and update URL.
        # Or better: Update DocumentRequest to use FileField in future.
        # For now, we manually save to default storage.
        
        from django.core.files.storage import default_storage
        path = default_storage.save(f"documents/{filename}", ContentFile(pdf_content))
        
        # Construct URL
        # Assuming MEDIA_URL is configured
        from django.conf import settings
        file_url = f"{settings.MEDIA_URL}{path}"
        
        doc_request.generated_file = file_url
        doc_request.status = RequestStatus.GENERATED
        doc_request.save()
        
        logger.info(f"Document generated successfully: {file_url}")
        
    except DocumentRequest.DoesNotExist:
        logger.error(f"DocumentRequest {request_id} not found.")
    except Exception as e:
        logger.exception(f"Error generating document for {request_id}: {str(e)}")
        # Optionally set status to error?
