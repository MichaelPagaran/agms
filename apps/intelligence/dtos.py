"""DTOs for Intelligence app."""
from dataclasses import dataclass
from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class OCRResultDTO:
    job_id: UUID
    status: str
    extracted_total: Optional[Decimal]
    extracted_date: Optional[date]
    extracted_merchant: str
