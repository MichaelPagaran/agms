import uuid
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationType
from apps.registry.models import Unit, UnitCategory, MembershipStatus, OccupancyStatus
from apps.assets.models import Asset, AssetType, Reservation, ReservationStatus, PaymentStatus, ReservationConfig
from apps.ledger.models import (
    TransactionCategory, Transaction, TransactionType, PaymentType, 
    TransactionStatus, BillingConfig, DuesStatement, DuesStatementStatus,
    DiscountConfig, DiscountType, PenaltyPolicy
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with sample data for testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing data before seeding',
        )
        parser.add_argument(
            '--users',
            action='store_true',
            help='Seed users and organizations only',
        )
        parser.add_argument(
            '--registry',
            action='store_true',
            help='Seed registry units only',
        )
        parser.add_argument(
            '--assets',
            action='store_true',
            help='Seed assets only',
        )
        parser.add_argument(
            '--ledger',
            action='store_true',
            help='Seed ledger categories and transactions only',
        )
        parser.add_argument(
            '--reservations',
            action='store_true',
            help='Seed reservations only',
        )

    def handle(self, *args, **options):
        # Determine which parts to seed
        seed_all = not any([
            options['users'], options['registry'], 
            options['assets'], options['ledger'], options['reservations']
        ])

        if options['clean']:
            self.stdout.write(self.style.WARNING('Cleaning database...'))
            self._clean_database()
            self.stdout.write(self.style.SUCCESS('Database cleaned.'))

        # Always need org to proceed with others, so we might need to get or create it
        # But for simplicity, we assume we create it if we are seeding users or all.
        # If we are strictly seeding assets (--assets) without users, we might fail if org doesn't exist.
        # However, for a seed script, it's acceptable to require a base state or just ensure the Org exists.
        
        org = self._get_or_create_org()

        if seed_all or options['users']:
            self._seed_users(org)
        
        if seed_all or options['registry']:
            self._seed_registry(org)

        if seed_all or options['assets']:
            self._seed_assets(org)

        if seed_all or options['ledger']:
            self._seed_ledger(org)
            
        if seed_all or options['reservations']:
            self._seed_reservation_config(org)
            self._seed_reservations(org)

        self.stdout.write(self.style.SUCCESS('Seeding completed successfully.'))

    def _clean_database(self):
        # Order matters due to foreign keys (though many are UUIDFields, some are real FKs)
        Reservation.objects.all().delete()
        Transaction.objects.all().delete()
        TransactionCategory.objects.all().delete()
        Asset.objects.all().delete()
        Unit.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()
        Organization.objects.all().delete()

    def _get_or_create_org(self):
        org, created = Organization.objects.get_or_create(
            name="Dayung Subdivision",
            defaults={
                'org_type': OrganizationType.SUBDIVISION,
                'address': '123 Dayung St, Happy Valley',
                'fiscal_year_start_month': 1
            }
        )
        if created:
             self.stdout.write(f'Created Organization: {org.name}')
        else:
             self.stdout.write(f'Using existing Organization: {org.name}')
        
        # Ensure Billing Config exists
        BillingConfig.objects.get_or_create(
            org_id=org.id,
            defaults={
                'monthly_dues_amount': Decimal('500.00'),
                'billing_day': 1,
                'grace_period_days': 15
            }
        )
        return org

    def _seed_users(self, org):
        self.stdout.write('Seeding Users...')
        
        # Admin
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="password123",
                org_id=org,
                role='ADMIN',
                first_name="Admin",
                last_name="User"
            )
            self.stdout.write(' - Created admin (password123)')

        # Staff
        if not User.objects.filter(username="staff").exists():
            User.objects.create_user(
                username="staff",
                email="staff@example.com",
                password="password123",
                org_id=org,
                role='STAFF',
                first_name="Staff",
                last_name="Member"
            )
            self.stdout.write(' - Created staff (password123)')

        # Homeowner (Juan Dela Cruz)
        if not User.objects.filter(username="homeowner").exists():
            User.objects.create_user(
                username="homeowner",
                email="user@example.com",
                password="password123",
                org_id=org,
                role='HOMEOWNER',
                first_name="Juan",
                last_name="Dela Cruz"
            )
            self.stdout.write(' - Created homeowner (password123)')

    def _seed_registry(self, org):
        self.stdout.write('Seeding Registry...')
        
        homeowner = User.objects.filter(username="homeowner").first()
        
        # Create Block 1, Lots 1-10
        for i in range(1, 11):
            unit_id = f"Lot {i}"
            section = "Block 1"
            
            defaults = {
                'location_name': 'Main Street',
                'category': UnitCategory.UNIT,
                'membership_status': MembershipStatus.GOOD_STANDING,
                'occupancy_status': OccupancyStatus.INHABITED if i % 2 == 0 else OccupancyStatus.VACANT
            }
            
            # Assign Lot 1 to our homeowner
            if i == 1 and homeowner:
                defaults['owner_id'] = homeowner.id
                defaults['owner_name'] = f"{homeowner.first_name} {homeowner.last_name}"
                defaults['owner_email'] = homeowner.email
            
            Unit.objects.get_or_create(
                org_id=org.id,
                section_identifier=section,
                unit_identifier=unit_id,
                defaults=defaults
            )
        self.stdout.write(' - Created 10 Units in Block 1')

    def _seed_assets(self, org):
        self.stdout.write('Seeding Assets...')
        
        assets = [
            {
                'name': 'Swimming Pool',
                'asset_type': AssetType.REVENUE,
                'description': 'Olympic-size swimming pool with lifeguard on duty',
                'image_url': 'https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?w=800',
                'rental_rate': Decimal('200.00'),
                'capacity': 50,
                'requires_deposit': True,
                'deposit_amount': Decimal('500.00'),
                'location': 'Near Main Gate'
            },
            {
                'name': 'Pickleball Court',
                'asset_type': AssetType.REVENUE,
                'description': 'Professional grade pickleball court with lighting',
                'image_url': 'https://images.unsplash.com/photo-1554068865-24cecd4e34b8?w=800',
                'rental_rate': Decimal('200.00'),
                'capacity': 8,
                'requires_deposit': False,
                'location': 'Sports Complex'
            },
            {
                'name': 'Basketball Court',
                'asset_type': AssetType.REVENUE,
                'description': 'Covered basketball court with bleachers',
                'image_url': 'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=800',
                'rental_rate': Decimal('200.00'),
                'capacity': 20,
                'requires_deposit': False,
                'location': 'Sports Complex'
            },
            {
                'name': 'Function Hall',
                'asset_type': AssetType.REVENUE,
                'description': 'Air-conditioned function hall for events and gatherings',
                'image_url': 'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?w=800',
                'rental_rate': Decimal('1000.00'),
                'capacity': 150,
                'requires_deposit': True,
                'deposit_amount': Decimal('2000.00'),
                'location': 'Clubhouse Building'
            },
            {
                'name': 'Tennis Court',
                'asset_type': AssetType.REVENUE,
                'description': 'Professional tennis court with night lighting',
                'image_url': 'https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=800',
                'rental_rate': Decimal('200.00'),
                'capacity': 4,
                'requires_deposit': False,
                'location': 'Sports Complex'
            },
            {
                'name': 'Volleyball Court',
                'asset_type': AssetType.REVENUE,
                'description': 'Outdoor volleyball court with sand surface',
                'image_url': 'https://images.unsplash.com/photo-1612872087720-bb876e2e67d1?w=800',
                'rental_rate': Decimal('150.00'),
                'capacity': 12,
                'requires_deposit': False,
                'location': 'Beach Area'
            },
            {
                'name': 'Main Gate',
                'asset_type': AssetType.SHARED,
                'description': 'Main entrance gate with 24/7 security',
                'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800',
                'rental_rate': None,
                'capacity': None,
                'requires_deposit': False,
                'location': 'Main Entrance'
            },
            {
                'name': 'Playground',
                'asset_type': AssetType.SHARED,
                'description': 'Children\'s playground with modern equipment',
                'image_url': 'https://images.unsplash.com/photo-1575783970733-1aaedde1db74?w=800',
                'rental_rate': None,
                'capacity': 30,
                'requires_deposit': False,
                'location': 'Central Park'
            }
        ]
        
        for asset_data in assets:
            Asset.objects.get_or_create(
                org_id=org.id,
                name=asset_data['name'],
                defaults=asset_data
            )
        self.stdout.write(f' - Created {len(assets)} assets')

    def _seed_ledger(self, org):
        self.stdout.write('Seeding Ledger...')
        
        # Categories
        dues_cat, _ = TransactionCategory.objects.get_or_create(
            org_id=org.id,
            name="Association Dues",
            transaction_type=TransactionType.INCOME,
            defaults={'is_default': True}
        )
        rental_cat, _ = TransactionCategory.objects.get_or_create(
            org_id=org.id,
            name="Facility Rental",
            transaction_type=TransactionType.INCOME
        )
        maint_cat, _ = TransactionCategory.objects.get_or_create(
            org_id=org.id,
            name="Maintenance & Repairs",
            transaction_type=TransactionType.EXPENSE
        )
        util_cat, _ = TransactionCategory.objects.get_or_create(
            org_id=org.id,
            name="Utilities",
            transaction_type=TransactionType.EXPENSE
        )
        security_cat, _ = TransactionCategory.objects.get_or_create(
            org_id=org.id,
            name="Security Services",
            transaction_type=TransactionType.EXPENSE
        )
        landscaping_cat, _ = TransactionCategory.objects.get_or_create(
            org_id=org.id,
            name="Landscaping",
            transaction_type=TransactionType.EXPENSE
        )
        
        self.stdout.write(' - Created 6 categories')

        # Units for reference
        units = list(Unit.objects.filter(org_id=org.id)[:5])
        now = timezone.now()

        transactions_data = [
            # Income - Association Dues
            {'cat': dues_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.POSTED,
             'amount': Decimal('500.00'), 'desc': 'January Dues - Block 1 Lot 1',
             'payer': 'Juan Dela Cruz', 'days_ago': 45, 'verified': True},
            {'cat': dues_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.POSTED,
             'amount': Decimal('500.00'), 'desc': 'January Dues - Block 1 Lot 2',
             'payer': 'Maria Santos', 'days_ago': 42, 'verified': True},
            {'cat': dues_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.POSTED,
             'amount': Decimal('500.00'), 'desc': 'February Dues - Block 1 Lot 1',
             'payer': 'Juan Dela Cruz', 'days_ago': 12, 'verified': True},
            {'cat': dues_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.POSTED,
             'amount': Decimal('500.00'), 'desc': 'February Dues - Block 1 Lot 3',
             'payer': 'Pedro Reyes', 'days_ago': 10, 'verified': False},
            {'cat': dues_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.PENDING,
             'amount': Decimal('500.00'), 'desc': 'February Dues - Block 1 Lot 5',
             'payer': 'Ana Garcia', 'days_ago': 3, 'verified': False},
            # Income - Facility Rental
            {'cat': rental_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.POSTED,
             'amount': Decimal('4000.00'), 'desc': 'Function Hall Rental - Birthday Party',
             'payer': 'Juan Dela Cruz', 'days_ago': 35, 'verified': True},
            {'cat': rental_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.POSTED,
             'amount': Decimal('800.00'), 'desc': 'Swimming Pool Rental (4hrs)',
             'payer': 'Lisa Mendoza', 'days_ago': 20, 'verified': True},
            {'cat': rental_cat, 'type': TransactionType.INCOME, 'status': TransactionStatus.POSTED,
             'amount': Decimal('600.00'), 'desc': 'Basketball Court Rental (3hrs)',
             'payer': 'Mark Tan', 'days_ago': 8, 'verified': False},
            # Expenses - Maintenance
            {'cat': maint_cat, 'type': TransactionType.EXPENSE, 'status': TransactionStatus.POSTED,
             'amount': Decimal('1500.00'), 'desc': 'Street Light Replacement - Main Road',
             'payer': None, 'days_ago': 40, 'verified': True},
            {'cat': maint_cat, 'type': TransactionType.EXPENSE, 'status': TransactionStatus.POSTED,
             'amount': Decimal('3200.00'), 'desc': 'Swimming Pool Pump Repair',
             'payer': None, 'days_ago': 25, 'verified': True},
            {'cat': maint_cat, 'type': TransactionType.EXPENSE, 'status': TransactionStatus.PENDING,
             'amount': Decimal('850.00'), 'desc': 'Playground Equipment Maintenance',
             'payer': None, 'days_ago': 5, 'verified': False},
            # Expenses - Utilities
            {'cat': util_cat, 'type': TransactionType.EXPENSE, 'status': TransactionStatus.POSTED,
             'amount': Decimal('8500.00'), 'desc': 'January Electricity Bill',
             'payer': None, 'days_ago': 38, 'verified': True},
            {'cat': util_cat, 'type': TransactionType.EXPENSE, 'status': TransactionStatus.POSTED,
             'amount': Decimal('2800.00'), 'desc': 'January Water Bill',
             'payer': None, 'days_ago': 36, 'verified': True},
            # Expenses - Security
            {'cat': security_cat, 'type': TransactionType.EXPENSE, 'status': TransactionStatus.POSTED,
             'amount': Decimal('15000.00'), 'desc': 'Security Guard Services - January',
             'payer': None, 'days_ago': 30, 'verified': True},
            # Expenses - Landscaping
            {'cat': landscaping_cat, 'type': TransactionType.EXPENSE, 'status': TransactionStatus.POSTED,
             'amount': Decimal('5000.00'), 'desc': 'Monthly Garden Maintenance',
             'payer': None, 'days_ago': 15, 'verified': True},
        ]

        created_count = 0
        for t in transactions_data:
            if not Transaction.objects.filter(description=t['desc']).exists():
                unit = units[created_count % len(units)] if units and t['type'] == TransactionType.INCOME else None
                Transaction.objects.create(
                    org_id=org.id,
                    category_id=t['cat'].id,
                    transaction_type=t['type'],
                    status=t['status'],
                    payment_type=PaymentType.EXACT,
                    gross_amount=t['amount'],
                    net_amount=t['amount'],
                    amount=t['amount'],
                    description=t['desc'],
                    payer_name=t['payer'],
                    transaction_date=(now - timedelta(days=t['days_ago'])).date(),
                    is_verified=t['verified'],
                    unit_id=unit.id if unit else None,
                )
                created_count += 1

        self.stdout.write(f' - Created {created_count} transactions')

        # Seed Discounts
        discount_data = [
            {'name': 'Early Payment Discount', 'description': 'Discount for paying before the due date',
             'discount_type': DiscountType.PERCENTAGE, 'value': Decimal('5.00'), 'min_months': 1},
            {'name': 'Annual Advance Payment', 'description': '10% off for 12-month advance payment',
             'discount_type': DiscountType.PERCENTAGE, 'value': Decimal('10.00'), 'min_months': 12},
            {'name': 'Senior Citizen Discount', 'description': 'Flat discount for senior citizen homeowners',
             'discount_type': DiscountType.FLAT_AMOUNT, 'value': Decimal('50.00'), 'min_months': 1},
        ]
        disc_count = 0
        for d in discount_data:
            _, created = DiscountConfig.objects.get_or_create(
                org_id=org.id, name=d['name'],
                defaults={
                    'description': d['description'],
                    'discount_type': d['discount_type'],
                    'value': d['value'],
                    'min_months': d['min_months'],
                    'is_active': True,
                }
            )
            if created:
                disc_count += 1
        self.stdout.write(f' - Created {disc_count} discounts')

        # Seed Penalties
        penalty_data = [
            {'name': 'Late Payment Penalty', 'description': '2% monthly interest on overdue balance',
             'rate_type': 'PERCENT', 'rate_value': Decimal('2.00'), 'grace_period_days': 15},
            {'name': 'Reconnection Fee', 'description': 'Flat fee for service reconnection',
             'rate_type': 'FLAT', 'rate_value': Decimal('200.00'), 'grace_period_days': 30},
        ]
        pen_count = 0
        for p in penalty_data:
            _, created = PenaltyPolicy.objects.get_or_create(
                org_id=org.id, name=p['name'],
                defaults={
                    'description': p['description'],
                    'rate_type': p['rate_type'],
                    'rate_value': p['rate_value'],
                    'grace_period_days': p['grace_period_days'],
                    'is_active': True,
                }
            )
            if created:
                pen_count += 1
        self.stdout.write(f' - Created {pen_count} penalties')

        # Seed Dues Statements
        if units:
            dues_count = 0
            for i, unit in enumerate(units[:3]):
                for month in [1, 2]:
                    due_date = now.replace(month=month, day=15).date()
                    if month == 1:
                        # Paid
                        _, created = DuesStatement.objects.get_or_create(
                            org_id=org.id, unit_id=unit.id, statement_year=now.year, statement_month=month,
                            defaults={
                                'base_amount': Decimal('500.00'),
                                'penalty_amount': Decimal('0.00'),
                                'discount_amount': Decimal('25.00'),
                                'net_amount': Decimal('475.00'),
                                'amount_paid': Decimal('475.00'),
                                'status': DuesStatementStatus.PAID,
                                'due_date': due_date,
                                'paid_date': due_date - timedelta(days=3),
                            }
                        )
                    else:
                        # February - mix of statuses
                        statuses = [DuesStatementStatus.UNPAID, DuesStatementStatus.PARTIAL, DuesStatementStatus.OVERDUE]
                        st = statuses[i % len(statuses)]
                        paid = Decimal('250.00') if st == DuesStatementStatus.PARTIAL else Decimal('0.00')
                        penalty = Decimal('10.00') if st == DuesStatementStatus.OVERDUE else Decimal('0.00')
                        net = Decimal('500.00') + penalty
                        _, created = DuesStatement.objects.get_or_create(
                            org_id=org.id, unit_id=unit.id, statement_year=now.year, statement_month=month,
                            defaults={
                                'base_amount': Decimal('500.00'),
                                'penalty_amount': penalty,
                                'discount_amount': Decimal('0.00'),
                                'net_amount': net,
                                'amount_paid': paid,
                                'status': st,
                                'due_date': due_date,
                            }
                        )
                    if created:
                        dues_count += 1
            self.stdout.write(f' - Created {dues_count} dues statements')

    def _seed_reservations(self, org):
        self.stdout.write('Seeding Reservations...')
        
        assets = {
            'Function Hall': Asset.objects.filter(name="Function Hall", org_id=org.id).first(),
            'Swimming Pool': Asset.objects.filter(name="Swimming Pool", org_id=org.id).first(),
            'Basketball Court': Asset.objects.filter(name="Basketball Court", org_id=org.id).first(),
            'Pickleball Court': Asset.objects.filter(name="Pickleball Court", org_id=org.id).first(),
        }
        homeowner = User.objects.filter(username="homeowner").first()
        staff = User.objects.filter(username="staff").first()
        now = timezone.now()

        if not all(assets.values()) or not homeowner:
            self.stdout.write(self.style.WARNING(' - Skipped: missing assets or homeowner'))
            return

        reservations_data = [
            # 1. Completed - Function Hall (past)
            {'asset': 'Function Hall', 'user': homeowner, 'name': 'Juan Dela Cruz',
             'purpose': 'Birthday Party', 'hours': 4, 'days_offset': -10,
             'status': ReservationStatus.COMPLETED, 'pay_status': PaymentStatus.PAID, 'paid_full': True},
            # 2. Completed - Swimming Pool (past)
            {'asset': 'Swimming Pool', 'user': homeowner, 'name': 'Juan Dela Cruz',
             'purpose': 'Family Swimming', 'hours': 3, 'days_offset': -7,
             'status': ReservationStatus.COMPLETED, 'pay_status': PaymentStatus.PAID, 'paid_full': True},
            # 3. Confirmed - Basketball Court (future)
            {'asset': 'Basketball Court', 'user': homeowner, 'name': 'Juan Dela Cruz',
             'purpose': 'Basketball Game', 'hours': 2, 'days_offset': 3,
             'status': ReservationStatus.CONFIRMED, 'pay_status': PaymentStatus.PAID, 'paid_full': True},
            # 4. Confirmed - Function Hall (future)
            {'asset': 'Function Hall', 'user': staff, 'name': 'Maria Santos',
             'purpose': 'HOA General Assembly', 'hours': 5, 'days_offset': 7,
             'status': ReservationStatus.CONFIRMED, 'pay_status': PaymentStatus.PAID, 'paid_full': True},
            # 5. Pending Payment - Swimming Pool (future)
            {'asset': 'Swimming Pool', 'user': homeowner, 'name': 'Pedro Reyes',
             'purpose': 'Pool Party', 'hours': 4, 'days_offset': 5,
             'status': ReservationStatus.PENDING_PAYMENT, 'pay_status': PaymentStatus.UNPAID, 'paid_full': False},
            # 6. For Review - Pickleball Court (future)
            {'asset': 'Pickleball Court', 'user': homeowner, 'name': 'Lisa Mendoza',
             'purpose': 'Pickleball Tournament', 'hours': 3, 'days_offset': 10,
             'status': ReservationStatus.FOR_REVIEW, 'pay_status': PaymentStatus.UNPAID, 'paid_full': False},
            # 7. Cancelled - Function Hall (past)
            {'asset': 'Function Hall', 'user': homeowner, 'name': 'Mark Tan',
             'purpose': 'Wedding Reception', 'hours': 8, 'days_offset': -3,
             'status': ReservationStatus.CANCELLED, 'pay_status': PaymentStatus.UNPAID, 'paid_full': False},
            # 8. For Review - Basketball Court (future)
            {'asset': 'Basketball Court', 'user': staff, 'name': 'Ana Garcia',
             'purpose': 'Youth Sports Clinic', 'hours': 3, 'days_offset': 14,
             'status': ReservationStatus.FOR_REVIEW, 'pay_status': PaymentStatus.UNPAID, 'paid_full': False},
        ]

        created_count = 0
        for r in reservations_data:
            asset = assets[r['asset']]
            start = now + timedelta(days=r['days_offset'])
            # Set to 10 AM start
            start = start.replace(hour=10, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=r['hours'])
            subtotal = asset.rental_rate * r['hours']
            deposit = asset.deposit_amount or Decimal('0.00')
            total = subtotal + deposit
            paid = total if r['paid_full'] else Decimal('0.00')

            if not Reservation.objects.filter(
                reserved_by_name=r['name'], purpose=r['purpose']
            ).exists():
                Reservation.objects.create(
                    org_id=org.id,
                    asset_id=asset.id,
                    reserved_by_id=r['user'].id,
                    reserved_by_name=r['name'],
                    purpose=r['purpose'],
                    start_datetime=start,
                    end_datetime=end,
                    hourly_rate=asset.rental_rate,
                    hours=r['hours'],
                    subtotal=subtotal,
                    deposit_amount=deposit,
                    total_amount=total,
                    amount_paid=paid,
                    status=r['status'],
                    payment_status=r['pay_status'],
                )
                created_count += 1

        self.stdout.write(f' - Created {created_count} reservations')

    def _seed_reservation_config(self, org):
        self.stdout.write('Seeding Reservation Config...')
        config, created = ReservationConfig.objects.get_or_create(
            org_id=org.id,
            defaults={
                'expiration_hours': 48,
                'allow_same_day_booking': True,
                'min_advance_hours': 2,
                'operating_hours_start': '09:00',
                'operating_hours_end': '22:00',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(' - Created ReservationConfig')
        else:
            self.stdout.write(' - ReservationConfig already exists')
