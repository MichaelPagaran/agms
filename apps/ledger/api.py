"""
API Router for Ledger app.
Handles all financial ledger endpoints with role-based access control.
"""
from typing import List, Optional
from uuid import UUID
from datetime import date
from ninja import Router, File
from ninja.files import UploadedFile
from ninja.errors import HttpError
from django.http import HttpRequest, HttpResponse
from django.conf import settings

from apps.identity.permissions import Permissions, get_user_permissions
from apps.governance.models import AuditLog
from .schemas import (
    IncomeIn, ExpenseIn, TransactionUpdateIn, TransactionVerificationIn,
    BulkPaymentIn, PreviewBreakdownIn, CategoryIn, DiscountConfigIn,
    PenaltyPolicyIn, TransactionFilterIn, ReportFilterIn,
    TransactionOut, TransactionDetailOut, TransactionBreakdownOut,
    CategoryOut, DiscountConfigOut, PenaltyPolicyOut, AttachmentOut,
    CreditBalanceOut, CreditTransactionOut, FinancialSummaryOut,
    CategoryBreakdownOut, MonthlyTrendOut, ProfitLossOut,
    DuesStatementOut, IncomeResultOut, VerificationResultOut,
    ErrorOut, SuccessOut, AdjustmentOut, DiscountPreviewOut, PenaltyPreviewOut,
)
from .models import (
    Transaction, TransactionCategory, DiscountConfig, PenaltyPolicy,
    TransactionType, TransactionStatus, DuesStatement,
)
from . import services
from . import analytics_service
from . import attachment_service

router = Router(tags=["Ledger"])


# =============================================================================
# Helper Functions
# =============================================================================

def require_auth(request: HttpRequest):
    """Ensure user is authenticated."""
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")


def require_permission(request: HttpRequest, permission: str):
    """Ensure user has the required permission."""
    require_auth(request)
    perms = get_user_permissions(request.user)
    if permission not in perms:
        raise HttpError(403, f"Permission denied: {permission}")


def get_org_id(request: HttpRequest) -> UUID:
    """Get organization ID from authenticated user."""
    if not request.user.org_id_id:
        raise HttpError(400, "User has no organization context")
    return request.user.org_id_id


# =============================================================================
# Transaction Endpoints
# =============================================================================

@router.post("/transactions/income", response=IncomeResultOut, auth=None)
def create_income(request: HttpRequest, payload: IncomeIn):
    """
    Record an income transaction.
    Validates payment amount against dues (prevents overcollection).
    """
    require_permission(request, Permissions.LEDGER_CREATE_INCOME)
    org_id = get_org_id(request)
    
    try:
        transaction_dto, credit_added = services.record_income(
            org_id=org_id,
            amount=payload.amount,
            category=payload.category,
            description=payload.description,
            transaction_date=payload.transaction_date,
            payment_type=payload.payment_type,
            unit_id=payload.unit_id,
            category_id=payload.category_id,
            payer_name=payload.payer_name,
            reference_number=payload.reference_number,
            apply_discount_ids=payload.apply_discount_ids,
            created_by_id=request.user.id,
        )
        
        return IncomeResultOut(
            transaction=TransactionOut(
                id=transaction_dto.id,
                org_id=transaction_dto.org_id,
                transaction_type=transaction_dto.transaction_type,
                status=transaction_dto.status,
                amount=transaction_dto.amount,
                net_amount=transaction_dto.net_amount,
                category=transaction_dto.category,
                transaction_date=transaction_dto.transaction_date,
                is_verified=transaction_dto.is_verified,
            ),
            credit_added=credit_added,
        )
    except ValueError as e:
        raise HttpError(400, str(e))


@router.post("/transactions/expense", response=TransactionOut, auth=None)
def create_expense(request: HttpRequest, payload: ExpenseIn):
    """Record an expense transaction."""
    require_permission(request, Permissions.LEDGER_CREATE_EXPENSE)
    org_id = get_org_id(request)
    
    try:
        transaction_dto = services.record_expense(
            org_id=org_id,
            unit_id=payload.unit_id,
            amount=payload.amount,
            category=payload.category,
            description=payload.description,
            transaction_date=payload.transaction_date,
            created_by_id=request.user.id,
            category_id=payload.category_id,
            asset_id=payload.asset_id,
        )
        
        return TransactionOut(
            id=transaction_dto.id,
            org_id=transaction_dto.org_id,
            transaction_type=transaction_dto.transaction_type,
            status=transaction_dto.status,
            amount=transaction_dto.amount,
            net_amount=transaction_dto.net_amount,
            category=transaction_dto.category,
            transaction_date=transaction_dto.transaction_date,
            is_verified=transaction_dto.is_verified,
        )
    except ValueError as e:
        raise HttpError(400, str(e))


@router.post("/transactions/income/preview", response=TransactionBreakdownOut, auth=None)
def preview_income_breakdown(request: HttpRequest, payload: PreviewBreakdownIn):
    """
    Preview transaction breakdown before submission.
    Shows gross amount, pending penalties, applicable discounts, and net amount.
    """
    require_permission(request, Permissions.LEDGER_CREATE_INCOME)
    org_id = get_org_id(request)
    
    breakdown = services.preview_transaction_breakdown(
        org_id=org_id,
        unit_id=payload.unit_id,
        amount=payload.amount,
        payment_type=payload.payment_type,
        category_id=payload.category_id,
        apply_discount_ids=payload.apply_discount_ids,
        months=payload.months,
    )
    
    return TransactionBreakdownOut(
        gross_amount=breakdown.gross_amount,
        adjustments=[
            AdjustmentOut(
                adjustment_type=adj.adjustment_type,
                amount=adj.amount,
                reason=adj.reason,
                months_overdue=adj.months_overdue,
            )
            for adj in breakdown.adjustments
        ],
        pending_penalties=[
            PenaltyPreviewOut(
                name=p.name,
                principal=p.principal,
                rate=p.rate,
                months_overdue=p.months_overdue,
                calculated_amount=p.calculated_amount,
            )
            for p in breakdown.pending_penalties
        ],
        applicable_discounts=[
            DiscountPreviewOut(
                id=d.id,
                name=d.name,
                discount_type=d.discount_type,
                value=d.value,
                calculated_amount=d.calculated_amount,
            )
            for d in breakdown.applicable_discounts
        ],
        net_amount=breakdown.net_amount,
        credit_to_add=breakdown.credit_to_add,
    )


@router.get("/transactions", response=List[TransactionOut], auth=None)
def list_transactions(
    request: HttpRequest,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    unit_id: Optional[UUID] = None,
    limit: int = 100,
):
    """List transactions with optional filtering."""
    require_permission(request, Permissions.LEDGER_VIEW_TRANSACTIONS)
    org_id = get_org_id(request)
    
    transactions = services.list_transactions(
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        transaction_type=transaction_type,
        status=status,
        unit_id=unit_id,
        limit=limit,
    )
    
    # Log audit
    try:
        AuditLog.objects.create(
            org_id=org_id,
            action="VIEW_LEDGER",
            target_type="TransactionList",
            target_id=org_id,
            target_label=f"Ledger View ({len(transactions)} items)",
            performed_by=request.user,
            context={
                "filters": {
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                    "category_id": str(category_id) if category_id else None,
                    "transaction_type": transaction_type,
                    "status": status,
                    "unit_id": str(unit_id) if unit_id else None,
                }
            }
        )
    except Exception:
        # Don't fail the request if logging fails
        pass
    
    return [
        TransactionOut(
            id=t.id,
            org_id=t.org_id,
            transaction_type=t.transaction_type,
            status=t.status,
            amount=t.amount,
            net_amount=t.net_amount,
            category=t.category,
            transaction_date=t.transaction_date,
            is_verified=t.is_verified,
        )
        for t in transactions
    ]


@router.get("/transactions/{transaction_id}", response=TransactionDetailOut, auth=None)
def get_transaction(request: HttpRequest, transaction_id: UUID):
    """Get detailed transaction by ID."""
    require_permission(request, Permissions.LEDGER_VIEW_TRANSACTIONS)
    
    transaction_dto = services.get_transaction_detail_dto(transaction_id)
    if not transaction_dto:
        raise HttpError(404, "Transaction not found")
    
    # Verify org access
    org_id = get_org_id(request)
    if transaction_dto.org_id != org_id:
        raise HttpError(403, "Access denied")
    
    return TransactionDetailOut(
        id=transaction_dto.id,
        org_id=transaction_dto.org_id,
        unit_id=transaction_dto.unit_id,
        category_id=transaction_dto.category_id,
        transaction_type=transaction_dto.transaction_type,
        status=transaction_dto.status,
        payment_type=transaction_dto.payment_type,
        gross_amount=transaction_dto.gross_amount,
        net_amount=transaction_dto.net_amount,
        category=transaction_dto.category,
        description=transaction_dto.description,
        payer_name=transaction_dto.payer_name,
        reference_number=transaction_dto.reference_number,
        transaction_date=transaction_dto.transaction_date,
        requires_receipt=transaction_dto.requires_receipt,
        receipt_verified=transaction_dto.receipt_verified,
        created_by_id=transaction_dto.created_by_id,
        verified_by_id=transaction_dto.verified_by_id,
        verified_at=transaction_dto.verified_at,
        created_at=transaction_dto.created_at,
        is_verified=transaction_dto.is_verified,
    )


# =============================================================================
# Approval Workflow Endpoints
# =============================================================================

@router.post("/transactions/{transaction_id}/verify", response=VerificationResultOut, auth=None)
def verify_transaction(request: HttpRequest, transaction_id: UUID):
    """Verify a posted transaction."""
    require_permission(request, Permissions.LEDGER_APPROVE_EXPENSE)
    
    try:
        transaction_dto = services.verify_transaction(
            transaction_id=transaction_id,
            verified_by_id=request.user.id,
        )
        return VerificationResultOut(
            transaction=TransactionOut(
                id=transaction_dto.id,
                org_id=transaction_dto.org_id,
                transaction_type=transaction_dto.transaction_type,
                status=transaction_dto.status,
                amount=transaction_dto.amount,
                net_amount=transaction_dto.net_amount,
                category=transaction_dto.category,
                transaction_date=transaction_dto.transaction_date,
                is_verified=transaction_dto.is_verified,
            ),
            message="Transaction verified",
        )
    except ValueError as e:
        raise HttpError(400, str(e))





@router.post("/transactions/{transaction_id}/cancel", response=TransactionOut, auth=None)
def cancel_transaction(request: HttpRequest, transaction_id: UUID, payload: TransactionVerificationIn):
    """Cancel a transaction."""
    require_permission(request, Permissions.LEDGER_CANCEL_TRANSACTION)
    
    try:
        transaction_dto = services.cancel_transaction(
            transaction_id=transaction_id,
            cancelled_by_id=request.user.id,
            reason=payload.comment or "",
        )
        return TransactionOut(
            id=transaction_dto.id,
            org_id=transaction_dto.org_id,
            transaction_type=transaction_dto.transaction_type,
            status=transaction_dto.status,
            amount=transaction_dto.amount,
            net_amount=transaction_dto.net_amount,
            category=transaction_dto.category,
            transaction_date=transaction_dto.transaction_date,
            is_verified=transaction_dto.is_verified,
        )
    except ValueError as e:
        raise HttpError(400, str(e))


# =============================================================================
# Attachment Endpoints
# =============================================================================

@router.post("/transactions/{transaction_id}/attachments", response=AttachmentOut, auth=None)
def upload_attachment(
    request: HttpRequest, 
    transaction_id: UUID, 
    file: UploadedFile = File(...)
):
    """Upload a receipt attachment for a transaction."""
    require_permission(request, Permissions.LEDGER_CREATE_INCOME)
    
    try:
        attachment = attachment_service.upload_receipt(
            file=file,
            transaction_id=transaction_id,
            uploaded_by_id=request.user.id,
        )
        
        response = AttachmentOut(
            id=attachment.id,
            transaction_id=attachment.transaction_id,
            file_url=attachment.file_url,
            file_name=attachment.file_name,
            file_type=attachment.file_type,
            file_size=attachment.file_size,
            created_at=attachment.created_at,
        )
        
        # Add warning in debug mode if S3 is not configured
        if settings.DEBUG and not getattr(settings, 'USE_S3_STORAGE', False):
            response._warning = "Using local storage. Configure AWS S3 for production."
        
        return response
    except ValueError as e:
        raise HttpError(400, str(e))


@router.get("/transactions/{transaction_id}/attachments", response=List[AttachmentOut], auth=None)
def list_attachments(request: HttpRequest, transaction_id: UUID):
    """List all attachments for a transaction."""
    require_permission(request, Permissions.LEDGER_VIEW_TRANSACTIONS)
    
    attachments = attachment_service.get_attachments_for_transaction(transaction_id)
    return [
        AttachmentOut(
            id=UUID(att['id']),
            transaction_id=transaction_id,
            file_url=att['file_url'],
            file_name=att['file_name'],
            file_type=att['file_type'],
            file_size=att['file_size'],
            created_at=att['created_at'],
        )
        for att in attachments
    ]


# =============================================================================
# Credit Endpoints
# =============================================================================

@router.get("/credits/{unit_id}", response=CreditBalanceOut, auth=None)
def get_credit_balance(request: HttpRequest, unit_id: UUID):
    """Get current credit balance for a unit."""
    require_permission(request, Permissions.LEDGER_VIEW_TRANSACTIONS)
    
    credit_dto = services.get_credit_balance_dto(unit_id)
    if not credit_dto:
        # Return zero balance
        from decimal import Decimal
        from django.utils import timezone
        return CreditBalanceOut(
            unit_id=unit_id,
            credit_balance=Decimal('0.00'),
            last_updated=timezone.now(),
        )
    
    return CreditBalanceOut(
        unit_id=credit_dto.unit_id,
        credit_balance=credit_dto.credit_balance,
        last_updated=credit_dto.last_updated,
    )


@router.get("/credits/{unit_id}/history", response=List[CreditTransactionOut], auth=None)
def get_credit_history(request: HttpRequest, unit_id: UUID, limit: int = 50):
    """Get credit transaction history for a unit."""
    require_permission(request, Permissions.LEDGER_VIEW_TRANSACTIONS)
    
    history = services.get_credit_history(unit_id, limit)
    return [
        CreditTransactionOut(
            id=h.id,
            transaction_type=h.transaction_type,
            amount=h.amount,
            balance_after=h.balance_after,
            description=h.description,
            created_at=h.created_at,
        )
        for h in history
    ]


# =============================================================================
# Analytics Endpoints
# =============================================================================

@router.get("/analytics/summary", response=FinancialSummaryOut, auth=None)
def get_financial_summary(request: HttpRequest, period: str = 'MTD'):
    """Get financial summary (MTD or YTD)."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    summary = analytics_service.get_combined_summary(org_id, period)
    
    return FinancialSummaryOut(
        period=summary.period,
        total_income=summary.total_income,
        total_expense=summary.total_expense,
        net_balance=summary.net_balance,
        transaction_count=summary.transaction_count,
    )


@router.get("/analytics/expenses/by-category", response=List[CategoryBreakdownOut], auth=None)
def get_expenses_by_category(
    request: HttpRequest,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get expense breakdown by category."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    breakdown = analytics_service.get_expense_by_category(org_id, start_date, end_date)
    
    return [
        CategoryBreakdownOut(
            category_id=b.category_id,
            category_name=b.category_name,
            total_amount=b.total_amount,
            transaction_count=b.transaction_count,
            percentage=b.percentage,
        )
        for b in breakdown
    ]


@router.get("/analytics/income/by-category", response=List[CategoryBreakdownOut], auth=None)
def get_income_by_category(
    request: HttpRequest,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get income breakdown by category."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    breakdown = analytics_service.get_income_by_category(org_id, start_date, end_date)
    
    return [
        CategoryBreakdownOut(
            category_id=b.category_id,
            category_name=b.category_name,
            total_amount=b.total_amount,
            transaction_count=b.transaction_count,
            percentage=b.percentage,
        )
        for b in breakdown
    ]


@router.get("/analytics/trends", response=List[MonthlyTrendOut], auth=None)
def get_monthly_trends(request: HttpRequest, months: int = 12):
    """Get monthly income/expense trends."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    trends = analytics_service.get_monthly_trends(org_id, months)
    
    return [
        MonthlyTrendOut(
            year=t.year,
            month=t.month,
            income=t.income,
            expense=t.expense,
            net=t.net,
        )
        for t in trends
    ]


@router.get("/analytics/best-worst-months", auth=None)
def get_best_worst_months(request: HttpRequest, year: Optional[int] = None):
    """Get best and worst performing months."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    return analytics_service.get_best_worst_months(org_id, year)


@router.get("/analytics/profit-loss", response=ProfitLossOut, auth=None)
def get_profit_loss_status(request: HttpRequest, period: str = 'MTD'):
    """Get current profit/loss status."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    status = analytics_service.get_profit_loss_status(org_id, period)
    
    return ProfitLossOut(
        period=status.period,
        total_income=status.total_income,
        total_expense=status.total_expense,
        net_balance=status.net_balance,
        is_profitable=status.is_profitable,
        percentage_recovered=status.percentage_recovered,
    )


# =============================================================================
# Category Configuration Endpoints
# =============================================================================

@router.get("/categories", response=List[CategoryOut], auth=None)
def list_categories(
    request: HttpRequest,
    transaction_type: Optional[str] = None,
):
    """List transaction categories."""
    require_permission(request, Permissions.LEDGER_VIEW_TRANSACTIONS)
    org_id = get_org_id(request)
    
    queryset = TransactionCategory.objects.filter(org_id=org_id, is_active=True)
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)
    
    return [
        CategoryOut(
            id=c.id,
            name=c.name,
            transaction_type=c.transaction_type,
            description=c.description,
            is_active=c.is_active,
            is_default=c.is_default,
        )
        for c in queryset
    ]


@router.post("/categories", response=CategoryOut, auth=None)
def create_category(request: HttpRequest, payload: CategoryIn):
    """Create a transaction category."""
    require_permission(request, Permissions.LEDGER_MANAGE_CONFIG)
    org_id = get_org_id(request)
    
    category = TransactionCategory.objects.create(
        org_id=org_id,
        name=payload.name,
        transaction_type=payload.transaction_type,
        description=payload.description,
    )
    
    return CategoryOut(
        id=category.id,
        name=category.name,
        transaction_type=category.transaction_type,
        description=category.description,
        is_active=category.is_active,
        is_default=category.is_default,
    )


# =============================================================================
# Discount Configuration Endpoints
# =============================================================================

@router.get("/discounts", response=List[DiscountConfigOut], auth=None)
def list_discounts(request: HttpRequest):
    """List discount configurations."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    discounts = DiscountConfig.objects.filter(org_id=org_id, is_active=True)
    
    return [
        DiscountConfigOut(
            id=d.id,
            name=d.name,
            description=d.description,
            discount_type=d.discount_type,
            value=d.value,
            min_months=d.min_months,
            is_active=d.is_active,
        )
        for d in discounts
    ]


@router.post("/discounts", response=DiscountConfigOut, auth=None)
def create_discount(request: HttpRequest, payload: DiscountConfigIn):
    """Create a discount configuration."""
    require_permission(request, Permissions.LEDGER_MANAGE_CONFIG)
    org_id = get_org_id(request)
    
    discount = DiscountConfig.objects.create(
        org_id=org_id,
        name=payload.name,
        description=payload.description,
        discount_type=payload.discount_type,
        value=payload.value,
        applicable_categories=payload.applicable_categories or [],
        min_months=payload.min_months,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )
    
    return DiscountConfigOut(
        id=discount.id,
        name=discount.name,
        description=discount.description,
        discount_type=discount.discount_type,
        value=discount.value,
        min_months=discount.min_months,
        is_active=discount.is_active,
    )


# =============================================================================
# Penalty Policy Endpoints
# =============================================================================

@router.get("/penalties", response=List[PenaltyPolicyOut], auth=None)
def list_penalty_policies(request: HttpRequest):
    """List penalty policies."""
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    policies = PenaltyPolicy.objects.filter(org_id=org_id, is_active=True)
    
    return [
        PenaltyPolicyOut(
            id=p.id,
            name=p.name,
            description=p.description,
            rate_type=p.rate_type,
            rate_value=p.rate_value,
            grace_period_days=p.grace_period_days,
            is_active=p.is_active,
        )
        for p in policies
    ]


@router.post("/penalties", response=PenaltyPolicyOut, auth=None)
def create_penalty_policy(request: HttpRequest, payload: PenaltyPolicyIn):
    """Create a penalty policy."""
    require_permission(request, Permissions.LEDGER_MANAGE_CONFIG)
    org_id = get_org_id(request)
    
    policy = PenaltyPolicy.objects.create(
        org_id=org_id,
        name=payload.name,
        description=payload.description,
        rate_type=payload.rate_type,
        rate_value=payload.rate_value,
        grace_period_days=payload.grace_period_days,
        applicable_categories=payload.applicable_categories or [],
    )
    
    return PenaltyPolicyOut(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        rate_type=policy.rate_type,
        rate_value=policy.rate_value,
        grace_period_days=policy.grace_period_days,
        is_active=policy.is_active,
    )


# =============================================================================
# Billing Configuration Endpoints
# =============================================================================

@router.get("/billing/config", auth=None)
def get_billing_config(request: HttpRequest):
    """Get billing configuration for the organization."""
    from .schemas import BillingConfigOut
    from .models import BillingConfig
    
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    config = BillingConfig.objects.filter(org_id=org_id).first()
    if not config:
        raise HttpError(404, "Billing configuration not found")
    
    return BillingConfigOut(
        id=config.id,
        org_id=config.org_id,
        monthly_dues_amount=config.monthly_dues_amount,
        billing_day=config.billing_day,
        grace_period_days=config.grace_period_days,
        is_active=config.is_active,
    )


@router.post("/billing/config", auth=None)
def create_or_update_billing_config(request: HttpRequest):
    """Create or update billing configuration."""
    from .schemas import BillingConfigIn, BillingConfigOut
    from .models import BillingConfig
    from ninja import Body
    
    require_permission(request, Permissions.LEDGER_MANAGE_CONFIG)
    org_id = get_org_id(request)
    
    import json
    data = json.loads(request.body)
    
    config, created = BillingConfig.objects.update_or_create(
        org_id=org_id,
        defaults={
            'monthly_dues_amount': data.get('monthly_dues_amount'),
            'billing_day': data.get('billing_day', 1),
            'grace_period_days': data.get('grace_period_days', 15),
            'is_active': True,
        }
    )
    
    return BillingConfigOut(
        id=config.id,
        org_id=config.org_id,
        monthly_dues_amount=config.monthly_dues_amount,
        billing_day=config.billing_day,
        grace_period_days=config.grace_period_days,
        is_active=config.is_active,
    )


@router.post("/billing/generate", auth=None)
def trigger_billing_generation(request: HttpRequest):
    """Manually trigger billing generation for the organization."""
    from .schemas import GenerateBillingResultOut
    from . import billing_service
    
    require_permission(request, Permissions.LEDGER_MANAGE_CONFIG)
    org_id = get_org_id(request)
    
    statements = billing_service.generate_monthly_statements(org_id)
    
    return GenerateBillingResultOut(
        org_id=org_id,
        statements_created=len(statements),
    )


# =============================================================================
# PDF Report Endpoints
# =============================================================================

@router.get("/reports/daily", auth=None)
def download_daily_report(
    request: HttpRequest,
    report_date: Optional[date] = None,
):
    """
    Generate and download a daily financial report PDF.
    Defaults to today if no date provided.
    """
    from django.utils import timezone
    from . import report_service
    from apps.organizations.models import Organization
    
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    if not report_date:
        report_date = timezone.now().date()
    
    # Get organization details
    try:
        org = Organization.objects.get(id=org_id)
        org_name = org.name
        org_address = org.settings.get('address', '') if org.settings else ''
    except Organization.DoesNotExist:
        org_name = "Organization"
        org_address = ""
    
    try:
        pdf_content = report_service.generate_daily_report(
            org_id=org_id,
            org_name=org_name,
            report_date=report_date,
            org_address=org_address,
        )
        
        filename = f"daily_report_{report_date.strftime('%Y%m%d')}.pdf"
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except ImportError as e:
        raise HttpError(500, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to generate report: {str(e)}")


@router.get("/reports/monthly", auth=None)
def download_monthly_report(
    request: HttpRequest,
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """
    Generate and download a monthly financial report PDF.
    Defaults to current month if not provided.
    """
    from django.utils import timezone
    from . import report_service
    from apps.organizations.models import Organization
    
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    today = timezone.now().date()
    if not year:
        year = today.year
    if not month:
        month = today.month
    
    # Validate month
    if month < 1 or month > 12:
        raise HttpError(400, "Month must be between 1 and 12")
    
    # Get organization details
    try:
        org = Organization.objects.get(id=org_id)
        org_name = org.name
        org_address = org.settings.get('address', '') if org.settings else ''
    except Organization.DoesNotExist:
        org_name = "Organization"
        org_address = ""
    
    try:
        pdf_content = report_service.generate_monthly_report(
            org_id=org_id,
            org_name=org_name,
            year=year,
            month=month,
            org_address=org_address,
        )
        
        filename = f"monthly_report_{year}{month:02d}.pdf"
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except ImportError as e:
        raise HttpError(500, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to generate report: {str(e)}")


@router.get("/reports/yearly", auth=None)
def download_yearly_report(
    request: HttpRequest,
    year: Optional[int] = None,
):
    """
    Generate and download a yearly financial report PDF.
    Defaults to current year if not provided.
    """
    from django.utils import timezone
    from . import report_service
    from apps.organizations.models import Organization
    
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)
    
    if not year:
        year = timezone.now().year
    
    # Get organization details
    try:
        org = Organization.objects.get(id=org_id)
        org_name = org.name
        org_address = org.settings.get('address', '') if org.settings else ''
    except Organization.DoesNotExist:
        org_name = "Organization"
        org_address = ""
    
    try:
        pdf_content = report_service.generate_yearly_report(
            org_id=org_id,
            org_name=org_name,
            year=year,
            org_address=org_address,
        )
        
        filename = f"annual_report_{year}.pdf"
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except ImportError as e:
        raise HttpError(500, str(e))
    except Exception as e:
        raise HttpError(500, f"Failed to generate report: {str(e)}")

