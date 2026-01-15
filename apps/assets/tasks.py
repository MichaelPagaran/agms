"""Celery tasks for Assets app."""
from celery import shared_task
from . import services


@shared_task
def expire_unpaid_reservations():
    """
    Run periodically to expire reservations that haven't been paid.
    Should be scheduled to run every 15-30 minutes.
    
    User Story #9: Auto-expire unpaid reservations.
    
    Returns count of expired reservations for logging.
    """
    count = services.expire_unpaid_reservations()
    return f"Expired {count} unpaid reservations"
