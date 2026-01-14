"""
Analytics services for Financial Ledger.
Provides summaries, trends, and category breakdowns.
"""
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import date
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import Transaction, TransactionType, TransactionStatus, TransactionCategory
from .dtos import (
    FinancialSummaryDTO, CategoryBreakdownDTO, MonthlyTrendDTO, ProfitLossStatusDTO
)


def get_income_summary(
    org_id: UUID,
    period: str = 'MTD',  # 'MTD' or 'YTD'
) -> FinancialSummaryDTO:
    """
    Get income summary for the specified period.
    Only counts APPROVED transactions.
    """
    today = timezone.now().date()
    
    if period == 'MTD':
        start_date = date(today.year, today.month, 1)
    else:  # YTD
        start_date = date(today.year, 1, 1)
    
    queryset = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
        transaction_date__lte=today,
    )
    
    aggregated = queryset.aggregate(
        total=Sum('net_amount'),
        count=Count('id'),
    )
    
    total_income = aggregated['total'] or Decimal('0.00')
    
    return FinancialSummaryDTO(
        period=period,
        total_income=total_income,
        total_expense=Decimal('0.00'),
        net_balance=total_income,
        transaction_count=aggregated['count'],
    )


def get_expense_summary(
    org_id: UUID,
    period: str = 'MTD',
) -> FinancialSummaryDTO:
    """
    Get expense summary for the specified period.
    Only counts APPROVED transactions.
    """
    today = timezone.now().date()
    
    if period == 'MTD':
        start_date = date(today.year, today.month, 1)
    else:  # YTD
        start_date = date(today.year, 1, 1)
    
    queryset = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
        transaction_date__lte=today,
    )
    
    aggregated = queryset.aggregate(
        total=Sum('net_amount'),
        count=Count('id'),
    )
    
    total_expense = aggregated['total'] or Decimal('0.00')
    
    return FinancialSummaryDTO(
        period=period,
        total_income=Decimal('0.00'),
        total_expense=total_expense,
        net_balance=-total_expense,
        transaction_count=aggregated['count'],
    )


def get_combined_summary(
    org_id: UUID,
    period: str = 'MTD',
) -> FinancialSummaryDTO:
    """
    Get combined income and expense summary.
    """
    income = get_income_summary(org_id, period)
    expense = get_expense_summary(org_id, period)
    
    return FinancialSummaryDTO(
        period=period,
        total_income=income.total_income,
        total_expense=expense.total_expense,
        net_balance=income.total_income - expense.total_expense,
        transaction_count=income.transaction_count + expense.transaction_count,
    )


def get_expense_by_category(
    org_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[CategoryBreakdownDTO]:
    """
    Get expense breakdown by category.
    """
    today = timezone.now().date()
    
    if not start_date:
        start_date = date(today.year, today.month, 1)
    if not end_date:
        end_date = today
    
    # Aggregate by category
    queryset = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
    ).values('category_id', 'category').annotate(
        total=Sum('net_amount'),
        count=Count('id'),
    ).order_by('-total')
    
    # Calculate total for percentages
    total = sum(item['total'] or Decimal('0.00') for item in queryset)
    
    if total == 0:
        total = Decimal('1')  # Avoid division by zero
    
    return [
        CategoryBreakdownDTO(
            category_id=item['category_id'],
            category_name=item['category'] or 'Uncategorized',
            total_amount=item['total'] or Decimal('0.00'),
            transaction_count=item['count'],
            percentage=((item['total'] or Decimal('0.00')) / total * 100).quantize(Decimal('0.01')),
        )
        for item in queryset
    ]


def get_income_by_category(
    org_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[CategoryBreakdownDTO]:
    """
    Get income breakdown by category.
    """
    today = timezone.now().date()
    
    if not start_date:
        start_date = date(today.year, today.month, 1)
    if not end_date:
        end_date = today
    
    queryset = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
    ).values('category_id', 'category').annotate(
        total=Sum('net_amount'),
        count=Count('id'),
    ).order_by('-total')
    
    total = sum(item['total'] or Decimal('0.00') for item in queryset)
    
    if total == 0:
        total = Decimal('1')
    
    return [
        CategoryBreakdownDTO(
            category_id=item['category_id'],
            category_name=item['category'] or 'Uncategorized',
            total_amount=item['total'] or Decimal('0.00'),
            transaction_count=item['count'],
            percentage=((item['total'] or Decimal('0.00')) / total * 100).quantize(Decimal('0.01')),
        )
        for item in queryset
    ]


def get_monthly_trends(
    org_id: UUID,
    months: int = 12,
) -> List[MonthlyTrendDTO]:
    """
    Get monthly income/expense trends.
    """
    today = timezone.now().date()
    
    # Calculate start date (n months ago)
    start_year = today.year
    start_month = today.month - months + 1
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    
    start_date = date(start_year, start_month, 1)
    
    # Get monthly income
    income_by_month = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
    ).annotate(
        month=TruncMonth('transaction_date')
    ).values('month').annotate(
        total=Sum('net_amount')
    )
    
    # Get monthly expense
    expense_by_month = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
    ).annotate(
        month=TruncMonth('transaction_date')
    ).values('month').annotate(
        total=Sum('net_amount')
    )
    
    # Combine into dictionary
    income_dict = {item['month']: item['total'] for item in income_by_month}
    expense_dict = {item['month']: item['total'] for item in expense_by_month}
    
    # Get all months
    all_months = set(income_dict.keys()) | set(expense_dict.keys())
    
    trends = []
    for month in sorted(all_months):
        income = income_dict.get(month, Decimal('0.00'))
        expense = expense_dict.get(month, Decimal('0.00'))
        
        trends.append(MonthlyTrendDTO(
            year=month.year,
            month=month.month,
            income=income,
            expense=expense,
            net=income - expense,
        ))
    
    return trends


def get_best_worst_months(
    org_id: UUID,
    year: Optional[int] = None,
) -> dict:
    """
    Find the best and worst performing months.
    
    Returns dict with:
    - best_income_month: Month with highest income
    - worst_income_month: Month with lowest income
    - best_expense_month: Month with lowest expense (most savings)
    - worst_expense_month: Month with highest expense
    """
    if not year:
        year = timezone.now().year
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    # Get monthly totals
    income_by_month = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
    ).annotate(
        month=TruncMonth('transaction_date')
    ).values('month').annotate(
        total=Sum('net_amount')
    ).order_by('total')
    
    expense_by_month = Transaction.objects.filter(
        org_id=org_id,
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.POSTED,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
    ).annotate(
        month=TruncMonth('transaction_date')
    ).values('month').annotate(
        total=Sum('net_amount')
    ).order_by('total')
    
    income_list = list(income_by_month)
    expense_list = list(expense_by_month)
    
    result = {
        'best_income_month': None,
        'worst_income_month': None,
        'best_expense_month': None,  # Lowest expense
        'worst_expense_month': None,  # Highest expense
        'year': year,
    }
    
    if income_list:
        result['worst_income_month'] = {
            'month': income_list[0]['month'].month,
            'amount': income_list[0]['total'],
        }
        result['best_income_month'] = {
            'month': income_list[-1]['month'].month,
            'amount': income_list[-1]['total'],
        }
    
    if expense_list:
        result['best_expense_month'] = {
            'month': expense_list[0]['month'].month,
            'amount': expense_list[0]['total'],
        }
        result['worst_expense_month'] = {
            'month': expense_list[-1]['month'].month,
            'amount': expense_list[-1]['total'],
        }
    
    return result


def get_profit_loss_status(
    org_id: UUID,
    period: str = 'MTD',
) -> ProfitLossStatusDTO:
    """
    Get current profit/loss status.
    Tells if the organization is currently profitable.
    """
    summary = get_combined_summary(org_id, period)
    
    is_profitable = summary.net_balance >= 0
    
    # Calculate percentage of expenses recovered
    if summary.total_expense > 0:
        percentage_recovered = (
            summary.total_income / summary.total_expense * 100
        ).quantize(Decimal('0.01'))
    else:
        percentage_recovered = Decimal('100.00') if summary.total_income > 0 else Decimal('0.00')
    
    return ProfitLossStatusDTO(
        period=period,
        total_income=summary.total_income,
        total_expense=summary.total_expense,
        net_balance=summary.net_balance,
        is_profitable=is_profitable,
        percentage_recovered=percentage_recovered,
    )
