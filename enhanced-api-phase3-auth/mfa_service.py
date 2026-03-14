"""
Multi-Factor Authentication Service
TOTP, SMS, Email MFA implementation
"""

import secrets
import pyotp
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
import logging

from models_auth import MFADevice, MFAChallenge, MFAMethod, User
from pydantic_models_auth import MFASetupRequest, MFAVerifyRequest

logger = logging.getLogger(__name__)


class MFAService:
    """Multi-Factor Authentication Service"""

    TOTP_ISSUER = "Piddy"
    TOTP_PERIOD = 30  # seconds
    BACKUP_CODE_COUNT = 10
    BACKUP_CODE_LENGTH = 8
    CHALLENGE_EXPIRY = 600  # 10 minutes
    MAX_ATTEMPTS = 3

    def __init__(self, sms_service=None, email_service=None):
        """Initialize MFA service with optional providers"""
        self.sms_service = sms_service
        self.email_service = email_service

    def setup_totp(
        self, user_id: str, device_name: str, db: Session
    ) -> Tuple[MFADevice, str, str]:
        """Setup TOTP multi-factor authentication"""
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        
        # Create unverified device
        device = MFADevice(
            user_id=user_id,
            method=MFAMethod.TOTP.value,
            name=device_name,
            secret=secret,
            is_backup=False,
        )
        db.add(device)
        db.commit()

        # Generate QR code
        totp = pyotp.TOTP(secret, issuer_name=self.TOTP_ISSUER)
        qr_uri = totp.provisioning_uri(name=f"{user_id}@piddy.com")
        qr_code = self._generate_qr_code(qr_uri)

        return device, secret, qr_code

    def setup_sms(
        self,
        user_id: str,
        phone_number: str,
        device_name: str,
        db: Session,
    ) -> MFADevice:
        """Setup SMS multi-factor authentication"""
        
        # Validate phone number (basic format check)
        phone = self._normalize_phone(phone_number)
        if not phone:
            raise ValueError("Invalid phone number format")

        # Create unverified device
        device = MFADevice(
            user_id=user_id,
            method=MFAMethod.SMS.value,
            name=device_name,
            secret=phone,  # Store phone as secret
            is_backup=False,
        )
        db.add(device)
        db.commit()

        # Send verification SMS
        if self.sms_service:
            code = self._generate_code()
            self.sms_service.send_verification_sms(
                phone,
                code,
                f"Your Piddy verification code is: {code}",
            )

        return device

    def setup_email(
        self,
        user_id: str,
        email: str,
        device_name: str,
        db: Session,
    ) -> MFADevice:
        """Setup Email multi-factor authentication"""
        
        # Create unverified device
        device = MFADevice(
            user_id=user_id,
            method=MFAMethod.EMAIL.value,
            name=device_name,
            secret=email,  # Store email as secret
            is_backup=False,
        )
        db.add(device)
        db.commit()

        # Send verification email
        if self.email_service:
            code = self._generate_code()
            self.email_service.send_mfa_verification(email, code)

        return device

    def verify_setup(
        self, device_id: str, code: str, db: Session
    ) -> Tuple[MFADevice, List[str]]:
        """Verify MFA device setup"""
        
        device = db.query(MFADevice).filter(MFADevice.id == device_id).first()
        if not device:
            raise ValueError("Device not found")

        if device.verified_at:
            raise ValueError("Device already verified")

        # Verify based on method
        if device.method == MFAMethod.TOTP.value:
            self._verify_totp(device.secret, code)
        else:
            # SMS/Email verification would check against sent code
            # For demo, we'll accept any 6-digit code
            if not code or len(code) != 6:
                raise ValueError("Invalid code format")

        # Mark as verified
        device.verified_at = datetime.utcnow()
        device.is_active = True

        # Generate backup codes
        backup_codes = self._generate_backup_codes()
        device.backup_codes = backup_codes

        db.commit()

        return device, backup_codes

    def create_challenge(
        self, user_id: str, device_id: Optional[str] = None, db: Session = None
    ) -> MFAChallenge:
        """Create MFA challenge"""
        
        # Get device
        if device_id:
            device = (
                db.query(MFADevice)
                .filter(
                    MFADevice.id == device_id,
                    MFADevice.user_id == user_id,
                    MFADevice.is_active,
                )
                .first()
            )
        else:
            # Get primary device
            device = (
                db.query(MFADevice)
                .filter(
                    MFADevice.user_id == user_id,
                    MFADevice.is_primary,
                    MFADevice.is_active,
                )
                .first()
            )

        if not device:
            raise ValueError("No MFA device found")

        # Generate challenge code
        challenge_code = self._generate_code()

        # Create challenge
        challenge = MFAChallenge(
            user_id=user_id,
            device_id=device.id,
            challenge_code=challenge_code,
            method=device.method,
            expires_at=datetime.utcnow() + timedelta(seconds=self.CHALLENGE_EXPIRY),
        )
        db.add(challenge)
        db.commit()

        # Send challenge via appropriate method
        if device.method == MFAMethod.SMS.value and self.sms_service:
            self.sms_service.send_code(device.secret, challenge_code)
        elif device.method == MFAMethod.EMAIL.value and self.email_service:
            self.email_service.send_code(device.secret, challenge_code)

        return challenge

    def verify_challenge(
        self, challenge_id: str, code: str, db: Session
    ) -> Tuple[bool, MFADevice]:
        """Verify MFA challenge response"""
        
        challenge = (
            db.query(MFAChallenge)
            .filter(MFAChallenge.id == challenge_id)
            .first()
        )

        if not challenge:
            raise ValueError("Challenge not found or expired")

        # Check expiration
        if challenge.expires_at < datetime.utcnow():
            db.delete(challenge)
            db.commit()
            raise ValueError("Challenge expired")

        # Check max attempts
        if challenge.attempts >= challenge.max_attempts:
            db.delete(challenge)
            db.commit()
            raise ValueError("Max attempts exceeded")

        challenge.attempts += 1

        # Verify code based on method
        device = db.query(MFADevice).filter(MFADevice.id == challenge.device_id).first()

        if device.method == MFAMethod.TOTP.value:
            verified = self._verify_totp(device.secret, code)
        else:
            # Check against sent code
            verified = code == challenge.challenge_code

        if not verified:
            db.commit()
            raise ValueError("Invalid verification code")

        # Mark challenge as verified
        challenge.is_verified = True
        challenge.verified_at = datetime.utcnow()
        device.last_used_at = datetime.utcnow()

        db.commit()

        return True, device

    def verify_backup_code(
        self, user_id: str, backup_code: str, db: Session
    ) -> bool:
        """Verify and consume backup code"""
        
        device = (
            db.query(MFADevice)
            .filter(
                MFADevice.user_id == user_id,
                MFADevice.is_backup,
                MFADevice.is_active,
            )
            .first()
        )

        if not device or not device.backup_codes:
            raise ValueError("No backup codes found")

        if backup_code not in device.backup_codes:
            raise ValueError("Invalid backup code")

        # Remove used code
        device.backup_codes.remove(backup_code)
        device.last_used_at = datetime.utcnow()

        db.commit()

        return True

    def list_devices(self, user_id: str, db: Session) -> List[MFADevice]:
        """List user's MFA devices"""
        return (
            db.query(MFADevice)
            .filter(MFADevice.user_id == user_id)
            .order_by(MFADevice.is_primary.desc(), MFADevice.created_at)
            .all()
        )

    def set_primary_device(
        self, user_id: str, device_id: str, db: Session
    ) -> MFADevice:
        """Set primary MFA device"""
        
        # Unset current primary
        current_primary = (
            db.query(MFADevice)
            .filter(
                MFADevice.user_id == user_id,
                MFADevice.is_primary,
            )
            .first()
        )
        if current_primary:
            current_primary.is_primary = False

        # Set new primary
        device = (
            db.query(MFADevice)
            .filter(
                MFADevice.id == device_id,
                MFADevice.user_id == user_id,
            )
            .first()
        )

        if not device:
            raise ValueError("Device not found")

        device.is_primary = True
        db.commit()

        return device

    def disable_device(self, user_id: str, device_id: str, db: Session) -> bool:
        """Disable MFA device"""
        
        device = (
            db.query(MFADevice)
            .filter(
                MFADevice.id == device_id,
                MFADevice.user_id == user_id,
            )
            .first()
        )

        if not device:
            raise ValueError("Device not found")

        device.is_active = False
        db.commit()

        return True

    def disable_all(self, user_id: str, db: Session) -> bool:
        """Disable all MFA devices"""
        
        devices = db.query(MFADevice).filter(MFADevice.user_id == user_id).all()
        for device in devices:
            device.is_active = False

        db.commit()
        return True

    # Helper methods
    @staticmethod
    def _verify_totp(secret: str, code: str) -> bool:
        """Verify TOTP code"""
        try:
            totp = pyotp.TOTP(secret)
            # Allow 1 time period grace window
            return totp.verify(code, valid_window=1)
        except Exception as e:
            logger.error(f"TOTP verification failed: {e}")
            return False

    @staticmethod
    def _generate_code(length: int = 6) -> str:
        """Generate random code"""
        return "".join([str(secrets.randbelow(10)) for _ in range(length)])

    @staticmethod
    def _generate_backup_codes(count: int = 10, length: int = 8) -> List[str]:
        """Generate backup codes"""
        return [
            secrets.token_urlsafe(length)[:length].upper()
            for _ in range(count)
        ]

    @staticmethod
    def _generate_qr_code(uri: str) -> str:
        """Generate QR code image as base64"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_base64}"

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number"""
        # Remove non-digits
        digits = "".join(filter(str.isdigit, phone))
        
        # Validate length (10-15 digits is typical)
        if len(digits) < 10 or len(digits) > 15:
            return None

        return f"+{digits}" if not phone.startswith("+") else phone
