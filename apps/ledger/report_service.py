"""
PDF Report Generation Service.
Uses WeasyPrint to generate PDF reports from HTML templates.
"""
import logging
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from io import BytesIO

from django.template.loader import render_to_string
from django.utils import timezone

from .models import Transaction, TransactionType, TransactionStatus
from . import analytics_service

logger = logging.getLogger(__name__)

# Month names for display
MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def _get_weasyprint():
    """Lazy import WeasyPrint to avoid import errors if not installed."""
    try:
        from weasyprint import HTML
        return HTML
    except ImportError:
        logger.error("WeasyPrint is not installed. Install with: pip install weasyprint")
        raise ImportError(
            "WeasyPrint is required for PDF generation. "
            "Install it with: pip install weasyprint"
        )


def generate_daily_report(
    org_id: UUID,
    org_name: str,
    report_date: date,
    org_address: str = "",
) -> bytes:
    """
    Generate a daily financial report PDF.
    
    Args:
        org_id: Organization UUID
        org_name: Organization display name
        report_date: Date for the report
        org_address: Optional organization address
        
    Returns:
        PDF file as bytes
    """
    HTML = _get_weasyprint()
    
    # Get transactions for the day
    income_transactions = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.APPROVED,
        transaction_date=report_date,
    ).order_by('created_at')
    
    expense_transactions = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.APPROVED,
        transaction_date=report_date,
    ).order_by('created_at')
    
    # Calculate totals
    total_income = sum(t.net_amount for t in income_transactions) or Decimal('0.00')
    total_expense = sum(t.net_amount for t in expense_transactions) or Decimal('0.00')
    net_balance = total_income - total_expense
    
    # Render HTML
    context = {
        'title': 'Daily Financial Report',
        'org_name': org_name,
        'org_address': org_address,
        'period': report_date.strftime('%B %d, %Y'),
        'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        'income_transactions': income_transactions,
        'expense_transactions': expense_transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
    }
    
    html_content = render_to_string('ledger/reports/daily_report.html', context)
    
    # Generate PDF
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file.read()


def generate_monthly_report(
    org_id: UUID,
    org_name: str,
    year: int,
    month: int,
    org_address: str = "",
) -> bytes:
    """
    Generate a monthly financial report PDF.
    
    Args:
        org_id: Organization UUID
        org_name: Organization display name
        year: Report year
        month: Report month (1-12)
        org_address: Optional organization address
        
    Returns:
        PDF file as bytes
    """
    HTML = _get_weasyprint()
    
    # Calculate date range
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    # Get all transactions for the month
    transactions = Transaction.objects.filter(
        org_id=org_id,
        status=TransactionStatus.APPROVED,
        transaction_date__gte=start_date,
        transaction_date__lt=end_date,
    ).order_by('transaction_date', 'created_at')
    
    # Get category breakdowns
    income_by_category = analytics_service.get_income_by_category(
        org_id, start_date, end_date
    )
    expense_by_category = analytics_service.get_expense_by_category(
        org_id, start_date, end_date
    )
    
    # Calculate totals
    total_income = sum(c.total_amount for c in income_by_category) or Decimal('0.00')
    total_expense = sum(c.total_amount for c in expense_by_category) or Decimal('0.00')
    net_balance = total_income - total_expense
    
    # Render HTML
    context = {
        'title': 'Monthly Financial Report',
        'org_name': org_name,
        'org_address': org_address,
        'period': f'{MONTH_NAMES[month]} {year}',
        'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        'month_name': MONTH_NAMES[month],
        'year': year,
        'transactions': transactions,
        'income_by_category': income_by_category,
        'expense_by_category': expense_by_category,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'transaction_count': transactions.count(),
    }
    
    html_content = render_to_string('ledger/reports/monthly_report.html', context)
    
    # Generate PDF
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file.read()


def generate_yearly_report(
    org_id: UUID,
    org_name: str,
    year: int,
    org_address: str = "",
) -> bytes:
    """
    Generate a yearly financial report PDF.
    
    Args:
        org_id: Organization UUID
        org_name: Organization display name
        year: Report year
        org_address: Optional organization address
        
    Returns:
        PDF file as bytes
    """
    HTML = _get_weasyprint()
    
    # Calculate date range
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    # Get monthly trends
    monthly_trends = analytics_service.get_monthly_trends(org_id, 12)
    
    # Convert to template-friendly format
    monthly_data = []
    for trend in monthly_trends:
        if trend.year == year:
            monthly_data.append({
                'month_name': MONTH_NAMES[trend.month],
                'income': trend.income,
                'expense': trend.expense,
                'net': trend.net,
            })
    
    # Pad missing months with zeros
    existing_months = {MONTH_NAMES[t.month] for t in monthly_trends if t.year == year}
    for i in range(1, 13):
        if MONTH_NAMES[i] not in existing_months:
            monthly_data.append({
                'month_name': MONTH_NAMES[i],
                'income': Decimal('0.00'),
                'expense': Decimal('0.00'),
                'net': Decimal('0.00'),
            })
    
    # Sort by month
    month_order = {name: i for i, name in enumerate(MONTH_NAMES)}
    monthly_data.sort(key=lambda x: month_order[x['month_name']])
    
    # Get category breakdowns
    income_by_category = analytics_service.get_income_by_category(
        org_id, start_date, end_date
    )
    expense_by_category = analytics_service.get_expense_by_category(
        org_id, start_date, end_date
    )
    
    # Calculate totals
    total_income = sum(c.total_amount for c in income_by_category) or Decimal('0.00')
    total_expense = sum(c.total_amount for c in expense_by_category) or Decimal('0.00')
    net_balance = total_income - total_expense
    
    # Get best/worst months
    best_worst = analytics_service.get_best_worst_months(org_id, year)
    best_month = None
    worst_month = None
    
    if best_worst['best_income_month']:
        best_month = {
            'name': MONTH_NAMES[best_worst['best_income_month']['month']],
            'amount': best_worst['best_income_month']['amount'],
        }
    
    if best_worst['worst_expense_month']:
        worst_month = {
            'name': MONTH_NAMES[best_worst['worst_expense_month']['month']],
            'amount': best_worst['worst_expense_month']['amount'],
        }
    
    # Render HTML
    context = {
        'title': 'Annual Financial Report',
        'org_name': org_name,
        'org_address': org_address,
        'period': f'January - December {year}',
        'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        'year': year,
        'monthly_data': monthly_data,
        'income_by_category': income_by_category,
        'expense_by_category': expense_by_category,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'best_month': best_month,
        'worst_month': worst_month,
    }
    
    return pdf_file.read()


def generate_financial_document(request):
    """
    Generate the appropriate PDF based on the DocumentRequest type.
    
    Args:
        request: DocumentRequest instance
        
    Returns:
        bytes: PDF content
    """
    from apps.governance.models import DocumentType
    
    if request.document_type == DocumentType.SOA:
        return generate_soa_pdf(request)
    elif request.document_type == DocumentType.FIN_OP:
        return generate_fin_op_pdf(request)
    elif request.document_type == DocumentType.FIN_POS:
        return generate_fin_pos_pdf(request)
    elif request.document_type == DocumentType.CASH_FLOW:
        return generate_cash_flows_pdf(request)
    elif request.document_type == DocumentType.FUND_BALANCE:
        return generate_fund_balance_pdf(request)
    else:
        raise ValueError(f"Unsupported document type: {request.document_type}")


def generate_soa_pdf(request) -> bytes:
    """Generate Statement of Account for a specific unit/user."""
    HTML = _get_weasyprint()
    from .models import DuesStatement
    
    user = request.requestor
    
    transactions = Transaction.objects.filter(
        org_id=request.org_id,
        payer_name=user.get_full_name(), # Fallback matching
    ).order_by('transaction_date')
    
    # Calculate balance (Mock logic for now as detailed ledger per user requires robust Unit link)
    history = []
    balance = Decimal('0.00')
    total_charges = Decimal('0.00')
    total_payments = Decimal('0.00')
    
    for t in transactions:
        amount = t.net_amount
        if t.transaction_type == TransactionType.INCOME:
            payment = amount
            charge = None
            total_payments += amount
            balance -= amount
        else:
            payment = None
            charge = amount
            total_charges += amount
            balance += amount
            
        history.append({
            'date': t.transaction_date,
            'description': t.description or t.category,
            'reference': t.reference_number,
            'charge': charge,
            'payment': payment,
        })
    
    context = {
        'title': 'Statement of Account',
        'org_name': 'Organization Name', # Should fetch Org
        'org_address': '',
        'period': f"As of {datetime.now().strftime('%B %d, %Y')}",
        'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        'unit_name': 'N/A', # Need Unit resolution
        'owner_name': user.get_full_name(),
        'history': history,
        'total_charges': total_charges,
        'total_payments': total_payments,
        'balance_due': balance,
    }
    
    html_content = render_to_string('ledger/reports/statement_of_account.html', context)
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()


def generate_fin_op_pdf(request) -> bytes:
    """Generate Statement of Financial Operation (Income Statement)."""
    # Reuse monthly report logic for now as simplified implementation
    # Ideally should parse date_range from request
    start_date = request.date_range_start or date(date.today().year, 1, 1)
    # Just passing arguments to existing monthly report might not be enough if it needs year/month int
    # So we call generate_monthly_report logic directly logic here?
    # Given complexity, we stub with monthly report for last month
    today = date.today()
    return generate_monthly_report(request.org_id, "Organization", today.year, today.month)


def generate_fin_pos_pdf(request) -> bytes:
    """Generate Statement of Financial Position."""
    HTML = _get_weasyprint()
    from .models import DuesStatement, UnitCredit
    
    # Calculate ASSETS
    total_income = Transaction.objects.filter(
        org_id=request.org_id, 
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.POSTED
    ).aggregate(models.Sum('net_amount'))['net_amount__sum'] or Decimal('0')
    
    total_expense_disbursed = Transaction.objects.filter(
        org_id=request.org_id, 
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.POSTED,
        is_disbursed=True
    ).aggregate(models.Sum('net_amount'))['net_amount__sum'] or Decimal('0')
    
    cash_balance = total_income - total_expense_disbursed
    
    # Receivables (Approximation via DuesStatements unpaids)
    # Note: This is simplified. Real accounting requires tracking receivables ledger.
    ds_qs = DuesStatement.objects.filter(
        org_id=request.org_id,
        status__in=[DuesStatementStatus.UNPAID, DuesStatementStatus.PARTIAL, DuesStatementStatus.OVERDUE]
    )
    # Calculate sum in python to use property
    receivables = sum(ds.balance_due for ds in ds_qs)
    
    total_assets = cash_balance + receivables
    
    # Calculate LIABILITIES
    payables = Transaction.objects.filter(
        org_id=request.org_id, 
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.POSTED,
        is_disbursed=False
    ).aggregate(models.Sum('net_amount'))['net_amount__sum'] or Decimal('0')
    
    advance_dues = UnitCredit.objects.filter(org_id=request.org_id).aggregate(
        models.Sum('credit_balance')
    )['credit_balance__sum'] or Decimal('0')
    
    total_liabilities = payables + advance_dues
    
    # EQUITY
    fund_balance = total_assets - total_liabilities
    
    context = {
        'title': 'Statement of Financial Position',
        'org_name': 'Organization', 
        'period': f"As of {date.today()}",
        'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        'assets': [
            {'name': 'Cash & Cash Equivalents', 'amount': cash_balance, 'prev_amount': 0},
            {'name': 'Accounts Receivable - Dues', 'amount': receivables, 'prev_amount': 0},
        ],
        'total_assets': total_assets,
        'liabilities': [
            {'name': 'Accounts Payable', 'amount': payables, 'prev_amount': 0},
            {'name': 'Advance Dues (Unit Credits)', 'amount': advance_dues, 'prev_amount': 0},
        ],
        'total_liabilities': total_liabilities,
        'fund_balance': fund_balance,
        'total_liabilities_equity': total_liabilities + fund_balance,
        
        # Comparatives (Zero for now)
        'total_assets_prev': 0,
        'total_liabilities_prev': 0,
        'fund_balance_prev': 0,
        'total_liabilities_equity_prev': 0,
    }
    
    html_content = render_to_string('ledger/reports/financial_position.html', context)
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()


def generate_cash_flows_pdf(request) -> bytes:
    """Generate Statement of Cash Flows."""
    HTML = _get_weasyprint()
    context = {
        'title': 'Statement of Cash Flows',
        'org_name': 'Organization',
        'generated_at': timezone.now().strftime('%B %d, %Y'),
        'net_surplus': 0,
        'operating_activities': [],
        'net_cash_operating': 0,
        'investing_activities': [],
        'net_cash_investing': 0,
        'financing_activities': [],
        'net_cash_financing': 0,
        'net_increase_cash': 0,
        'cash_beginning': 0,
        'cash_ending': 0,
    }
    html_content = render_to_string('ledger/reports/cash_flows.html', context)
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()


def generate_fund_balance_pdf(request) -> bytes:
    """Generate Statement of Changes in Fund Balance."""
    HTML = _get_weasyprint()
    context = {
        'title': 'Statement of Changes in Fund Balance',
        'org_name': 'Organization',
        'generated_at': timezone.now().strftime('%B %d, %Y'),
        'fund_beginning': 0,
        'net_surplus': 0,
        'adjustments': [],
        'fund_ending': 0,
    }
    html_content = render_to_string('ledger/reports/fund_balance.html', context)
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()
