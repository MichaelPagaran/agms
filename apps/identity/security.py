from django.core.exceptions import PermissionDenied
from ninja.errors import HttpError
from .permissions import get_user_permissions

def has_permission(permission: str):
    """
    Returns a callable dependency that checks if the user has the specific permission.
    Usage:
        @router.get("/protected", auth=..., dependencies=[Depends(has_permission("ledger.view_report"))])
        # Note: Ninja V1 dependencies work differently?
        # Standard way in Ninja:
        
        def check_perm(request):
            if not has_perm...: raise...
            
    """
    def check(request):
        if not request.user.is_authenticated:
            raise HttpError(401, "Unauthorized")
            
        perms = get_user_permissions(request.user)
        if permission not in perms:
            raise HttpError(403, f"Missing permission: {permission}")
        return True
    return check
