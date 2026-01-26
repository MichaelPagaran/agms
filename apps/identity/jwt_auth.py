"""
JWT Authentication utilities for AGMS.

Provides token generation, validation, and cookie management
for stateless authentication compatible with AWS Lambda.
"""
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID
from django.conf import settings


# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', settings.SECRET_KEY)
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id: UUID, org_id: UUID) -> str:
    """
    Create a short-lived access token.
    
    Contains user_id and org_id for request authorization.
    Expires in 15 minutes.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        'sub': str(user_id),
        'org_id': str(org_id),
        'exp': expire,
        'iat': datetime.now(timezone.utc),
        'type': 'access'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """
    Create a long-lived refresh token.
    
    Used to obtain new access tokens without re-authentication.
    Expires in 7 days.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'sub': str(user_id),
        'exp': expire,
        'iat': datetime.now(timezone.utc),
        'type': 'refresh'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_token_pair(user_id: UUID, org_id: UUID) -> Tuple[str, str]:
    """
    Create both access and refresh tokens.
    
    Returns:
        (access_token, refresh_token)
    """
    return (
        create_access_token(user_id, org_id),
        create_refresh_token(user_id)
    )


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Returns:
        Decoded payload if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_id_from_token(token: str) -> Optional[UUID]:
    """
    Extract user_id from a valid token.
    
    Returns:
        UUID of user if token valid, None otherwise.
    """
    payload = decode_token(token)
    if payload and 'sub' in payload:
        try:
            return UUID(payload['sub'])
        except ValueError:
            return None
    return None


def get_org_id_from_token(token: str) -> Optional[UUID]:
    """
    Extract org_id from a valid access token.
    
    Only access tokens contain org_id.
    """
    payload = decode_token(token)
    if payload and payload.get('type') == 'access' and 'org_id' in payload:
        try:
            return UUID(payload['org_id'])
        except ValueError:
            return None
    return None


# Cookie configuration
def get_cookie_settings(is_production: bool = False) -> dict:
    """
    Get cookie settings based on environment.
    
    Production: Secure, SameSite=Lax
    Development: Not secure (localhost), SameSite=Lax
    """
    return {
        'httponly': True,
        'secure': is_production,
        'samesite': 'Lax',
        'path': '/',
    }


def get_access_token_cookie_settings(is_production: bool = False) -> dict:
    """Cookie settings for access token."""
    settings = get_cookie_settings(is_production)
    settings['max_age'] = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    return settings


def get_refresh_token_cookie_settings(is_production: bool = False) -> dict:
    """Cookie settings for refresh token."""
    settings = get_cookie_settings(is_production)
    settings['max_age'] = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    return settings
