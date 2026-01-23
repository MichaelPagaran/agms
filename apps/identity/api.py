from ninja import Router, Schema
from django.http import HttpRequest
from ninja.errors import HttpError
from django.contrib.auth import authenticate, login, logout
from .dtos import UserDTO, UserCreate
from .services import get_user_dto, create_user
from apps.identity.permissions import Permissions, get_user_permissions

router = Router()

class LoginSchema(Schema):
    username: str
    password: str

@router.post("/login", auth=None)
def login_user(request: HttpRequest, payload: LoginSchema):
    user = authenticate(request, username=payload.username, password=payload.password)
    if user is not None:
        login(request, user)
        return {"success": True, "user_id": user.id}
    else:
        raise HttpError(401, "Invalid credentials")

@router.post("/logout", auth=None)
def logout_user(request: HttpRequest):
    logout(request)
    return {"success": True}

@router.get("/me", response=UserDTO, auth=None) # Start with no auth enforcement here for now, assuming middleware or simple session. 
# But wait, request.user only works if some auth is present. 
# For now, I'll rely on global auth or simple check.
def get_me(request: HttpRequest):
    if not request.user.is_authenticated:
         # In a real app we'd use Ninja's Auth dependency, but for this snippet:
         raise HttpError(401, "Unauthorized")

    user_dto = get_user_dto(request.user.id)
    if not user_dto:
        raise HttpError(404, "User not found")
    return user_dto


@router.post("/users", response=UserDTO, auth=None)
def create_org_user(request: HttpRequest, payload: UserCreate):
    """
    **Admin Endpoint**: Add a new user to your Organization.
    
    This allows an Organization Admin to create Staff, Board Members, or Homeowners
    within their own organization.
    
    Requires `identity.manage_user` permission.
    """
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")

    perms = get_user_permissions(request.user)
    if Permissions.IDENTITY_MANAGE_USER not in perms:
        raise HttpError(403, "Permission denied")

    return create_user(request.user.org_id, payload)
