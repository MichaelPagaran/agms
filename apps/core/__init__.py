"""
Core app - Shared abstractions and utilities.

This app provides platform-agnostic interfaces for:
- Task execution (TaskService)
- Database configuration (future)

These abstractions allow switching between:
- Local development (sync execution)
- AWS Lambda + SQS (production)
- Celery + Redis (fallback)
"""
