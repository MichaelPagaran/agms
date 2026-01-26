"""
TaskService - Abstraction layer for async task execution.

This module provides a platform-agnostic interface for executing background tasks.
The actual backend is determined by the TASK_BACKEND environment variable.

Usage:
    from apps.core.task_service import TaskService
    
    # Queue a document generation task
    TaskService.generate_document(request_id=uuid)
    
    # Queue OCR processing
    TaskService.process_ocr(job_id=uuid)

Environment Configuration:
    TASK_BACKEND=local   # Sync execution (development)
    TASK_BACKEND=lambda  # AWS Lambda + SQS (production)
    TASK_BACKEND=celery  # Celery + Redis (fallback)
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class TaskServiceInterface(ABC):
    """
    Abstract interface for async task execution.
    
    Implementations:
    - LocalTaskService: Sync execution for development/testing
    - LambdaTaskService: AWS Lambda + SQS for production
    - CeleryTaskService: Celery + Redis as fallback
    """
    
    @abstractmethod
    def send_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """
        Queue a task for async execution.
        
        Args:
            task_name: Identifier for the task handler
            payload: Data to pass to the task
            delay_seconds: Delay before execution (0 = immediate)
            
        Returns:
            Task ID for tracking
        """
        pass


def _get_backend() -> TaskServiceInterface:
    """Get the configured task backend based on TASK_BACKEND env var."""
    backend = os.getenv('TASK_BACKEND', 'local')
    
    if backend == 'local':
        from apps.core.backends.local_backend import LocalTaskService
        return LocalTaskService()
    elif backend == 'lambda':
        from apps.core.backends.lambda_backend import LambdaTaskService
        return LambdaTaskService()
    elif backend == 'celery':
        from apps.core.backends.celery_backend import CeleryTaskService
        return CeleryTaskService()
    else:
        raise ValueError(f"Unknown TASK_BACKEND: {backend}")


class TaskService:
    """
    Facade for sending async tasks.
    
    This class provides static methods for each task type,
    delegating to the configured backend.
    """
    
    @staticmethod
    def generate_document(request_id: UUID) -> str:
        """
        Queue document generation task.
        
        Used by: Governance app for PDF generation after approval.
        """
        logger.info(f"Queueing generate_document task for request {request_id}")
        return _get_backend().send_task(
            task_name="generate_document",
            payload={"request_id": str(request_id)}
        )
    
    @staticmethod
    def expire_reservations() -> str:
        """
        Queue reservation expiration check.
        
        Used by: Scheduled job to expire unpaid reservations.
        """
        logger.info("Queueing expire_reservations task")
        return _get_backend().send_task(
            task_name="expire_reservations",
            payload={}
        )
    
    @staticmethod
    def process_ocr(job_id: UUID) -> str:
        """
        Queue OCR processing task.
        
        Used by: Intelligence app for receipt scanning.
        """
        logger.info(f"Queueing process_ocr task for job {job_id}")
        return _get_backend().send_task(
            task_name="process_ocr",
            payload={"job_id": str(job_id)}
        )
    
    @staticmethod
    def generate_monthly_dues_fanout(org_id: UUID) -> str:
        """
        Queue monthly dues generation for all units in an organization.
        
        This is a fan-out task that will queue individual unit tasks.
        Used by: Scheduled job on 1st of each month.
        """
        logger.info(f"Queueing generate_monthly_dues_fanout for org {org_id}")
        return _get_backend().send_task(
            task_name="generate_monthly_dues_fanout",
            payload={"org_id": str(org_id)}
        )
    
    @staticmethod
    def generate_dues_for_unit(unit_id: UUID) -> str:
        """
        Queue dues generation for a single unit.
        
        Used by: Fan-out from generate_monthly_dues_fanout.
        Atomic, fast, retryable.
        """
        logger.info(f"Queueing generate_dues_for_unit for unit {unit_id}")
        return _get_backend().send_task(
            task_name="generate_dues_for_unit",
            payload={"unit_id": str(unit_id)}
        )
