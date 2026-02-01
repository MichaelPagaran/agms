"""Services for Identity app."""
from .models import User
from .dtos import UserDTO, UserCreate
from .permissions import get_user_permissions


def get_user_dto(user_id) -> UserDTO | None:
    try:
        user = User.objects.get(id=user_id)
        return UserDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            org_id=user.org_id_id,
            is_active=user.is_active,
            permissions=get_user_permissions(user),
        )
    except User.DoesNotExist:
        return None


def create_user(org_id, payload: UserCreate) -> UserDTO:
    user = User.objects.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        phone=payload.phone or "",
        org_id=org_id,
        is_active=True
    )
    return get_user_dto(user.id)
    return get_user_dto(user.id)


def list_users(org_id) -> list[UserDTO]:
    users = User.objects.filter(org_id=org_id)
    return [get_user_dto(u.id) for u in users]


def update_user(user_id, data: dict) -> UserDTO | None:
    try:
        user = User.objects.get(id=user_id)
        
        for key, value in data.items():
            if value is not None:
                setattr(user, key, value)
        
        user.save()
        return get_user_dto(user_id)
    except User.DoesNotExist:
        return None


def soft_delete_user(user_id) -> bool:
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False # Soft delete usually means disabling login
        user.save()
        return True
    except User.DoesNotExist:
        return False
