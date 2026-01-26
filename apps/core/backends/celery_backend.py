"""
Celery Task Backend - Async execution via Celery + Redis.

This backend uses the existing Celery infrastructure.
Serves as a fallback option if Lambda doesn't meet requirements.

Usage:
    Set TASK_BACKEND=celery in your .env file.
    Requires Redis and Celery worker running.
"""

import uuid
import logging
from typing import Any, Dict
from apps.core.task_service import TaskServiceInterface

logger = logging.getLogger(__name__)


# Map task names to Celery task functions
def _get_celery_task(task_name: str):
    """Get the Celery task function for a task name."""
    task_map = {
        "generate_document": "apps.ledger.tasks.generate_document_task",
        "expire_reservations": "apps.assets.tasks.expire_unpaid_reservations",
        "process_ocr": "apps.intelligence.tasks.process_ocr_job",
        # Fan-out tasks - need to be created
        "generate_monthly_dues_fanout": "apps.ledger.tasks.generate_monthly_dues",
        "generate_dues_for_unit": "apps.ledger.tasks.generate_dues_for_unit",
    }
    
    task_path = task_map.get(task_name)
    if not task_path:
        raise ValueError(f"No Celery task mapped for: {task_name}")
    
    from celery import current_app
    return current_app.tasks.get(task_path)


class CeleryTaskService(TaskServiceInterface):
    """
    Execute tasks via Celery + Redis.
    
    This backend delegates to existing Celery tasks,
    maintaining backward compatibility during migration.
    """
    
    def send_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """Queue task via Celery."""
        task_id = str(uuid.uuid4())
        
        logger.info(f"[CELERY] Queueing task {task_name} (id={task_id})")
        
        task = _get_celery_task(task_name)
        
        if task is None:
            logger.error(f"[CELERY] Task not found: {task_name}")
            raise ValueError(f"Celery task not found: {task_name}")
        
        # Extract the relevant argument based on task
        if task_name == "generate_document":
            args = [payload.get("request_id")]
        elif task_name == "process_ocr":
            args = [payload.get("job_id")]
        elif task_name == "generate_dues_for_unit":
            args = [payload.get("unit_id")]
        elif task_name == "generate_monthly_dues_fanout":
            args = [payload.get("org_id")]
        else:
            args = []
        
        if delay_seconds > 0:
            task.apply_async(args=args, countdown=delay_seconds, task_id=task_id)
        else:
            task.apply_async(args=args, task_id=task_id)
        
        return task_id
