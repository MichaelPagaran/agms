"""DTOs for Ledger app."""
from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal
from datetime import date


@dataclass(frozen=True)
class TransactionDTO:
    id: UUID
    org_id: UUID
    transaction_type: str
    amount: Decimal
    category: str
    transaction_date: date
