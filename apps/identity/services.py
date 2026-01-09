"""Services for Identity app."""
from .models import User
from .dtos import UserDTO


def get_user_dto(user_id) -> UserDTO | None:
    try:
        user = User.objects.get(id=user_id)
        return UserDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            org_id=user.org_id,
            is_active=user.is_active,
        )
    except User.DoesNotExist:
        return None
