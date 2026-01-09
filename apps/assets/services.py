"""Services for Assets app."""
from .models import Asset
from .dtos import AssetDTO


def get_asset_dto(asset_id) -> AssetDTO | None:
    try:
        asset = Asset.objects.get(id=asset_id)
        return AssetDTO(
            id=asset.id,
            org_id=asset.org_id,
            name=asset.name,
            asset_type=asset.asset_type,
            is_active=asset.is_active,
        )
    except Asset.DoesNotExist:
        return None
