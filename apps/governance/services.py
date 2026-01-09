"""Services for Governance app."""
from .models import GovernanceDocument
from .dtos import GovernanceDocumentDTO


def get_documents_by_org(org_id) -> list[GovernanceDocumentDTO]:
    """Get all governance documents for an organization."""
    docs = GovernanceDocument.objects.filter(org_id=org_id)
    return [
        GovernanceDocumentDTO(
            id=d.id,
            title=d.title,
            document_type=d.document_type,
            document_date=d.document_date,
            file_url=d.file_url,
        )
        for d in docs
    ]
