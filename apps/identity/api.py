from ninja import Router, Schema
from django.http import HttpRequest
from ninja.errors import HttpError
from django.contrib.auth import authenticate, login, logout
from .dtos import UserDTO, UserCreate, UserUpdate
from .services import get_user_dto, create_user, list_users, update_user, soft_delete_user
from apps.identity.permissions import Permissions, get_user_permissions

router = Router(tags=["Identity"])

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


@router.get("/users", response=List[UserDTO], auth=None)
def list_org_users(request: HttpRequest):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")

    # Assuming strict tenancy: can only list own org's users
    # And maybe only Admin/Staff/Board? Let's check permissions.
    perms = get_user_permissions(request.user)
    if Permissions.IDENTITY_VIEW_USER not in perms:
        raise HttpError(403, "Permission denied")

    return list_users(request.user.org_id)


@router.put("/users/{user_id}", response=UserDTO, auth=None)
def update_org_user(request: HttpRequest, user_id: UUID, payload: UserUpdate):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")

    perms = get_user_permissions(request.user)
    if Permissions.IDENTITY_MANAGE_USER not in perms:
        raise HttpError(403, "Permission denied")

    # Ensure user belongs to same org (multitenant check)
    target_user = get_user_dto(user_id)
    if not target_user:
        raise HttpError(404, "User not found")
        
    if target_user.org_id != request.user.org_id:
        raise HttpError(404, "User not found") # Hide cross-tenant existence

    updated = update_user(user_id, payload.dict(exclude_unset=True))
    if not updated:
        raise HttpError(404, "User not found")
        
    return updated


@router.delete("/users/{user_id}", response={204: None}, auth=None)
def delete_org_user(request: HttpRequest, user_id: UUID):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")

    perms = get_user_permissions(request.user)
    if Permissions.IDENTITY_MANAGE_USER not in perms:
        raise HttpError(403, "Permission denied")

    # Ensure user belongs to same org
    target_user = get_user_dto(user_id)
    if not target_user:
         raise HttpError(404, "User not found")
         
    if target_user.org_id != request.user.org_id:
        raise HttpError(404, "User not found")

    if not soft_delete_user(user_id):
        raise HttpError(404, "User not found")
        
    return 204
