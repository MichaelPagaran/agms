from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date
from io import BytesIO
import os

try:
    from weasyprint import HTML
except ImportError:
    HTML = None

class Command(BaseCommand):
    help = 'Generates prototype PDFs for Transparency Portal reports'

    def handle(self, *args, **options):
        if not HTML:
            self.stderr.write(self.style.ERROR("WeasyPrint not installed. Please install it to generate PDFs."))
            return

        self.stdout.write("Generating prototype PDFs...")
        
        output_dir = "apps/ledger/prototypes"
        os.makedirs(output_dir, exist_ok=True)

        # 1. Statement of Account
        self.generate_soa(output_dir)
        
        # 2. Financial Operation (Income Statement) with Comparatives
        self.generate_fin_op(output_dir)
        
        # 3. Financial Position (Balance Sheet)
        self.generate_fin_pos(output_dir)
        
        # 4. Cash Flows
        self.generate_cash_flows(output_dir)
        
        # 5. Fund Balance
        self.generate_fund_balance(output_dir)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully generated 5 PDFs in {output_dir}/"))

    def generate_soa(self, output_dir):
        context = {
            'title': 'Statement of Account',
            'org_name': 'Sunset Valley Homeowners Association',
            'org_address': '123 Main St, Sunset Valley',
            'period': 'January 1, 2024 - January 31, 2024',
            'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            'unit_name': 'Block 5 Lot 2',
            'owner_name': 'Juan Dela Cruz',
            'unit_address': 'Block 5 Lot 2, Sunset Valley',
            'history': [
                {'date': '2024-01-01', 'description': 'Monthly Dues - Jan 2024', 'reference': 'BILL-2024-001', 'charge': 1500.00, 'payment': None},
                {'date': '2024-01-05', 'description': 'Garbage Collection Fee', 'reference': 'BILL-2024-002', 'charge': 200.00, 'payment': None},
                {'date': '2024-01-15', 'description': 'Payment Received', 'reference': 'OR-10255', 'charge': None, 'payment': 1500.00},
            ],
            'total_charges': 1700.00,
            'total_payments': 1500.00,
            'balance_due': 200.00,
        }
        
        self._render_and_save('statement_of_account.html', context, f'{output_dir}/statement_of_account.pdf')

    def generate_fin_op(self, output_dir):
        context = {
            'title': 'Statement of Financial Operation',
            'org_name': 'Sunset Valley Homeowners Association',
            'org_address': '123 Main St, Sunset Valley',
            'period': 'For the Year Ended December 31, 2024',
            'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            'revenues': [
                {'name': 'Association Dues', 'amount': 1500000.00, 'prev_amount': 1400000.00},
                {'name': 'Facility Rentals', 'amount': 150000.00, 'prev_amount': 120000.00},
                {'name': 'Penalty / Interest Income', 'amount': 25000.00, 'prev_amount': 30000.00},
                {'name': 'Car Sticker Fees', 'amount': 50000.00, 'prev_amount': 45000.00},
            ],
            'total_revenue': 1725000.00,
            'total_revenue_prev': 1595000.00,
            'expenses': [
                {'name': 'Security Services', 'amount': 450000.00, 'prev_amount': 420000.00},
                {'name': 'Utilities (Electricity/Water)', 'amount': 250000.00, 'prev_amount': 230000.00},
                {'name': 'Maintenance & Repairs', 'amount': 120000.00, 'prev_amount': 150000.00},
                {'name': 'Administrative Salaries', 'amount': 300000.00, 'prev_amount': 280000.00},
                {'name': 'Office Supplies', 'amount': 35000.00, 'prev_amount': 30000.00},
            ],
            'total_expense': 1155000.00,
            'total_expense_prev': 1110000.00,
            'net_surplus': 570000.00,
            'net_surplus_prev': 485000.00,
        }
        
        self._render_and_save('financial_operation.html', context, f'{output_dir}/financial_operation.pdf')

    def generate_fin_pos(self, output_dir):
        context = {
            'title': 'Statement of Financial Position',
            'org_name': 'Sunset Valley Homeowners Association',
            'org_address': '123 Main St, Sunset Valley',
            'period': 'As of December 31, 2024',
            'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            'assets': [
                {'name': 'Cash & Cash Equivalents', 'amount': 535000.00, 'prev_amount': 250000.00},
                {'name': 'Accounts Receivable - Dues', 'amount': 85000.00, 'prev_amount': 70000.00},
            ],
            'total_assets': 620000.00,
            'total_assets_prev': 320000.00,
            
            'liabilities': [
                {'name': 'Accounts Payable', 'amount': 12000.00, 'prev_amount': 10000.00},
                {'name': 'Advance Dues (Unit Credits)', 'amount': 45000.00, 'prev_amount': 15000.00},
            ],
            'total_liabilities': 57000.00,
            'total_liabilities_prev': 25000.00,
            
            'fund_balance': 563000.00,
            'fund_balance_prev': 295000.00,
            'total_liabilities_equity': 620000.00,
            'total_liabilities_equity_prev': 320000.00,
        }
        
        self._render_and_save('financial_position.html', context, f'{output_dir}/financial_position.pdf')

    def generate_cash_flows(self, output_dir):
        context = {
            'title': 'Statement of Cash Flows',
            'org_name': 'Sunset Valley Homeowners Association',
            'org_address': '123 Main St, Sunset Valley',
            'period': 'For the Year Ended December 31, 2024',
            'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            
            'net_surplus': 570000.00,
            'net_surplus_prev': 485000.00,
            
            'operating_activities': [
                {'name': 'Increase in Accounts Receivable', 'amount': -15000.00, 'prev_amount': -5000.00},
                {'name': 'Increase in Accounts Payable', 'amount': 5000.00, 'prev_amount': 2000.00},
                {'name': 'Increase in Advance Dues', 'amount': 10000.00, 'prev_amount': 5000.00},
            ],
            'net_cash_operating': 570000.00 - 15000.00 + 5000.00 + 10000.00, # 570k
            'net_cash_operating_prev': 485000.00 - 5000.00 + 2000.00 + 5000.00,
            
            'investing_activities': [
                {'name': 'Purchase of Office Equipment', 'amount': -50000.00, 'prev_amount': -20000.00}
            ],
            'net_cash_investing': -50000.00,
            'net_cash_investing_prev': -20000.00,
            
            'financing_activities': [],
            'net_cash_financing': 0.00,
            'net_cash_financing_prev': 0.00,
            
            'net_increase_cash': 520000.00,
            'net_increase_cash_prev': 467000.00,
            
            'cash_beginning': 15000.00,
            'cash_beginning_prev': 10000.00,
            
            'cash_ending': 535000.00,
            'cash_ending_prev': 477000.00,
        }
        
        self._render_and_save('cash_flows.html', context, f'{output_dir}/cash_flows.pdf')

    def generate_fund_balance(self, output_dir):
        context = {
            'title': 'Statement of Changes in Fund Balance',
            'org_name': 'Sunset Valley Homeowners Association',
            'org_address': '123 Main St, Sunset Valley',
            'period': 'For the Year Ended December 31, 2024',
            'generated_at': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            
            'fund_beginning': 10000.00, # Small starting balance
            'fund_beginning_prev': 5000.00,
            
            'net_surplus': 570000.00,
            'net_surplus_prev': 485000.00,
            
            'adjustments': [
                {'name': 'Prior Year Expense Adjustment', 'amount': -17000.00, 'prev_amount': 0.00}
            ],
            'fund_ending': 563000.00,
            'fund_ending_prev': 490000.00,
        }
        
        self._render_and_save('fund_balance.html', context, f'{output_dir}/fund_balance.pdf')

    def _render_and_save(self, template_name, context, output_path):
        html_content = render_to_string(f'ledger/reports/{template_name}', context)
        html = HTML(string=html_content)
        html.write_pdf(output_path)
        self.stdout.write(f"Generated {output_path}")
