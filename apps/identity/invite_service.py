import logging
import secrets
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import UserInvite, InviteStatus, User, UserRole
from .services import create_user
from .dtos import UserCreate
from apps.registry.services import update_unit, UnitIn

logger = logging.getLogger(__name__)

class InviteService:
    @staticmethod
    def create_invite(org_id, email, role=UserRole.HOMEOWNER, unit_id=None, invited_by_id=None):
        """
        Creates a new invitation.
        """
        # Check existing active invite
        existing = UserInvite.objects.filter(
            org_id=org_id, 
            email=email, 
            status=InviteStatus.PENDING
        ).first()
        
        if existing:
            # Resend/extend logic could go here
            return existing
            
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7) # 7 day validity
        
        invite = UserInvite.objects.create(
            org_id=org_id,
            email=email,
            role=role,
            unit_id=unit_id,
            token=token,
            expires_at=expires_at,
            invited_by_id=invited_by_id,
            status=InviteStatus.PENDING
        )
        
        # TODO: Send Email Task (Celery)
        # send_invite_email.delay(invite.id)
        logger.info(f"Created invite for {email}: {token}")
        
        return invite

    @staticmethod
    @transaction.atomic
    def accept_invite(token, password, first_name, last_name, phone=None):
        """
        Accepts an invite:
        1. Validates token
        2. Creates User
        3. Links Unit (if applicable)
        4. Marks invite accepted
        """
        try:
            invite = UserInvite.objects.get(token=token)
        except UserInvite.DoesNotExist:
            raise ValidationError("Invalid invitation token.")
            
        if invite.status != InviteStatus.PENDING:
            raise ValidationError("Invitation is no longer valid.")
            
        if invite.expires_at < timezone.now():
            invite.status = InviteStatus.EXPIRED
            invite.save()
            raise ValidationError("Invitation has expired.")
            
        # Create User
        user_dto = create_user(
            org_id=invite.org_id,
            payload=UserCreate(
                username=invite.email, # Use email as username
                email=invite.email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=invite.role,
                phone=phone
            )
        )
        
        # Link Unit if applicable
        if invite.unit_id:
            logger.info(f"Linking User {user_dto.id} to Unit {invite.unit_id}")
            # We need to call registry service to link
            # Note: We need to import properly to avoid circular deps if they exist
            # Using the service function imported at top
            try:
                # We fetch the unit just to integrity check or just update it
                # The generic update_unit expects a payload
                # We'll just update owner_id
                
                # Construct payload compatible with UnitIn
                # We need to fetch current unit data to not overwrite? 
                # actually update_unit only updates fields present in payload usually?
                # Check apps.registry.services.update_unit implementation
                pass 
                
                from apps.registry.models import Unit
                unit = Unit.objects.get(id=invite.unit_id)
                unit.owner_id = user_dto.id
                unit.save()
                
            except Exception as e:
                logger.error(f"Failed to link unit: {e}")
                # We don't fail the user creation, just log error
        
        # Mark Accepted
        invite.status = InviteStatus.ACCEPTED
        invite.save()
        
        return user_dto
