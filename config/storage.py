"""
Storage configuration for AGMS.
Supports AWS S3 for production and local storage for development.
"""
import os
from pathlib import Path

# Check if S3 should be used
USE_S3 = os.getenv('USE_S3_STORAGE', 'false').lower() == 'true'


def get_storage_settings(base_dir: Path) -> dict:
    """
    Returns storage-related settings based on environment configuration.
    
    Args:
        base_dir: The BASE_DIR from Django settings
        
    Returns:
        Dictionary of storage settings to be merged into Django settings
    """
    if USE_S3:
        # Production: Use AWS S3
        return {
            'DEFAULT_FILE_STORAGE': 'storages.backends.s3boto3.S3Boto3Storage',
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'AWS_STORAGE_BUCKET_NAME': os.getenv('AWS_STORAGE_BUCKET_NAME', 'agms-receipts'),
            'AWS_S3_REGION_NAME': os.getenv('AWS_S3_REGION_NAME', 'ap-southeast-1'),
            'AWS_S3_FILE_OVERWRITE': False,
            'AWS_DEFAULT_ACL': 'private',
            'AWS_S3_CUSTOM_DOMAIN': os.getenv('AWS_S3_CUSTOM_DOMAIN') or None,
            'AWS_QUERYSTRING_AUTH': True,  # Use signed URLs for private files
            'AWS_S3_OBJECT_PARAMETERS': {
                'CacheControl': 'max-age=86400',  # 1 day cache
            },
        }
    else:
        # Development: Use local file storage
        return {
            'DEFAULT_FILE_STORAGE': 'django.core.files.storage.FileSystemStorage',
            'MEDIA_URL': '/media/',
            'MEDIA_ROOT': base_dir / 'media',
        }


# Convenience flag for services to check storage type
def is_s3_enabled() -> bool:
    """Check if S3 storage is enabled."""
    return USE_S3
