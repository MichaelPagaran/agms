"""Services for Ledger app."""
from apps.registry.services import get_unit_dto
from .models import Transaction
from .dtos import TransactionDTO


def record_expense(org_id, unit_id, amount, category, description, transaction_date, created_by_id=None):
    """Record an expense, using registry DTO for unit validation."""
    # Example of using DTO from another app
    if unit_id:
        unit_dto = get_unit_dto(unit_id)
        if not unit_dto or not unit_dto.is_active:
            raise ValueError("Invalid or inactive unit")
    
    transaction = Transaction.objects.create(
        org_id=org_id,
        unit_id=unit_id,
        transaction_type='EXPENSE',
        amount=amount,
        category=category,
        description=description,
        transaction_date=transaction_date,
        created_by_id=created_by_id,
    )
    return TransactionDTO(
        id=transaction.id,
        org_id=transaction.org_id,
        transaction_type=transaction.transaction_type,
        amount=transaction.amount,
        category=transaction.category,
        transaction_date=transaction.transaction_date,
    )
