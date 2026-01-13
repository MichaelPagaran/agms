"""
Attachment service for handling receipt uploads.
Supports both AWS S3 and local storage based on configuration.
"""
import logging
import mimetypes
from typing import Optional, Tuple
from uuid import UUID
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from .models import TransactionAttachment

logger = logging.getLogger(__name__)

# Allowed file types for receipts
ALLOWED_MIME_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'application/pdf': '.pdf',
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_upload_file(file: UploadedFile) -> Tuple[bool, Optional[str]]:
    """
    Validate an uploaded file for receipt storage.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if file.size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB"
    
    # Check file type
    mime_type = file.content_type
    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"Invalid file type: {mime_type}. Allowed: JPEG, PNG, PDF"
    
    return True, None


def upload_receipt(
    file: UploadedFile,
    transaction_id: UUID,
    uploaded_by_id: Optional[UUID] = None,
) -> TransactionAttachment:
    """
    Upload a receipt file for a transaction.
    Uses S3 if configured, otherwise local storage.
    
    Args:
        file: The uploaded file
        transaction_id: ID of the transaction this receipt belongs to
        uploaded_by_id: ID of the user uploading the file
        
    Returns:
        TransactionAttachment object with the file URL
        
    Raises:
        ValueError: If file validation fails
    """
    # Validate file
    is_valid, error = validate_upload_file(file)
    if not is_valid:
        raise ValueError(error)
    
    # Determine storage path
    extension = ALLOWED_MIME_TYPES.get(file.content_type, '')
    filename = f"{transaction_id}_{file.name}"
    path = f"receipts/{transaction_id}/{filename}"
    
    # Upload based on configuration
    if getattr(settings, 'USE_S3_STORAGE', False):
        file_url = _upload_to_s3(file, path)
    else:
        file_url = _upload_to_local(file, path)
        logger.warning("S3 not configured. Using local storage for receipts.")
    
    # Create attachment record
    attachment = TransactionAttachment.objects.create(
        transaction_id=transaction_id,
        file_url=file_url,
        file_name=file.name,
        file_type=file.content_type,
        file_size=file.size,
        uploaded_by_id=uploaded_by_id,
    )
    
    return attachment


def _upload_to_s3(file: UploadedFile, path: str) -> str:
    """Upload file to AWS S3."""
    try:
        from storages.backends.s3boto3 import S3Boto3Storage
        storage = S3Boto3Storage()
        saved_path = storage.save(path, file)
        return storage.url(saved_path)
    except ImportError:
        logger.error("boto3 not installed. Install with: pip install boto3")
        raise ValueError("S3 storage configured but boto3 is not installed")
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise ValueError(f"Failed to upload to S3: {str(e)}")


def _upload_to_local(file: UploadedFile, path: str) -> str:
    """Upload file to local storage."""
    from django.core.files.storage import default_storage
    
    saved_path = default_storage.save(path, file)
    
    # Return URL-style path
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    return f"{media_url}{saved_path}"


def get_attachments_for_transaction(transaction_id: UUID) -> list:
    """Get all attachments for a transaction."""
    attachments = TransactionAttachment.objects.filter(
        transaction_id=transaction_id
    ).order_by('-created_at')
    
    return [
        {
            'id': str(att.id),
            'file_url': att.file_url,
            'file_name': att.file_name,
            'file_type': att.file_type,
            'file_size': att.file_size,
            'created_at': att.created_at.isoformat(),
        }
        for att in attachments
    ]


def delete_attachment(attachment_id: UUID) -> bool:
    """
    Delete an attachment.
    Note: This only deletes the database record, not the actual file.
    For production, you'd want to also delete from S3/local storage.
    """
    try:
        attachment = TransactionAttachment.objects.get(id=attachment_id)
        attachment.delete()
        return True
    except TransactionAttachment.DoesNotExist:
        return False
