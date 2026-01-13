"""
Management command to seed default categories, discounts, and penalty policies.
"""
from django.core.management.base import BaseCommand
from uuid import UUID
from decimal import Decimal

from apps.ledger.models import (
    TransactionCategory, TransactionType, DiscountConfig, DiscountType, PenaltyPolicy
)
from apps.ledger.categories import INCOME_CATEGORIES, EXPENSE_CATEGORIES
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = 'Seeds default categories, discounts, and penalty policies for an organization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id',
            type=str,
            help='Organization UUID to seed data for. If not provided, seeds for all orgs.',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Seed for all active organizations',
        )

    def handle(self, *args, **options):
        org_id = options.get('org_id')
        seed_all = options.get('all')

        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
                self._seed_for_org(org)
            except Organization.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Organization {org_id} not found'))
                return
        elif seed_all:
            orgs = Organization.objects.filter(is_active=True)
            for org in orgs:
                self._seed_for_org(org)
            self.stdout.write(self.style.SUCCESS(f'Seeded data for {orgs.count()} organizations'))
        else:
            self.stderr.write(self.style.WARNING('Please provide --org-id or --all flag'))
            return

    def _seed_for_org(self, org):
        """Seed all default data for an organization."""
        self.stdout.write(f'Seeding data for: {org.name} ({org.id})')
        
        # Seed categories
        income_count = self._seed_categories(org.id, INCOME_CATEGORIES, TransactionType.INCOME)
        expense_count = self._seed_categories(org.id, EXPENSE_CATEGORIES, TransactionType.EXPENSE)
        
        # Seed default discounts
        discount_count = self._seed_discounts(org.id)
        
        # Seed default penalty policies
        penalty_count = self._seed_penalty_policies(org.id)
        
        self.stdout.write(self.style.SUCCESS(
            f'  Created: {income_count} income categories, '
            f'{expense_count} expense categories, '
            f'{discount_count} discounts, '
            f'{penalty_count} penalty policies'
        ))

    def _seed_categories(self, org_id: UUID, categories: list, transaction_type: str) -> int:
        """Seed categories for an organization."""
        created = 0
        for cat in categories:
            obj, was_created = TransactionCategory.objects.get_or_create(
                org_id=org_id,
                name=cat['name'],
                transaction_type=transaction_type,
                defaults={
                    'description': cat['description'],
                    'is_default': True,
                    'is_active': True,
                }
            )
            if was_created:
                created += 1
        return created

    def _seed_discounts(self, org_id: UUID) -> int:
        """Seed default discounts for an organization."""
        default_discounts = [
            {
                'name': 'Early Payment Discount (5%)',
                'description': 'Discount for paying before the due date',
                'discount_type': DiscountType.PERCENTAGE,
                'value': Decimal('5.00'),
                'min_months': 1,
            },
            {
                'name': '6-Month Advance Payment (10%)',
                'description': 'Discount for paying 6 months in advance',
                'discount_type': DiscountType.PERCENTAGE,
                'value': Decimal('10.00'),
                'min_months': 6,
            },
            {
                'name': '12-Month Advance Payment (20%)',
                'description': 'Discount for paying 12 months in advance',
                'discount_type': DiscountType.PERCENTAGE,
                'value': Decimal('20.00'),
                'min_months': 12,
            },
        ]
        
        created = 0
        for discount in default_discounts:
            obj, was_created = DiscountConfig.objects.get_or_create(
                org_id=org_id,
                name=discount['name'],
                defaults={
                    'description': discount['description'],
                    'discount_type': discount['discount_type'],
                    'value': discount['value'],
                    'min_months': discount['min_months'],
                    'is_active': True,
                }
            )
            if was_created:
                created += 1
        return created

    def _seed_penalty_policies(self, org_id: UUID) -> int:
        """Seed default penalty policies for an organization."""
        default_policies = [
            {
                'name': 'Late Payment Penalty (2% Monthly)',
                'description': 'Simple interest penalty of 2% per month for overdue payments',
                'rate_type': 'PERCENT',
                'rate_value': Decimal('2.00'),
                'grace_period_days': 15,
            },
        ]
        
        created = 0
        for policy in default_policies:
            obj, was_created = PenaltyPolicy.objects.get_or_create(
                org_id=org_id,
                name=policy['name'],
                defaults={
                    'description': policy['description'],
                    'rate_type': policy['rate_type'],
                    'rate_value': policy['rate_value'],
                    'grace_period_days': policy['grace_period_days'],
                    'is_active': True,
                }
            )
            if was_created:
                created += 1
        return created
