import uuid
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationType
from apps.registry.models import Unit, UnitCategory, MembershipStatus, OccupancyStatus
from apps.assets.models import Asset, AssetType, Reservation, ReservationStatus, PaymentStatus
from apps.ledger.models import (
    TransactionCategory, Transaction, TransactionType, PaymentType, 
    TransactionStatus, BillingConfig
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
                'name': 'Clubhouse',
                'asset_type': AssetType.REVENUE,
                'description': 'Main community clubhouse for events',
                'rental_rate': Decimal('1000.00'),
                'capacity': 100,
                'requires_deposit': True,
                'deposit_amount': Decimal('500.00')
            },
            {
                'name': 'Basketball Court',
                'asset_type': AssetType.REVENUE,
                'description': 'Covered basketball court',
                'rental_rate': Decimal('200.00'),
                'capacity': 20,
                'requires_deposit': False
            },
            {
                'name': 'Main Gate',
                'asset_type': AssetType.SHARED,
                'description': 'Main entrance gate',
                'rental_rate': None,
                'capacity': None,
                'requires_deposit': False
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
        
        self.stdout.write(' - Created categories')

        # Transactions
        # 1. Income: Dues Payment
        if not Transaction.objects.filter(description="January Dues").exists():
            Transaction.objects.create(
                org_id=org.id,
                category_id=dues_cat.id,
                transaction_type=TransactionType.INCOME,
                status=TransactionStatus.POSTED,
                payment_type=PaymentType.EXACT,
                gross_amount=Decimal('500.00'),
                net_amount=Decimal('500.00'),
                amount=Decimal('500.00'),
                description="January Dues",
                payer_name="Juan Dela Cruz",
                transaction_date=timezone.now().date() - timedelta(days=15),
                is_verified=True
            )

        # 2. Expense: Light Bulb Replacement
        if not Transaction.objects.filter(description="Street Light Replacement").exists():
            Transaction.objects.create(
                org_id=org.id,
                category_id=maint_cat.id,
                transaction_type=TransactionType.EXPENSE,
                status=TransactionStatus.POSTED,
                gross_amount=Decimal('1500.00'),
                net_amount=Decimal('1500.00'),
                amount=Decimal('1500.00'),
                description="Street Light Replacement",
                transaction_date=timezone.now().date() - timedelta(days=5),
                is_verified=True,
                is_disbursed=True
            )
            
        self.stdout.write(' - Created sample transactions')

    def _seed_reservations(self, org):
        self.stdout.write('Seeding Reservations...')
        
        clubhouse = Asset.objects.filter(name="Clubhouse", org_id=org.id).first()
        homeowner = User.objects.filter(username="homeowner").first()
        
        if clubhouse and homeowner:
            # 1. Past Reservation (Completed)
            start_date = timezone.now() - timedelta(days=10)
            end_date = start_date + timedelta(hours=4)
            
            if not Reservation.objects.filter(reserved_by_id=homeowner.id, status=ReservationStatus.COMPLETED).exists():
                Reservation.objects.create(
                    org_id=org.id,
                    asset_id=clubhouse.id,
                    reserved_by_id=homeowner.id,
                    reserved_by_name=f"{homeowner.first_name} {homeowner.last_name}",
                    purpose="Birthday Party",
                    start_datetime=start_date,
                    end_datetime=end_date,
                    hourly_rate=clubhouse.rental_rate,
                    hours=4,
                    subtotal=clubhouse.rental_rate * 4,
                    total_amount=clubhouse.rental_rate * 4,
                    amount_paid=clubhouse.rental_rate * 4,
                    status=ReservationStatus.COMPLETED,
                    payment_status=PaymentStatus.PAID
                )

            # 2. Future Reservation (Confirmed)
            future_start = timezone.now() + timedelta(days=5)
            future_end = future_start + timedelta(hours=3)
            
            if not Reservation.objects.filter(reserved_by_id=homeowner.id, status=ReservationStatus.CONFIRMED).exists():
                Reservation.objects.create(
                    org_id=org.id,
                    asset_id=clubhouse.id,
                    reserved_by_id=homeowner.id,
                    reserved_by_name=f"{homeowner.first_name} {homeowner.last_name}",
                    purpose="Meeting",
                    start_datetime=future_start,
                    end_datetime=future_end,
                    hourly_rate=clubhouse.rental_rate,
                    hours=3,
                    subtotal=clubhouse.rental_rate * 3,
                    total_amount=clubhouse.rental_rate * 3,
                    amount_paid=clubhouse.rental_rate * 3,
                    status=ReservationStatus.CONFIRMED,
                    payment_status=PaymentStatus.PAID
                )
            
            self.stdout.write(' - Created reservations')
