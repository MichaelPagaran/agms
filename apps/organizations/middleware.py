import logging
import uuid
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

class TenantMiddleware(MiddlewareMixin):
    """
    Sets the current organization on the request.
    Enforces strict tenant isolation.
    Authorization:
    - Normal Users: Bound to request.user.org_id
    - Super Admins: Can switch via X-Organization-ID header
    """
    
    def process_request(self, request):
        request.org_id = None
        request.org = None
        
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            return

        user = request.user
        
        # 1. Super Admin Context Switch
        if user.is_superuser:
            header_org = request.headers.get('X-Organization-ID')
            if header_org:
                try:
                    request.org_id = uuid.UUID(header_org)
                except ValueError:
                    logger.warning(f"Invalid X-Organization-ID header: {header_org}")
                    # Fallback to user's org if any, or None
                    request.org_id = user.org_id
            else:
                 # Default to user's org or None (Super Admin might not belong to one)
                 request.org_id = user.org_id
            return

        # 2. Regular User Enforced Context
        if hasattr(user, 'org_id'):
            request.org_id = user.org_id
            
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Verify that URL parameters don't contradict the user's Org ID.
        If a URL has `org_id` (e.g. /api/orgs/<uuid>/units/), it MUST match.
        """
        # Skip for superusers or unauthenticated
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            return None
        if request.user.is_superuser:
            return None
            
        url_org_id = view_kwargs.get('org_id')
        if url_org_id:
            # Check strictly against the already-resolved request.org_id
            # which came from the user (enforced in process_request)
            if not request.org_id or str(url_org_id) != str(request.org_id):
                logger.warning(f"Security Alert: User {request.user.id} tried to access Org {url_org_id}")
                raise PermissionDenied("You do not have access to this organization.")
                
        return None
