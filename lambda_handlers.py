"""
Lambda Handlers - Entry points for AWS Lambda functions.

This module provides Lambda handlers for:
1. SQS Task Processing - Consumes messages from task queue
2. Django API (via Mangum) - HTTP requests through API Gateway
3. Scheduled Events - EventBridge triggers

The handlers use Django's setup to access models and services.
"""

import os
import sys
import json
import logging

# Ensure the project root is in the path for Lambda
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django before importing any models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def sqs_task_handler(event, context):
    """
    AWS Lambda handler for SQS task messages.
    
    Processes messages from the task queue and dispatches
    to the appropriate task handler.
    
    Event structure:
    {
        "Records": [
            {
                "body": "{\"task_id\": \"...\", \"task_name\": \"...\", \"payload\": {...}}"
            }
        ]
    }
    """
    from apps.core.backends.local_backend import TASK_HANDLERS
    
    processed = 0
    failed = 0
    
    for record in event.get('Records', []):
        try:
            message = json.loads(record['body'])
            task_id = message.get('task_id', 'unknown')
            task_name = message['task_name']
            payload = message.get('payload', {})
            
            logger.info(f"Processing task {task_name} (id={task_id})")
            
            handler = TASK_HANDLERS.get(task_name)
            if handler:
                result = handler(**payload)
                logger.info(f"Task {task_name} completed: {result}")
                processed += 1
            else:
                logger.error(f"No handler for task: {task_name}")
                failed += 1
                
        except Exception as e:
            logger.exception(f"Failed to process message: {e}")
            failed += 1
            # Let the message go to DLQ by not catching
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed,
            'failed': failed
        })
    }


def scheduled_expire_reservations(event, context):
    """
    EventBridge scheduled handler: Expire unpaid reservations.
    
    Schedule: Every 30 minutes
    """
    from apps.assets import services
    
    logger.info("Running scheduled expire_reservations")
    count = services.expire_unpaid_reservations()
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'expired_count': count
        })
    }


def scheduled_monthly_dues_fanout(event, context):
    """
    EventBridge scheduled handler: Generate monthly dues.
    
    Schedule: 1st of each month at 00:00
    
    This handler fans out by queuing individual unit tasks per organization.
    """
    from apps.organizations.models import Organization
    from apps.core.task_service import TaskService
    
    logger.info("Running scheduled monthly_dues_fanout")
    
    orgs = Organization.objects.filter(is_active=True)
    queued = 0
    
    for org in orgs:
        TaskService.generate_monthly_dues_fanout(org.id)
        queued += 1
        logger.info(f"Queued dues fanout for org {org.id}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'organizations_queued': queued
        })
    }


# =============================================================================
# Django API Handler (Mangum)
# =============================================================================

# Lazy initialization to avoid import errors if mangum not installed
_asgi_handler = None

def api_handler(event, context):
    """
    AWS Lambda handler for HTTP requests via API Gateway.
    
    Uses Mangum to wrap Django's ASGI application.
    """
    global _asgi_handler
    
    if _asgi_handler is None:
        try:
            from mangum import Mangum
            from config.asgi import application
            _asgi_handler = Mangum(application, lifespan="off")
        except ImportError:
            logger.error("Mangum not installed. Run: pip install mangum")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Mangum not installed'})
            }
    
    return _asgi_handler(event, context)
