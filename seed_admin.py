"""
seed_admin.py — Run this once to create the first Admin user.

Usage:
    cd backend
    .venv\\Scripts\\activate     # Windows
    source .venv/bin/activate   # macOS/Linux
    python seed_admin.py
"""
import asyncio
import sys
import os

# Add the project root to the path so app.* imports work
sys.path.insert(0, os.path.dirname(__file__))

# Load the correct .env file based on APP_ENV BEFORE importing app modules.
# This must happen before any app.* import so config.py reads the right values.
_app_env = os.getenv("APP_ENV", "").strip().lower()
_env_file = f".env.{_app_env}" if _app_env else ".env"
_env_path = os.path.join(os.path.dirname(__file__), _env_file)

from dotenv import load_dotenv
load_dotenv(_env_path, override=True)

print(f"  Loading env : {_env_file}")

from app.database import init_db
from app.models.user import User, Role
from app.utils.password import hash_password


ADMIN_NAME     = "PNCIBMAdmin"
ADMIN_EMAIL    = "Akash.V1@ibm.com"
ADMIN_PASSWORD = "Test@IBM"


async def seed():
    await init_db()

    existing = await User.find_one(User.email == ADMIN_EMAIL)
    if existing:
        print(f"[!] An admin with email '{ADMIN_EMAIL}' already exists. Skipping.")
        return

    admin = User(
        name=ADMIN_NAME,
        email=ADMIN_EMAIL,
        password=hash_password(ADMIN_PASSWORD),
        role=Role.ADMIN,
        must_change_password=True,   # Force password change on first login
        can_create_portfolio_managers=True,
        is_active=True,
    )
    await admin.insert()

    print("=" * 50)
    print("Admin user created successfully!")
    print(f"  Email    : {ADMIN_EMAIL}")
    print(f"  Password : {ADMIN_PASSWORD}")
    print()
    print("Log in and change your password immediately.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed())
