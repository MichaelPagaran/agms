from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from apps.assets.models import Asset, Reservation, AssetType, ReservationStatus, PaymentStatus
from apps.assets.services import create_reservation, submit_reservation_receipt, confirm_reservation_receipt
from apps.ledger.models import Transaction, TransactionStatus, TransactionAttachment
from apps.identity.models import User, UserRole

class ReservationReceiptWorkflowTests(TestCase):
    def setUp(self):
        self.org_id = uuid4()
        
        # Create users
        self.homeowner = User.objects.create(
            username="homeowner",
            role=UserRole.HOMEOWNER,
            org_id=self.org_id
        )
        self.staff = User.objects.create(
            username="staff",
            role=UserRole.STAFF,
            org_id=self.org_id
        )
        
        # Create asset
        self.asset = Asset.objects.create(
            org_id=self.org_id,
            name="Clubhouse",
            asset_type=AssetType.REVENUE,
            rental_rate=Decimal('100.00'),
            is_active=True
        )
        
        # Create reservation
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)
        
        # Create DTO/mock object for creation
        class ReservationData:
            asset_id = self.asset.id
            unit_id = uuid4()
            start_datetime = start
            end_datetime = end
            reserved_by_name = "Test User"
            contact_phone = "123"
            contact_email = "test@example.com"
            purpose = "Party"
            apply_discount_ids = []
            
        self.reservation_dto = create_reservation(
            org_id=self.org_id,
            data=ReservationData(),
            created_by_id=self.homeowner.id,
            is_homeowner=True
        )
        self.reservation_id = self.reservation_dto.id
        
        # Mock storage to avoid S3/file issues
        # settings.USE_S3_STORAGE = False # Already default false likely

    def test_receipt_workflow(self):
        # 1. Verify initial status
        reservation = Reservation.objects.get(id=self.reservation_id)
        self.assertEqual(reservation.status, ReservationStatus.PENDING_PAYMENT)
        self.assertIsNone(reservation.income_transaction_id)
        
        # 2. Submit Receipt
        file = SimpleUploadedFile("receipt.jpg", b"file_content", content_type="image/jpeg")
        
        updated_dto = submit_reservation_receipt(
            reservation_id=self.reservation_id,
            file=file,
            uploaded_by_id=self.homeowner.id
        )
        
        # Verify status change
        self.assertEqual(updated_dto.status, ReservationStatus.FOR_REVIEW)
        
        # Verify transaction created as PENDING
        reservation.refresh_from_db()
        self.assertIsNotNone(reservation.income_transaction_id)
        txn = Transaction.objects.get(id=reservation.income_transaction_id)
        self.assertEqual(txn.status, TransactionStatus.PENDING)
        self.assertEqual(txn.amount, reservation.total_amount)
        
        # Verify attachment
        attachments = TransactionAttachment.objects.filter(transaction_id=txn.id)
        self.assertTrue(attachments.exists())
        self.assertEqual(attachments.first().uploaded_by_id, self.homeowner.id)
        
        # 3. Confirm Receipt
        confirmed_dto = confirm_reservation_receipt(
            reservation_id=self.reservation_id,
            confirmed_by_id=self.staff.id
        )
        
        # Verify confirmed status
        self.assertEqual(confirmed_dto.status, ReservationStatus.CONFIRMED)
        self.assertEqual(confirmed_dto.payment_status, PaymentStatus.PAID)
        
        # Verify transaction POSTED
        txn.refresh_from_db()
        self.assertEqual(txn.status, TransactionStatus.POSTED)
        self.assertTrue(txn.is_verified)
        self.assertEqual(txn.verified_by_id, self.staff.id)

    def test_invalid_submissions(self):
        # Can't submit for confirmed reservation
        pass # Todo if needed
