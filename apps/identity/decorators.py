from functools import wraps
from typing import List, Callable, Optional, Union
from ninja.errors import HttpError
from django.http import HttpRequest
from .permissions import get_user_permissions

def has_permission(required_perm: str):
    """
    Decorator to enforce a specific permission on a Django Ninja endpoint.
    
    Usage:
        @router.get("/some-path")
        @has_permission(Permissions.SOME_PERM)
        def my_view(request):
            ...
    """
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not request.user.is_authenticated:
                raise HttpError(401, "Unauthorized")
                
            perms = get_user_permissions(request.user)
            if required_perm not in perms:
                raise HttpError(403, "Permission denied")
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
