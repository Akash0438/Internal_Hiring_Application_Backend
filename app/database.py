import logging

import beanie
import certifi
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings, _APP_ENV

logger = logging.getLogger(__name__)

# Detect production environment to use strict TLS vs. relaxed local TLS.
# Python 3.14 + OpenSSL 3.5 on Windows rejects MongoDB Atlas SRV connections
# when `tls=True` is set explicitly alongside tlsAllowInvalidCertificates.
# The fix: in non-prod, pass ONLY tlsAllowInvalidCertificates (which implies TLS);
# in prod, use tls=True + certifi CA bundle for strict certificate validation.
_IS_PROD = settings.ENVIRONMENT == "production"


def _make_client() -> AsyncIOMotorClient:
    """Return a Motor client with the correct TLS settings for the environment."""
    if _IS_PROD:
        # Production: strict TLS with certifi CA bundle
        return AsyncIOMotorClient(
            settings.MONGODB_URL,
            tls=True,
            tlsCAFile=certifi.where(),
        )
    # Local / RND / QA: tlsAllowInvalidCertificates implicitly enables TLS.
    # Do NOT also pass tls=True — that combination triggers the SSL handshake
    # failure on Python 3.14 + OpenSSL 3.5 on Windows.
    return AsyncIOMotorClient(
        settings.MONGODB_URL,
        tlsAllowInvalidCertificates=True,
    )


async def init_db() -> None:
    """
    Initialise Beanie with all document models.

    - Connects to MongoDB Atlas using MONGODB_URL.
    - Targets the database named by DATABASE_NAME (derived from APP_ENV).
    - Beanie auto-creates collections and indexes if they do not exist.
    """
    # Import here to avoid circular imports at module load time
    from app.models.user import User
    from app.models.candidate import Candidate
    from app.models.interview_assignment import InterviewAssignment
    from app.models.interview_feedback import InterviewFeedback
    from app.models.notification import Notification

    env_label = _APP_ENV.upper() if _APP_ENV else "DEV (local)"
    logger.info("━" * 55)
    logger.info(f"  Environment : {env_label}")
    logger.info(f"  Database    : {settings.DATABASE_NAME}")
    logger.info("━" * 55)

    client = _make_client()
    database = client[settings.DATABASE_NAME]

    await beanie.init_beanie(
        database=database,
        document_models=[
            User,
            Candidate,
            InterviewAssignment,
            InterviewFeedback,
            Notification,
        ],
    )

    logger.info("✓ Beanie initialised — collections and indexes verified.")
