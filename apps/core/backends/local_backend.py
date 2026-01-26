"""
Local Task Backend - Synchronous execution for development.

This backend executes tasks immediately in the same process.
No Redis, SQS, or external dependencies required.

Usage:
    Set TASK_BACKEND=local in your .env file.
"""

import uuid
import logging
from typing import Any, Dict
from apps.core.task_service import TaskServiceInterface

logger = logging.getLogger(__name__)


# Task handler registry - maps task names to handler functions
TASK_HANDLERS = {}


def register_handler(task_name: str):
    """Decorator to register a task handler."""
    def decorator(func):
        TASK_HANDLERS[task_name] = func
        return func
    return decorator


class LocalTaskService(TaskServiceInterface):
    """
    Execute tasks synchronously in the same process.
    
    This is ideal for:
    - Local development without Docker/Redis
    - Unit testing with immediate execution
    - Debugging task logic
    
    Note: Tasks run in the same request cycle, so they block
    the response. Only use for development.
    """
    
    def send_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """Execute task synchronously."""
        task_id = str(uuid.uuid4())
        
        logger.info(f"[LOCAL] Executing task {task_name} (id={task_id})")
        
        if delay_seconds > 0:
            logger.warning(
                f"[LOCAL] delay_seconds={delay_seconds} ignored in local backend"
            )
        
        handler = TASK_HANDLERS.get(task_name)
        if handler:
            try:
                result = handler(**payload)
                logger.info(f"[LOCAL] Task {task_name} completed: {result}")
            except Exception as e:
                logger.exception(f"[LOCAL] Task {task_name} failed: {e}")
                raise
        else:
            logger.warning(f"[LOCAL] No handler registered for task: {task_name}")
        
        return task_id


# =============================================================================
# Task Handlers - Import and register actual task implementations
# =============================================================================

@register_handler("generate_document")
def handle_generate_document(request_id: str):
    """Generate document synchronously."""
    from uuid import UUID
    from apps.governance.models import DocumentRequest, RequestStatus
    from apps.ledger.report_service import generate_financial_document
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from django.conf import settings
    
    doc_request = DocumentRequest.objects.get(id=UUID(request_id))
    
    if doc_request.status != RequestStatus.APPROVED:
        return f"Request {request_id} is not APPROVED. Skipping."
    
    pdf_content = generate_financial_document(doc_request)
    filename = f"{doc_request.document_type}_{doc_request.id}.pdf"
    path = default_storage.save(f"documents/{filename}", ContentFile(pdf_content))
    
    doc_request.generated_file = f"{settings.MEDIA_URL}{path}"
    doc_request.status = RequestStatus.GENERATED
    doc_request.save()
    
    return f"Generated document: {path}"


@register_handler("expire_reservations")
def handle_expire_reservations():
    """Expire unpaid reservations synchronously."""
    from apps.assets import services
    count = services.expire_unpaid_reservations()
    return f"Expired {count} reservations"


@register_handler("process_ocr")
def handle_process_ocr(job_id: str):
    """Process OCR job synchronously."""
    from uuid import UUID
    from apps.intelligence.models import OCRJob
    
    job = OCRJob.objects.get(id=UUID(job_id))
    job.status = 'PROCESSING'
    job.save()
    
    # TODO: Actual OCR implementation
    job.status = 'COMPLETED'
    job.save()
    
    return f"Processed OCR job: {job_id}"


@register_handler("generate_monthly_dues_fanout")
def handle_generate_monthly_dues_fanout(org_id: str):
    """Fan out monthly dues generation to individual units."""
    from uuid import UUID
    from apps.registry.models import Unit
    from apps.core.task_service import TaskService
    
    unit_ids = Unit.objects.filter(
        org_id=UUID(org_id)
    ).values_list('id', flat=True)
    
    for unit_id in unit_ids:
        # In local mode, this executes synchronously
        TaskService.generate_dues_for_unit(unit_id)
    
    return f"Processed {len(unit_ids)} units"


@register_handler("generate_dues_for_unit")
def handle_generate_dues_for_unit(unit_id: str):
    """Generate dues for a single unit."""
    from uuid import UUID
    # TODO: Import actual dues generation service
    # from apps.ledger import services
    # services.create_dues_statement(UUID(unit_id))
    
    return f"Generated dues for unit: {unit_id}"
