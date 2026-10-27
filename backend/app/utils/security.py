"""
AICTE FlowOps — Cryptographic Security & Token Management

Provides:
- Argon2 password hashing and verification via pwdlib
- Password complexity policy enforcement
- JWT access token generation and decoding using pyjwt
- Constant-time secret comparison and secure token claims
"""

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, Optional

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

settings = get_settings()

# Initialize Argon2 password hasher via pwdlib recommended configuration
_password_hasher = PasswordHash.recommended()


class PasswordPolicyError(ValueError):
    """Raised when a password fails compliance checks."""
    pass


def validate_password_strength(password: str) -> None:
    """
    Enforce AICTE FlowOps statutory password complexity rules:
    - Minimum 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special symbol (!@#$%^&*()_+-=[]{}|;:,.<>?)
    """
    if len(password) < 8:
        raise PasswordPolicyError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise PasswordPolicyError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise PasswordPolicyError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise PasswordPolicyError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        raise PasswordPolicyError("Password must contain at least one special character.")


def hash_password(plain_password: str) -> str:
    """Hash password using Argon2id."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """
    Verify password against stored Argon2id hash.
    Safely returns False if hashed_password is None.
    """
    if not hashed_password:
        return False
    return _password_hasher.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generate a signed JWT access token containing subject identity, role,
    issued-at (iat), and expiration (exp) timestamps in UTC.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises jwt.PyJWTError subclasses (ExpiredSignatureError, InvalidTokenError, etc.).
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub"]},
    )
