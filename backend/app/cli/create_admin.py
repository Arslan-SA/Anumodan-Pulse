"""
AICTE FlowOps — Secure Administrator Bootstrap Utility

Creates the initial platform administrator securely without hardcoded credentials.
Prompts interactively for credentials or accepts arguments / environment variables.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.utils.security import hash_password, validate_password_strength


def create_admin_interactive():
    parser = argparse.ArgumentParser(
        description="Bootstrap the initial AICTE FlowOps system administrator."
    )
    parser.add_argument("--name", help="Full name of administrator")
    parser.add_argument("--email", help="Official email address of administrator")
    parser.add_argument("--password", help="Strong password (or leave blank to be prompted securely)")

    args = parser.parse_args()

    # 1. Resolve Name
    name = args.name or os.getenv("BOOTSTRAP_ADMIN_NAME")
    if not name:
        name = input("Administrator Full Name: ").strip()
    if not name:
        print("❌ Error: Administrator name cannot be empty.", file=sys.stderr)
        sys.exit(1)

    # 2. Resolve Email
    email = args.email or os.getenv("BOOTSTRAP_ADMIN_EMAIL")
    if not email:
        email = input("Administrator Email: ").strip()
    if not email or "@" not in email:
        print("❌ Error: A valid email address is required.", file=sys.stderr)
        sys.exit(1)
    email = email.lower().strip()

    # 3. Resolve Password
    password = args.password or os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Administrator Password: ")
        confirm_password = getpass.getpass("Confirm Administrator Password: ")
        if password != confirm_password:
            print("❌ Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    try:
        validate_password_strength(password)
    except Exception as e:
        print(f"❌ Password Policy Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Check if user already exists
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            if existing.role == UserRole.ADMIN:
                print(f"ℹ️ Administrator with email '{email}' already exists.")
                sys.exit(0)
            else:
                print(f"❌ Error: A non-admin user with email '{email}' already exists.", file=sys.stderr)
                sys.exit(1)

        admin_user = User(
            full_name=name,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

    print(f"✅ Successfully created administrator '{name}' ({email}) with ID: {admin_user.id}")


if __name__ == "__main__":
    create_admin_interactive()
