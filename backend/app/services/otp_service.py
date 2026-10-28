"""
AICTE FlowOps — Email OTP Service

Provides cryptographically secure 6-digit One-Time Passcode generation,
dispatch (via SMTP or dev console logging), and verification for user
registration and passwordless authentication.
"""

from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import secrets
import smtplib
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.email_otp import EmailOTP

logger = logging.getLogger("aicte_flowops.otp")
settings = get_settings()


class OTPService:
    @staticmethod
    def generate_otp_code(length: int = 6) -> str:
        """Generate a cryptographically secure numeric OTP string."""
        digits = "0123456789"
        return "".join(secrets.choice(digits) for _ in range(length))

    @staticmethod
    def dispatch_email_message(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Deliver verification email via configured SMTP server.
        Gracefully falls back to server log if SMTP is not configured.
        """
        if not settings.smtp_host:
            logger.info("SMTP host not configured. Email dispatch skipped for '%s'.", to_email)
            return False

        try:
            msg = MIMEMultipart("alternative")
            sender_email = settings.smtp_username if (settings.smtp_username and "@" in settings.smtp_username) else settings.smtp_from_email
            msg["From"] = f"AICTE FlowOps <{sender_email}>"
            msg["To"] = to_email

            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(sender_email, [to_email], msg.as_string())
            logger.info("Successfully dispatched OTP email to '%s'.", to_email)
            return True
        except Exception as exc:
            logger.error("Failed to deliver OTP email to '%s' via SMTP: %s", to_email, exc)
            return False

    @classmethod
    def send_otp(
        cls,
        db: Session,
        email: str,
        purpose: str = "register",
    ) -> Dict[str, Any]:
        """
        Generate and persist a 6-digit OTP code, invalidate previous active codes,
        and dispatch via email or secure log.
        """
        normalized_email = email.lower().strip()
        code = cls.generate_otp_code(length=6)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.otp_expiry_minutes)

        # Invalidate prior active unverified OTPs for this email & purpose
        prior_otps = db.scalars(
            select(EmailOTP).where(
                EmailOTP.email == normalized_email,
                EmailOTP.purpose == purpose,
                EmailOTP.is_verified == False,
            )
        ).all()
        for p in prior_otps:
            p.is_verified = True  # decommission old OTPs
        db.flush()

        # Create new OTP record
        record = EmailOTP(
            email=normalized_email,
            otp_code=code,
            purpose=purpose,
            attempts=0,
            is_verified=False,
            expires_at=expires_at,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        # Log OTP securely for local development / testing visibility
        logger.info(
            "🔑 [EMAIL OTP DISPATCH] To: %s | Purpose: %s | Code: %s | Expires: %s",
            normalized_email,
            purpose,
            code,
            expires_at.isoformat(),
        )

        # Prepare email templates
        subject = f"AICTE FlowOps — Your {purpose.capitalize()} Verification Code: {code}"
        text_body = (
            f"Dear User,\n\n"
            f"Your verification code for AICTE FlowOps ({purpose}) is: {code}\n\n"
            f"This code will expire in {settings.otp_expiry_minutes} minutes.\n"
            f"If you did not request this verification, please ignore this email.\n\n"
            f"@aicte-flowops.gov.in #{code}\n"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <div style="font-size: 20px; font-weight: bold; color: #1e293b; margin-bottom: 8px;">AICTE FlowOps</div>
            <div style="color: #64748b; font-size: 14px; margin-bottom: 20px;">Approval Workflow Automation &amp; Compliance Monitoring</div>
            <p style="font-size: 15px; color: #334155;">Your verification code for <strong>{purpose}</strong> is:</p>
            <div style="background-color: #f1f5f9; padding: 16px; border-radius: 6px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #0f172a; margin: 20px 0;">
                {code}
            </div>
            <p style="font-size: 13px; color: #64748b;">This code will expire in {settings.otp_expiry_minutes} minutes. Please do not share this code with anyone.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
            <p style="font-size: 11px; color: #94a3b8;">Smart India Hackathon 2026 · AICTE FlowOps</p>
        </div>
        """

        cls.dispatch_email_message(normalized_email, subject, html_body, text_body)

        response_data: Dict[str, Any] = {
            "message": f"Verification code sent to {normalized_email}.",
            "expires_in_minutes": settings.otp_expiry_minutes,
        }

        # In non-production environments or when SMTP is not configured, provide dev_otp for developer ease
        if settings.app_env != "production" or not settings.smtp_host:
            response_data["dev_otp"] = code

        return response_data

    @classmethod
    def verify_otp(
        cls,
        db: Session,
        email: str,
        otp_code: str,
        purpose: str = "register",
        consume: bool = True,
    ) -> bool:
        """
        Verify the supplied OTP against the latest active record.
        Enforces expiration checks and maximum attempt limits.
        """
        normalized_email = email.lower().strip()
        cleaned_code = otp_code.strip()

        record = db.scalar(
            select(EmailOTP)
            .where(
                EmailOTP.email == normalized_email,
                EmailOTP.purpose == purpose,
                EmailOTP.is_verified == False,
            )
            .order_by(EmailOTP.created_at.desc())
        )

        if not record:
            logger.warning("No active OTP found for '%s' (%s).", normalized_email, purpose)
            return False

        # Expiration check
        now = datetime.now(timezone.utc)
        if record.expires_at < now:
            logger.warning("OTP expired for '%s' (%s).", normalized_email, purpose)
            record.is_verified = True  # decommission expired record
            db.commit()
            return False

        # Attempt rate-limiting
        record.attempts += 1
        if record.attempts > settings.otp_max_attempts:
            logger.warning("Maximum OTP attempts exceeded for '%s' (%s).", normalized_email, purpose)
            record.is_verified = True  # lock out this OTP
            db.commit()
            return False

        # Verification check
        if secrets.compare_digest(record.otp_code, cleaned_code):
            if consume:
                record.is_verified = True
            db.commit()
            logger.info("OTP verified successfully for '%s' (%s).", normalized_email, purpose)
            return True

        db.commit()
        logger.warning("Incorrect OTP code entered for '%s' (%s). Attempt %d.", normalized_email, purpose, record.attempts)
        return False
