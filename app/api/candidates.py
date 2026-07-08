import csv
import io
from datetime import datetime
from typing import List

import openpyxl
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.models.user import Role, User
from app.models.candidate import Candidate, CandidateStatus
from app.models.interview_assignment import InterviewAssignment
from app.models.interview_feedback import InterviewFeedback
from app.schemas.candidate import CandidateResponse, CreateCandidateRequest, UpdateCandidateRequest
from app.schemas.interview import DecisionRequest
from app.services.auth_service import get_current_user, require_role

router = APIRouter(prefix="/candidates", tags=["candidates"])

# Required CSV/Excel columns (case-insensitive, spaces stripped)
_REQUIRED_COLS = {"employee_id", "candidate_name", "email", "position"}
_ALL_COLS = [
    "employee_id", "candidate_name", "email", "phone", "position",
    "experience", "current_location", "pay_band_level", "resume_url",
]


def _fmt(c: Candidate) -> CandidateResponse:
    return CandidateResponse(
        id=str(c.id),
        employee_id=c.employee_id,
        candidate_name=c.candidate_name,
        email=c.email,
        phone=c.phone,
        position=c.position,
        experience=c.experience,
        current_location=c.current_location,
        pay_band_level=c.pay_band_level,
        resume_url=c.resume_url,
        status=c.status,
        created_by_id=str(c.created_by_id),
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


@router.get("/")
async def list_candidates(current_user: User = Depends(get_current_user)):
    if current_user.role == Role.MAIN_MANAGER:  # Role.MAIN_MANAGER value is "PORTFOLIO_MANAGER"
        candidates = await Candidate.find(
            Candidate.created_by_id == current_user.id
        ).to_list()
    elif current_user.role == Role.HIRING_MANAGER:
        assignments = await InterviewAssignment.find(
            InterviewAssignment.hiring_manager_id == current_user.id
        ).to_list()
        candidate_ids = [a.candidate_id for a in assignments]
        candidates = await Candidate.find({"_id": {"$in": candidate_ids}}).to_list()
    else:
        candidates = await Candidate.find_all().to_list()
    return [_fmt(c) for c in candidates]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_candidate(
    body: CreateCandidateRequest,
    current_user: User = Depends(require_role(Role.MAIN_MANAGER)),
):
    # Enforce uniqueness at the app layer before hitting the DB index
    if await Candidate.find_one(Candidate.employee_id == body.employee_id.strip()):
        raise HTTPException(status_code=400, detail=f"A candidate with Employee ID '{body.employee_id}' already exists")
    if await Candidate.find_one(Candidate.email == body.email.lower().strip()):
        raise HTTPException(status_code=400, detail="A candidate with this email already exists")

    candidate = Candidate(
        employee_id=body.employee_id.strip(),
        candidate_name=body.candidate_name,
        email=body.email.lower().strip(),
        phone=body.phone,
        position=body.position,
        experience=body.experience,
        current_location=body.current_location,
        pay_band_level=body.pay_band_level,
        resume_url=body.resume_url,
        created_by_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    await candidate.insert()
    return _fmt(candidate)


@router.get("/{candidate_id}")
async def get_candidate(candidate_id: str, current_user: User = Depends(get_current_user)):
    candidate = await Candidate.get(PydanticObjectId(candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    assignments = await InterviewAssignment.find(
        InterviewAssignment.candidate_id == candidate.id
    ).to_list()
    feedback_list = []
    for a in assignments:
        fb = await InterviewFeedback.find_one(InterviewFeedback.assignment_id == a.id)
        if fb:
            feedback_list.append(fb)

    return {
        "candidate": _fmt(candidate),
        "assignments": [
            {
                "id": str(a.id),
                "status": a.status,
                "assigned_date": a.assigned_date.isoformat(),
                "hiring_manager_id": str(a.hiring_manager_id),
            }
            for a in assignments
        ],
        "feedback": [
            {
                "id": str(fb.id),
                "assignment_id": str(fb.assignment_id),
                "rating": fb.rating,
                "recommendation": fb.recommendation,
                "submitted_at": fb.submitted_at.isoformat(),
            }
            for fb in feedback_list
        ],
    }


@router.patch("/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    body: UpdateCandidateRequest,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (Role.MAIN_MANAGER, Role.HIRING_MANAGER):
        raise HTTPException(status_code=403, detail="Access denied")

    candidate = await Candidate.get(PydanticObjectId(candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if current_user.role == Role.MAIN_MANAGER:
        # PM must own the candidate
        if str(candidate.created_by_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="You do not own this candidate")
    else:
        # HM must be assigned to this candidate
        assignment = await InterviewAssignment.find_one(
            InterviewAssignment.candidate_id == candidate.id,
            InterviewAssignment.hiring_manager_id == current_user.id,
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="You are not assigned to this candidate")

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)
    candidate.updated_at = datetime.utcnow()
    await candidate.save()
    return _fmt(candidate)


@router.post("/{candidate_id}/decision")
async def hiring_decision(
    candidate_id: str,
    body: DecisionRequest,
    current_user: User = Depends(require_role(Role.MAIN_MANAGER)),
):
    candidate = await Candidate.get(PydanticObjectId(candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if str(candidate.created_by_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not own this candidate")

    # Allow decision change from any status — PM can revise at any time
    candidate.status = CandidateStatus(body.decision)
    candidate.updated_at = datetime.utcnow()
    await candidate.save()

    return _fmt(candidate)


# ── Bulk upload helpers ────────────────────────────────────────────────────────

def _normalise_header(h: str) -> str:
    """Strip whitespace and lowercase a column header."""
    return h.strip().lower().replace(" ", "_")


def _parse_csv(content: bytes) -> List[dict]:
    text = content.decode("utf-8-sig")   # handle BOM from Excel-saved CSVs
    reader = csv.DictReader(io.StringIO(text))
    headers = [_normalise_header(h) for h in (reader.fieldnames or [])]
    rows = []
    for raw in reader:
        rows.append({_normalise_header(k): (v or "").strip() for k, v in raw.items()})
    return rows, headers


def _parse_xlsx(content: bytes) -> List[dict]:
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    raw_headers = next(rows_iter, None)
    if not raw_headers:
        return [], []
    headers = [_normalise_header(str(h)) for h in raw_headers if h is not None]
    rows = []
    for raw in rows_iter:
        row = {}
        for i, val in enumerate(raw):
            if i < len(headers):
                row[headers[i]] = str(val).strip() if val is not None else ""
        rows.append(row)
    return rows, headers


@router.get("/bulk-upload/template")
async def download_template(_: User = Depends(require_role(Role.MAIN_MANAGER))):
    """Download a blank CSV template with the correct column headers."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_ALL_COLS)
    writer.writerow(["EMP001", "Jane Smith", "jane@example.com", "+1-555-0100", "Software Engineer", "3 years", "London, UK", "L4", ""])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=candidates_template.csv"},
    )


@router.post("/bulk-upload", status_code=status.HTTP_200_OK)
async def bulk_upload_candidates(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(Role.MAIN_MANAGER)),
):
    """
    Accept a CSV or XLSX file and bulk-create candidates owned by the current Portfolio Manager.

    Returns per-row results:
      { created: [...], skipped: [...], errors: [...] }

    Rows are skipped (not errored) when a candidate with the same email already exists.
    """
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are accepted")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        if ext == "csv":
            rows, headers = _parse_csv(content)
        else:
            rows, headers = _parse_xlsx(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    missing = _REQUIRED_COLS - set(headers)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. "
                   f"Required: employee_id, candidate_name, email, position",
        )

    created, skipped, errors = [], [], []

    for idx, row in enumerate(rows, start=2):   # row 2 = first data row (row 1 = header)
        employee_id = row.get("employee_id", "").strip()
        name = row.get("candidate_name", "").strip()
        email = row.get("email", "").strip()
        position = row.get("position", "").strip()

        # Validation
        if not employee_id or not name or not email or not position:
            errors.append({"row": idx, "email": email or "—", "reason": "employee_id, candidate_name, email, and position are required"})
            continue
        if "@" not in email:
            errors.append({"row": idx, "email": email, "reason": "Invalid email address"})
            continue

        # Skip duplicates on either employee_id or email
        if await Candidate.find_one(Candidate.employee_id == employee_id):
            skipped.append({"row": idx, "email": email, "reason": f"Employee ID '{employee_id}' already exists"})
            continue
        if await Candidate.find_one(Candidate.email == email.lower()):
            skipped.append({"row": idx, "email": email, "reason": "Candidate with this email already exists"})
            continue

        try:
            candidate = Candidate(
                employee_id=employee_id,
                candidate_name=name,
                email=email.lower(),
                phone=row.get("phone") or None,
                position=position,
                experience=row.get("experience") or None,
                current_location=row.get("current_location") or None,
                pay_band_level=row.get("pay_band_level") or None,
                resume_url=row.get("resume_url") or None,
                created_by_id=current_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            await candidate.insert()
            created.append({"row": idx, "email": email, "candidate_name": name})
        except Exception as exc:
            errors.append({"row": idx, "email": email, "reason": str(exc)})

    return {
        "summary": {
            "total_rows": len(rows),
            "created": len(created),
            "skipped": len(skipped),
            "errors": len(errors),
        },
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }
