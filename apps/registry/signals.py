from django.dispatch import receiver
from apps.identity.signals import user_accepted_invite
from .models import Unit
import logging

logger = logging.getLogger(__name__)

@receiver(user_accepted_invite)
def handle_user_invite_accepted(sender, user, invite, **kwargs):
    """
    Link a unit to the user when they accept an invite, if the invite specifies a unit.
    """
    if not invite.unit_id:
        return

    try:
        unit = Unit.objects.get(id=invite.unit_id)
        # Update owner to the new user
        unit.owner_id = user.id
        unit.save()
        logger.info(f"Signal: Linked User {user.id} to Unit {unit.id} via invite {invite.token}")
    except Unit.DoesNotExist:
        logger.warning(f"Signal: Unit {invite.unit_id} not found for invite {invite.token}")
    except Exception as e:
        logger.error(f"Signal: Failed to link unit for invite {invite.token}: {e}")
