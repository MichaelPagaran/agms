"""DTOs for Governance app."""
from dataclasses import dataclass
from uuid import UUID
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class GovernanceDocumentDTO:
    id: UUID
    title: str
    document_type: str
    document_date: date
    file_url: Optional[str]
