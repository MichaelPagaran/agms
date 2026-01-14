"""
Celery tasks for the Ledger app.
"""
from celery import shared_task
from uuid import UUID

from apps.organizations.models import Organization
from . import billing_service


@shared_task
def generate_monthly_dues():
    """
    Periodic task to generate monthly dues statements for all organizations.
    Should be scheduled to run on the 1st of each month via Celery Beat.
    """
    organizations = Organization.objects.filter(is_active=True)
    
    results = []
    for org in organizations:
        statements = billing_service.generate_monthly_statements(org.id)
        results.append({
            'org_id': str(org.id),
            'statements_created': len(statements),
        })
    
    return results


@shared_task
def generate_dues_for_organization(org_id: str):
    """
    Generate monthly dues statements for a specific organization.
    Can be triggered manually via admin or API.
    """
    org_uuid = UUID(org_id)
    statements = billing_service.generate_monthly_statements(org_uuid)
    return {
        'org_id': org_id,
        'statements_created': len(statements),
    }
