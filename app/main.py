import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.database import init_db
from app.api import auth, users, candidates, interviews, feedback, notifications

logger = logging.getLogger(__name__)

# ── Scheduler ──────────────────────────────────────────────────────────────────
_scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Import here to avoid circular dependency before Beanie is initialised
    from app.services.report_service import send_daily_report

    # 5:00 PM IST = 11:30 AM UTC  (IST is UTC+5:30)
    _scheduler.add_job(
        send_daily_report,
        trigger=CronTrigger(hour=11, minute=30, timezone="UTC"),
        id="daily_report",
        replace_existing=True,
        misfire_grace_time=300,   # fire even if server was briefly down
    )
    _scheduler.start()
    logger.info("Scheduler started — daily report job scheduled at 11:30 UTC (5:00 PM IST)")

    yield

    _scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


# ── CORS config ────────────────────────────────────────────────────────────────
_IS_DEV = settings.ENVIRONMENT != "production"
_frontend = settings.FRONTEND_URL.rstrip("/")

# Production: only the exact Vercel URL is allowed.
# Development: any localhost / 127.0.0.1 origin is allowed automatically.
_PROD_ORIGINS = {_frontend}

_CORS_RESPONSE_HEADERS = {
    "Access-Control-Allow-Methods":  "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "Access-Control-Allow-Headers":  "Content-Type,Authorization,Accept,X-Requested-With",
    "Access-Control-Max-Age":        "600",
    "Vary":                          "Origin",
}


def _origin_allowed(origin: str) -> bool:
    """Return True if the origin should receive CORS headers."""
    if not origin:
        return False
    if _IS_DEV:
        # Allow any localhost / 127.0.0.1 origin on any port during development
        return (
            origin.startswith("http://localhost:")
            or origin.startswith("http://127.0.0.1:")
            or origin == "http://localhost"
            or origin == "http://127.0.0.1"
            or origin in _PROD_ORIGINS        # also allow prod URL in dev if needed
        )
    return origin in _PROD_ORIGINS


# ── CORS middleware ────────────────────────────────────────────────────────────
class CORSHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        allowed = _origin_allowed(origin)

        # Preflight: answer before the router runs
        if request.method == "OPTIONS":
            logger.debug("CORS preflight: origin=%r allowed=%s", origin, allowed)
            if allowed:
                return Response(
                    status_code=204,
                    headers={
                        "Access-Control-Allow-Origin":      origin,
                        "Access-Control-Allow-Credentials": "true",
                        **_CORS_RESPONSE_HEADERS,
                    },
                )
            logger.warning("CORS preflight BLOCKED: origin=%r", origin)
            return Response(status_code=400)

        # Normal request
        response = await call_next(request)
        if allowed:
            response.headers["Access-Control-Allow-Origin"]      = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"]                             = "Origin"
        return response


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Interview Management Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSHandlerMiddleware)

# Routers
app.include_router(auth.router,          prefix="/api")
app.include_router(users.router,         prefix="/api")
app.include_router(candidates.router,    prefix="/api")
app.include_router(interviews.router,    prefix="/api")
app.include_router(feedback.router,      prefix="/api")
app.include_router(notifications.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/admin/trigger-daily-report", tags=["admin"])
async def trigger_daily_report():
    """Manually trigger the daily report (for testing). Remove or protect in production."""
    from app.services.report_service import send_daily_report
    import asyncio
    asyncio.create_task(send_daily_report())
    return {"message": "Daily report job triggered — emails will be sent shortly"}


@app.get("/debug-cors")
async def debug_cors(request: Request):
    """
    Hit this from the browser to see exactly what origin the server receives.
    Open: http://localhost:8000/debug-cors
    """
    origin = request.headers.get("origin", "(none — direct browser tab request)")
    return JSONResponse({
        "origin_received": origin,
        "origin_allowed": _origin_allowed(origin),
        "is_dev": _IS_DEV,
        "frontend_url": _frontend,
        "all_request_headers": dict(request.headers),
    })
