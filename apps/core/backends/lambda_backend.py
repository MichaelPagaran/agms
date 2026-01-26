"""
Lambda Task Backend - Async execution via AWS SQS + Lambda.

This backend sends messages to SQS, which triggers Lambda functions.
Designed for serverless production deployment.

Usage:
    Set TASK_BACKEND=lambda in your .env file.
    Requires:
    - AWS credentials configured
    - SQS queue created
    - Lambda functions deployed

Environment Variables:
    TASK_QUEUE_URL: SQS queue URL for task messages
    AWS_REGION: AWS region (default: ap-southeast-1)
"""

import os
import json
import uuid
import logging
from typing import Any, Dict
from apps.core.task_service import TaskServiceInterface

logger = logging.getLogger(__name__)


class LambdaTaskService(TaskServiceInterface):
    """
    Execute tasks via AWS SQS + Lambda.
    
    Messages are sent to SQS with task name and payload.
    Lambda functions consume from the queue and execute tasks.
    """
    
    def __init__(self):
        self._sqs_client = None
        self._queue_url = os.getenv('TASK_QUEUE_URL')
        
        if not self._queue_url:
            logger.warning(
                "[LAMBDA] TASK_QUEUE_URL not set. "
                "Lambda backend will fail on send_task."
            )
    
    @property
    def sqs_client(self):
        """Lazy initialization of SQS client."""
        if self._sqs_client is None:
            import boto3
            self._sqs_client = boto3.client(
                'sqs',
                region_name=os.getenv('AWS_REGION', 'ap-southeast-1')
            )
        return self._sqs_client
    
    def send_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        """Queue task via SQS."""
        task_id = str(uuid.uuid4())
        
        if not self._queue_url:
            raise RuntimeError(
                "TASK_QUEUE_URL environment variable not set. "
                "Cannot send tasks to Lambda backend."
            )
        
        message_body = json.dumps({
            "task_id": task_id,
            "task_name": task_name,
            "payload": payload,
        })
        
        logger.info(f"[LAMBDA] Sending task {task_name} to SQS (id={task_id})")
        
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self._queue_url,
                MessageBody=message_body,
                DelaySeconds=min(delay_seconds, 900),  # SQS max is 15 min
                MessageAttributes={
                    'TaskName': {
                        'DataType': 'String',
                        'StringValue': task_name,
                    },
                    'TaskId': {
                        'DataType': 'String',
                        'StringValue': task_id,
                    },
                },
            )
            
            logger.info(
                f"[LAMBDA] Task {task_name} queued. "
                f"SQS MessageId: {response['MessageId']}"
            )
            
        except Exception as e:
            logger.exception(f"[LAMBDA] Failed to send task {task_name}: {e}")
            raise
        
        return task_id
