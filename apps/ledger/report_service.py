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
    
    html_content = render_to_string('ledger/reports/yearly_report.html', context)
    
    # Generate PDF
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file.read()
