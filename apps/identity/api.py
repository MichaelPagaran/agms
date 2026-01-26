"""
Identity API endpoints with JWT authentication.

Provides login, logout, token refresh, and user management endpoints.
Uses JWT tokens in httpOnly cookies for secure stateless authentication.
"""
from typing import List, Optional
from uuid import UUID
from ninja import Router, Schema
from django.http import HttpRequest, HttpResponse
from ninja.errors import HttpError
from django.contrib.auth import authenticate

from .models import User
from .dtos import UserDTO, UserCreate, UserUpdate
from .services import get_user_dto, create_user, list_users, update_user, soft_delete_user
from .permissions import Permissions, get_user_permissions
from .jwt_auth import (
    create_token_pair,
    decode_token,
    get_user_id_from_token,
    get_access_token_cookie_settings,
    get_refresh_token_cookie_settings,
    create_access_token,
)

router = Router(tags=["Identity"])


# =============================================================================
# Schemas
# =============================================================================

class LoginSchema(Schema):
    username: str
    password: str


class TokenResponse(Schema):
    success: bool
    user: Optional[UserDTO] = None
    message: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def get_current_user(request: HttpRequest) -> Optional[User]:
    """
    Extract and validate user from JWT access token cookie.
    
    Returns User object if valid token, None otherwise.
    """
    access_token = request.COOKIES.get('access_token')
    if not access_token:
        return None
    
    user_id = get_user_id_from_token(access_token)
    if not user_id:
        return None
    
    try:
        return User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return None


def require_auth(request: HttpRequest) -> User:
    """
    Require authentication. Raises 401 if not authenticated.
    """
    user = get_current_user(request)
    if not user:
        raise HttpError(401, "Authentication required")
    return user


def is_production() -> bool:
    """Check if running in production (Lambda or DEBUG=False)."""
    import os
    from django.conf import settings
    return bool(os.getenv('AWS_LAMBDA_FUNCTION_NAME')) or not settings.DEBUG


# =============================================================================
# Auth Endpoints
# =============================================================================

@router.post("/login", response=TokenResponse, auth=None)
def login_user(request: HttpRequest, payload: LoginSchema):
    """
    Authenticate user and set JWT tokens in httpOnly cookies.
    
    Returns user data on success, sets access_token and refresh_token cookies.
    """
    user = authenticate(request, username=payload.username, password=payload.password)
    
    if user is None:
        raise HttpError(401, "Invalid username or password")
    
    if not user.is_active:
        raise HttpError(401, "Account is disabled")
    
    # Create JWT tokens
    access_token, refresh_token = create_token_pair(user.id, user.org_id)
    
    # Create response with user data
    user_dto = get_user_dto(user.id)
    response_data = TokenResponse(success=True, user=user_dto)
    
    # Create response and set cookies
    response = HttpResponse(
        response_data.model_dump_json(),
        content_type='application/json'
    )
    
    # Set cookies
    prod = is_production()
    access_settings = get_access_token_cookie_settings(prod)
    refresh_settings = get_refresh_token_cookie_settings(prod)
    
    response.set_cookie('access_token', access_token, **access_settings)
    response.set_cookie('refresh_token', refresh_token, **refresh_settings)
    
    return response


@router.post("/logout", response=TokenResponse, auth=None)
def logout_user(request: HttpRequest):
    """
    Clear authentication cookies.
    """
    response = HttpResponse(
        TokenResponse(success=True, message="Logged out").model_dump_json(),
        content_type='application/json'
    )
    
    # Clear cookies by setting them to expire immediately
    response.delete_cookie('access_token', path='/')
    response.delete_cookie('refresh_token', path='/')
    
    return response


@router.post("/refresh", response=TokenResponse, auth=None)
def refresh_token(request: HttpRequest):
    """
    Refresh the access token using the refresh token.
    
    Returns new access token if refresh token is valid.
    """
    refresh_token_value = request.COOKIES.get('refresh_token')
    
    if not refresh_token_value:
        raise HttpError(401, "No refresh token")
    
    payload = decode_token(refresh_token_value)
    if not payload or payload.get('type') != 'refresh':
        raise HttpError(401, "Invalid refresh token")
    
    try:
        user_id = UUID(payload['sub'])
        user = User.objects.get(id=user_id, is_active=True)
    except (ValueError, User.DoesNotExist):
        raise HttpError(401, "Invalid refresh token")
    
    # Create new access token
    new_access_token = create_access_token(user.id, user.org_id)
    
    user_dto = get_user_dto(user.id)
    response = HttpResponse(
        TokenResponse(success=True, user=user_dto).model_dump_json(),
        content_type='application/json'
    )
    
    # Set new access token cookie
    prod = is_production()
    access_settings = get_access_token_cookie_settings(prod)
    response.set_cookie('access_token', new_access_token, **access_settings)
    
    return response


@router.get("/me", response=UserDTO, auth=None)
def get_me(request: HttpRequest):
    """
    Get current authenticated user's profile.
    """
    user = require_auth(request)
    user_dto = get_user_dto(user.id)
    if not user_dto:
        raise HttpError(404, "User not found")
    return user_dto


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.post("/users", response=UserDTO, auth=None)
def create_org_user(request: HttpRequest, payload: UserCreate):
    """
    Create a new user in the organization.
    
    Requires IDENTITY_MANAGE_USER permission.
    """
    user = require_auth(request)
    perms = get_user_permissions(user)
    
    if Permissions.IDENTITY_MANAGE_USER not in perms:
        raise HttpError(403, "Permission denied")

    return create_user(user.org_id, payload)


@router.get("/users", response=List[UserDTO], auth=None)
def list_org_users(request: HttpRequest):
    """
    List all users in the organization.
    
    Requires IDENTITY_VIEW_USER permission.
    """
    user = require_auth(request)
    perms = get_user_permissions(user)
    
    if Permissions.IDENTITY_VIEW_USER not in perms:
        raise HttpError(403, "Permission denied")

    return list_users(user.org_id)


@router.put("/users/{user_id}", response=UserDTO, auth=None)
def update_org_user(request: HttpRequest, user_id: UUID, payload: UserUpdate):
    """
    Update a user in the organization.
    
    Requires IDENTITY_MANAGE_USER permission.
    """
    user = require_auth(request)
    perms = get_user_permissions(user)
    
    if Permissions.IDENTITY_MANAGE_USER not in perms:
        raise HttpError(403, "Permission denied")

    # Ensure target user belongs to same org
    target_user = get_user_dto(user_id)
    if not target_user or target_user.org_id != user.org_id:
        raise HttpError(404, "User not found")

    updated = update_user(user_id, payload.dict(exclude_unset=True))
    if not updated:
        raise HttpError(404, "User not found")
        
    return updated


@router.delete("/users/{user_id}", response={204: None}, auth=None)
def delete_org_user(request: HttpRequest, user_id: UUID):
    """
    Soft delete a user from the organization.
    
    Requires IDENTITY_MANAGE_USER permission.
    """
    user = require_auth(request)
    perms = get_user_permissions(user)
    
    if Permissions.IDENTITY_MANAGE_USER not in perms:
        raise HttpError(403, "Permission denied")

    # Ensure target user belongs to same org
    target_user = get_user_dto(user_id)
    if not target_user or target_user.org_id != user.org_id:
        raise HttpError(404, "User not found")

    if not soft_delete_user(user_id):
        raise HttpError(404, "User not found")
        
    return 204
