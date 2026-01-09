"""
Tenant Middleware for multi-tenancy.
Filters all queries by the logged-in user's organization.
"""
from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    """
    Sets the current organization on the request based on the logged-in user.
    """
    
    def process_request(self, request):
        # Default to None if not authenticated
        request.org = None
        request.org_id = None
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            # User model will have an org_id field
            if hasattr(request.user, 'org_id'):
                request.org_id = request.user.org_id
                request.org = getattr(request.user, 'org', None)
