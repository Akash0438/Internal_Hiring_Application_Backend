"""
migrate_portfolio_manager.py
─────────────────────────────
One-time migration script.  Run ONCE after deploying the code changes.

What it does:
  1. Updates every User whose role == "MAIN_MANAGER"  →  "PORTFOLIO_MANAGER"
  2. Renames the field  can_create_main_managers  →  can_create_portfolio_managers
     on every user document that still has the old field name.
  3. Renames the field  main_manager_id  →  portfolio_manager_id
     on every InterviewAssignment document.

Usage:
    cd backend
    .venv\\Scripts\\activate          # Windows
    source .venv/bin/activate        # macOS/Linux

    # Against production Atlas:
    APP_ENV=prod python migrate_portfolio_manager.py

    # Against local/rnd:
    APP_ENV=rnd python migrate_portfolio_manager.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

_app_env = os.getenv("APP_ENV", "").strip().lower()
_env_file = f".env.{_app_env}" if _app_env else ".env"
_env_path = os.path.join(os.path.dirname(__file__), _env_file)

from dotenv import load_dotenv
load_dotenv(_env_path, override=True)
print(f"  Loading env : {_env_file}")

from app.database import init_db
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


async def migrate():
    await init_db()

    # Get raw Motor client for bulk update operations
    client = AsyncIOMotorClient(settings.MONGODB_URL, tlsAllowInvalidCertificates=True)
    db = client[settings.DATABASE_NAME]

    # ── 1. Update role value MAIN_MANAGER → PORTFOLIO_MANAGER ─────────────────
    users_col = db["users"]
    result = await users_col.update_many(
        {"role": "MAIN_MANAGER"},
        {"$set": {"role": "PORTFOLIO_MANAGER"}},
    )
    print(f"[users] role updated: {result.modified_count} document(s)")

    # ── 2. Rename field can_create_main_managers → can_create_portfolio_managers
    result2 = await users_col.update_many(
        {"can_create_main_managers": {"$exists": True}},
        {"$rename": {"can_create_main_managers": "can_create_portfolio_managers"}},
    )
    print(f"[users] field renamed (can_create_main_managers -> can_create_portfolio_managers): {result2.modified_count} document(s)")

    # ── 3. Rename field main_manager_id -> portfolio_manager_id ───────────────
    assignments_col = db["interview_assignments"]
    result3 = await assignments_col.update_many(
        {"main_manager_id": {"$exists": True}},
        {"$rename": {"main_manager_id": "portfolio_manager_id"}},
    )
    print(f"[interview_assignments] field renamed (main_manager_id -> portfolio_manager_id): {result3.modified_count} document(s)")

    print()
    print("Migration complete.")
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
