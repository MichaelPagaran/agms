"""
ASGI config for AGMS project.

Optimized for AWS Lambda deployment with Mangum.
Also supports traditional ASGI servers (Daphne, Uvicorn).
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# =============================================================================
# Cold Start Optimization
# =============================================================================
# Import Django and initialize BEFORE the handler is called.
# This moves initialization to container startup, not request time.

from django.core.asgi import get_asgi_application

# Initialize Django application at module load time (container startup)
application = get_asgi_application()


# =============================================================================
# Lambda Handler (via Mangum)
# =============================================================================
# Mangum wraps the ASGI application for Lambda compatibility.
# This is used by lambda_handlers.py:api_handler

def get_lambda_handler():
    """
    Returns a Mangum-wrapped handler for AWS Lambda.
    
    Lazy initialization to avoid import errors when mangum isn't installed
    (e.g., in local development without Lambda dependencies).
    """
    try:
        from mangum import Mangum
        return Mangum(application, lifespan="off")
    except ImportError:
        raise ImportError(
            "Mangum is required for Lambda deployment. "
            "Install with: pip install mangum"
        )


# Pre-create handler if we're in Lambda environment
# This further reduces cold start by not recreating on each invocation
_lambda_handler = None

def lambda_handler(event, context):
    """
    AWS Lambda entry point for HTTP requests.
    
    This can be used directly as the Lambda handler, or you can use
    lambda_handlers.api_handler which provides more error handling.
    """
    global _lambda_handler
    if _lambda_handler is None:
        _lambda_handler = get_lambda_handler()
    return _lambda_handler(event, context)
