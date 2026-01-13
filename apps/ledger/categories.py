"""
Default transaction categories for the Ledger app.
These are seeded for new organizations during onboarding.
"""
from typing import List, Dict


# Default Income Categories for HOAs
INCOME_CATEGORIES: List[Dict[str, str]] = [
    {
        'name': 'Monthly Dues',
        'description': 'Regular monthly association dues from homeowners'
    },
    {
        'name': 'Special Assessment',
        'description': 'One-time assessments for specific projects or expenses'
    },
    {
        'name': 'Facility Rental',
        'description': 'Income from clubhouse, pool, or other facility rentals'
    },
    {
        'name': 'Parking Fee',
        'description': 'Fees for parking spaces or stickers'
    },
    {
        'name': 'Move-in/Move-out Fee',
        'description': 'Fees charged when residents move in or out'
    },
    {
        'name': 'Advance Payment',
        'description': 'Bulk payments for future dues (credited to unit account)'
    },
    {
        'name': 'Interest Income',
        'description': 'Interest earned from bank deposits or investments'
    },
    {
        'name': 'Penalty Income',
        'description': 'Late payment penalties collected from delinquent accounts'
    },
    {
        'name': 'Other Income',
        'description': 'Miscellaneous income not categorized elsewhere'
    },
]


# Default Expense Categories for HOAs
EXPENSE_CATEGORIES: List[Dict[str, str]] = [
    {
        'name': 'Salaries & Wages',
        'description': 'Compensation for staff, guards, and maintenance personnel'
    },
    {
        'name': 'Security Services',
        'description': 'Security agency fees and related expenses'
    },
    {
        'name': 'Utilities (Electric)',
        'description': 'Electricity for common areas, street lights, etc.'
    },
    {
        'name': 'Utilities (Water)',
        'description': 'Water for common areas, landscaping, pool, etc.'
    },
    {
        'name': 'Maintenance & Repairs',
        'description': 'General maintenance and repair of common facilities'
    },
    {
        'name': 'Office Supplies',
        'description': 'Stationery, printing materials, and office consumables'
    },
    {
        'name': 'Professional Fees',
        'description': 'Legal, accounting, and other professional services'
    },
    {
        'name': 'Insurance',
        'description': 'Property and liability insurance premiums'
    },
    {
        'name': 'Landscaping',
        'description': 'Garden maintenance, plants, and landscaping services'
    },
    {
        'name': 'Garbage Collection',
        'description': 'Waste management and disposal services'
    },
    {
        'name': 'Bank Charges',
        'description': 'Bank fees, charges, and transaction costs'
    },
    {
        'name': 'Other Expenses',
        'description': 'Miscellaneous expenses not categorized elsewhere'
    },
]


def get_all_default_categories() -> Dict[str, List[Dict[str, str]]]:
    """
    Returns all default categories organized by type.
    
    Returns:
        Dict with 'income' and 'expense' keys containing category lists
    """
    return {
        'income': INCOME_CATEGORIES,
        'expense': EXPENSE_CATEGORIES,
    }
