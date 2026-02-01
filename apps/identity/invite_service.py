import logging
import secrets
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import UserInvite, InviteStatus, User, UserRole
from .services import create_user
from .dtos import UserCreate
from .signals import user_accepted_invite

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
        
        # Send signal for other apps (like Registry) to handle linking or setup
        try:
            user_accepted_invite.send(
                sender=InviteService,
                user=User.objects.get(id=user_dto.id),
                invite=invite
            )
        except Exception as e:
            logger.error(f"Error handling user_accepted_invite signal: {e}")

        
        # Mark Accepted
        invite.status = InviteStatus.ACCEPTED
        invite.save()
        
        return user_dto
