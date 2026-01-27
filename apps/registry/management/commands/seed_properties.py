from django.core.management.base import BaseCommand
from apps.identity.models import User, UserRole
from apps.registry.models import Unit, MembershipStatus, OccupancyStatus
import random

class Command(BaseCommand):
    help = 'Seeds the database with test properties linked to existing users'

    def handle(self, *args, **options):
        # 1. Get Organization Context from Admin
        try:
            admin = User.objects.get(username='admin')
            if not admin.org_id:
                self.stdout.write(self.style.ERROR('Admin user exists but has no Org ID. Re-run seed_users?'))
                return
            org_id = admin.org_id
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin user not found. Please run "python manage.py seed_users" first.'))
            return

        # 2. Get Homeowner for linking
        homeowner = User.objects.filter(username='homeowner').first()

        # 3. Generate Properties
        blocks = ['1', '2', '3', '4', '5']
        lots_per_block = 10
        street_names = ['Narra St.', 'Molave St.', 'Yakal St.', 'Acacia Ave.']

        units_created = 0
        
        self.stdout.write('Generating properties...')

        for block in blocks:
            location = random.choice(street_names)
            
            for lot in range(1, lots_per_block + 1):
                lot_str = str(lot)
                
                # Check exist
                if Unit.objects.filter(
                    org_id=org_id, 
                    section_identifier=block, 
                    unit_identifier=lot_str
                ).exists():
                    continue

                # Randomize status
                membership = random.choice(MembershipStatus.choices)[0]
                occupancy = random.choices(
                    OccupancyStatus.choices, 
                    weights=[80, 15, 5], 
                    k=1
                )[0][0]

                # Link homeowner to specifically Block 1 Lot 1 for easy testing
                owner_id = None
                owner_name = None
                
                if block == '1' and lot_str == '1' and homeowner:
                    owner_id = homeowner.id
                    owner_name = f"{homeowner.first_name} {homeowner.last_name}"
                    membership = MembershipStatus.GOOD_STANDING
                    occupancy = OccupancyStatus.INHABITED
                elif random.random() < 0.3: # 30% have random owners
                    owner_name = f"Owner B{block}-L{lot}"
                
                Unit.objects.create(
                    org_id=org_id,
                    section_identifier=block,
                    unit_identifier=lot_str,
                    location_name=location,
                    owner_id=owner_id,
                    owner_name=owner_name,
                    membership_status=membership,
                    occupancy_status=occupancy,
                )
                units_created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {units_created} units for Org {org_id}'))
