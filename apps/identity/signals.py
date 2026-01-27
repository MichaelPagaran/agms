from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from apps.governance.models import AuditLog

@receiver(user_logged_in)
def log_user_login(sender, user, request, **kwargs):
    """
    Log user login events to the global Audit Log.
    """
    if user and getattr(user, 'org_id', None):
        ip = request.META.get('REMOTE_ADDR') if request else 'Unknown'
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        AuditLog.objects.create(
            org_id=user.org_id,
            action="USER_LOGIN",
            target_type="User",
            target_id=user.id,
            target_label=str(user),
            performed_by=user,
            context={
                "ip": ip,
                "user_agent": user_agent,
                "method": "Signal"
            }
        )
