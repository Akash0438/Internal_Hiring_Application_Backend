"""
email_service.py — Send emails via Gmail SMTP using an App Password.

Gmail setup (one-time):
  1. Enable 2-Step Verification on your Google account.
  2. Go to https://myaccount.google.com/apppasswords
  3. Generate an App Password (select "Mail" + "Windows Computer" or "Other").
  4. Copy the 16-character password into GMAIL_APP_PASSWORD in your .env file.

.env variables required:
  GMAIL_USER        = your-address@gmail.com
  GMAIL_APP_PASSWORD = xxxx xxxx xxxx xxxx   (spaces optional — we strip them)
  FROM_EMAIL        = your-address@gmail.com  (usually same as GMAIL_USER)
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587   # STARTTLS


def _send(to: str, subject: str, html: str) -> None:
    """Send a single HTML email via Gmail SMTP.  Silently skips if not configured."""
    if not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
        logger.warning("Gmail credentials not set — skipping email to %s", to)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL or settings.GMAIL_USER
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(
                settings.GMAIL_USER,
                settings.GMAIL_APP_PASSWORD.replace(" ", ""),
            )
            smtp.sendmail(msg["From"], [to], msg.as_string())
        logger.info("Email sent to %s — %s", to, subject)
    except Exception as exc:
        # Never crash the API because email failed
        logger.error("Failed to send email to %s: %s", to, exc)


# ── Individual email templates ─────────────────────────────────────────────────

def send_welcome_email(to: str, name: str, temp_password: str) -> None:
    _send(
        to=to,
        subject="Welcome to Interview Management Platform",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto">
          <h2 style="color:#1d4ed8">Welcome to the Interview Platform, {name}!</h2>
          <p>Your account has been created. Use the credentials below to log in:</p>
          <table style="border-collapse:collapse;width:100%;margin:16px 0">
            <tr><td style="padding:8px;background:#f1f5f9;font-weight:600">Email</td>
                <td style="padding:8px;background:#f8fafc">{to}</td></tr>
            <tr><td style="padding:8px;background:#f1f5f9;font-weight:600">Temporary Password</td>
                <td style="padding:8px;background:#f8fafc;font-family:monospace">{temp_password}</td></tr>
          </table>
          <p style="color:#dc2626"><strong>You will be asked to change your password on first login.</strong></p>
          <a href="{settings.FRONTEND_URL}/login"
             style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:#fff;border-radius:6px;text-decoration:none">
            Log In Now
          </a>
        </div>
        """,
    )


def send_password_reset_email(to: str, name: str, temp_password: str) -> None:
    _send(
        to=to,
        subject="Your Interview Platform password has been reset",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto">
          <h2>Password Reset — {name}</h2>
          <p>An administrator has reset your password. Your new temporary password is:</p>
          <p style="font-family:monospace;font-size:18px;background:#f1f5f9;padding:12px;border-radius:6px">
            {temp_password}
          </p>
          <p style="color:#dc2626"><strong>Please log in and change your password immediately.</strong></p>
          <a href="{settings.FRONTEND_URL}/login"
             style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:#fff;border-radius:6px;text-decoration:none">
            Log In
          </a>
        </div>
        """,
    )


def send_assignment_email(
    to: str,
    interviewer_name: str,
    candidate_name: str,
    assigned_by: str = "",
    position: str = "",
    employee_id: str = "",
    current_location: str = "",
) -> None:
    details_rows = ""
    if employee_id:
        details_rows += f"<tr><td style='padding:7px 10px;background:#f1f5f9;font-weight:600;white-space:nowrap'>Employee ID</td><td style='padding:7px 10px;background:#f8fafc;font-family:monospace'>{employee_id}</td></tr>"
    if position:
        details_rows += f"<tr><td style='padding:7px 10px;background:#f1f5f9;font-weight:600;white-space:nowrap'>Position</td><td style='padding:7px 10px;background:#f8fafc'>{position}</td></tr>"
    if current_location:
        details_rows += f"<tr><td style='padding:7px 10px;background:#f1f5f9;font-weight:600;white-space:nowrap'>Location</td><td style='padding:7px 10px;background:#f8fafc'>{current_location}</td></tr>"
    if assigned_by:
        details_rows += f"<tr><td style='padding:7px 10px;background:#f1f5f9;font-weight:600;white-space:nowrap'>Assigned by</td><td style='padding:7px 10px;background:#f8fafc'>{assigned_by}</td></tr>"

    _send(
        to=to,
        subject=f"New Interview Assignment: {candidate_name}",
        html=f"""
        <div style="font-family:sans-serif;max-width:540px;margin:auto;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
          <div style="background:#1d4ed8;padding:20px 24px">
            <h2 style="margin:0;color:#fff;font-size:18px">New Interview Assignment</h2>
          </div>
          <div style="padding:24px">
            <p style="margin-top:0">Hi <strong>{interviewer_name}</strong>,</p>
            <p>You have been assigned to interview the following candidate.
               Please review the details below and submit your feedback after the interview.</p>
            <table style="border-collapse:collapse;width:100%;margin:16px 0;font-size:14px">
              <tr><td style="padding:7px 10px;background:#f1f5f9;font-weight:600;white-space:nowrap">Candidate</td>
                  <td style="padding:7px 10px;background:#f8fafc"><strong>{candidate_name}</strong></td></tr>
              {details_rows}
            </table>
            <a href="{settings.FRONTEND_URL}/assignments"
               style="display:inline-block;padding:10px 22px;background:#1d4ed8;color:#fff;border-radius:6px;text-decoration:none;font-weight:600">
              View My Assignments
            </a>
            <p style="margin-top:20px;font-size:12px;color:#6b7280">
              This is an automated notification from the Interview Management Platform.
            </p>
          </div>
        </div>
        """,
    )


def send_feedback_submitted_email(to: str, portfolio_manager_name: str, candidate_name: str) -> None:
    _send(
        to=to,
        subject=f"Feedback Ready for Review: {candidate_name}",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto">
          <h2>Interview Feedback Submitted</h2>
          <p>Hi <strong>{portfolio_manager_name}</strong>,</p>
          <p>The hiring manager has submitted feedback for <strong>{candidate_name}</strong>.</p>
          <p>Please log in to review the feedback and make your hiring decision.</p>
          <a href="{settings.FRONTEND_URL}/candidates"
             style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:#fff;border-radius:6px;text-decoration:none">
            Review Candidates
          </a>
        </div>
        """,
    )


def send_decision_email(to: str, hiring_manager_name: str, candidate_name: str, decision: str) -> None:
    decision_label = decision.replace("_", " ").title()
    color = "#16a34a" if decision == "APPROVED" else "#dc2626" if decision == "REJECTED" else "#d97706"
    _send(
        to=to,
        subject=f"Hiring Decision: {candidate_name}",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto">
          <h2>Hiring Decision Made</h2>
          <p>Hi <strong>{hiring_manager_name}</strong>,</p>
          <p>A hiring decision has been made for <strong>{candidate_name}</strong>:</p>
          <p style="font-size:20px;font-weight:700;color:{color}">{decision_label}</p>
        </div>
        """,
    )
