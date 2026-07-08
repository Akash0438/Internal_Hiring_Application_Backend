import asyncio
from datetime import datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import Role, User
from app.models.candidate import Candidate, CandidateStatus
from app.models.interview_assignment import InterviewAssignment, AssignmentStatus
from app.schemas.interview import AssignInterviewRequest, AssignmentResponse, ReassignRequest, SelfAssignRequest
from app.services.auth_service import get_current_user, require_role
from app.services.notification_service import create_notification
from app.services import email_service

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _fmt_assignment(
    a: InterviewAssignment,
    candidate_name: str = "",
    hiring_manager_name: str = "",
    candidate_employee_id: str = "",
    candidate_pay_band: str = "",
) -> AssignmentResponse:
    return AssignmentResponse(
        id=str(a.id),
        candidate_id=str(a.candidate_id),
        candidate_name=candidate_name,
        candidate_employee_id=candidate_employee_id or None,
        candidate_pay_band=candidate_pay_band or None,
        portfolio_manager_id=str(a.portfolio_manager_id),
        hiring_manager_id=str(a.hiring_manager_id),
        hiring_manager_name=hiring_manager_name,
        assigned_date=a.assigned_date.isoformat(),
        status=a.status,
        is_self_assigned=a.is_self_assigned,
    )


@router.post("/self-assign", status_code=status.HTTP_201_CREATED)
async def self_assign_interview(
    body: SelfAssignRequest,
    current_user: User = Depends(require_role(Role.MAIN_MANAGER)),
):
    """
    Portfolio Manager self-assigns as the interviewer for a candidate they own.
    They act as both the Portfolio Manager and the Hiring Manager for this interview.
    """
    candidate = await Candidate.get(PydanticObjectId(body.candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if str(candidate.created_by_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not own this candidate")

    # Block if an active assignment already exists
    existing = await InterviewAssignment.find_one(
        InterviewAssignment.candidate_id == candidate.id,
        InterviewAssignment.status != AssignmentStatus.COMPLETED,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Candidate already has an active assignment")

    assignment = InterviewAssignment(
        candidate_id=candidate.id,
        portfolio_manager_id=current_user.id,
        hiring_manager_id=current_user.id,   # same person
        assigned_date=datetime.utcnow(),
        is_self_assigned=True,
    )
    await assignment.insert()

    candidate.status = CandidateStatus.ASSIGNED
    candidate.updated_at = datetime.utcnow()
    await candidate.save()

    # Self-notification so it shows in their bell
    await create_notification(
        current_user.id,
        f"You have self-assigned the interview for {candidate.candidate_name}",
    )

    return _fmt_assignment(assignment, candidate.candidate_name, current_user.name)


@router.post("/assign", status_code=status.HTTP_201_CREATED)
async def assign_interview(
    body: AssignInterviewRequest,
    current_user: User = Depends(require_role(Role.MAIN_MANAGER)),
):
    candidate = await Candidate.get(PydanticObjectId(body.candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if str(candidate.created_by_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not own this candidate")

    hiring_manager = await User.get(PydanticObjectId(body.hiring_manager_id))
    if not hiring_manager or hiring_manager.role not in (Role.HIRING_MANAGER, Role.MAIN_MANAGER):
        raise HTTPException(status_code=404, detail="Assignee not found or not eligible")
    if not hiring_manager.is_active:
        raise HTTPException(status_code=400, detail="Selected user is not active")

    # Check no active assignment exists
    existing = await InterviewAssignment.find_one(
        InterviewAssignment.candidate_id == candidate.id,
        InterviewAssignment.status != AssignmentStatus.COMPLETED,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Candidate already has an active assignment")

    # Detect self-assignment via the dropdown (PM selected themselves)
    is_self = str(hiring_manager.id) == str(current_user.id)

    assignment = InterviewAssignment(
        candidate_id=candidate.id,
        portfolio_manager_id=current_user.id,
        hiring_manager_id=hiring_manager.id,
        assigned_date=datetime.utcnow(),
        is_self_assigned=is_self,
    )
    await assignment.insert()

    candidate.status = CandidateStatus.ASSIGNED
    candidate.updated_at = datetime.utcnow()
    await candidate.save()

    if is_self:
        # Self-assign via dropdown — notify PM themselves, skip external email
        await create_notification(
            current_user.id,
            f"You have self-assigned the interview for {candidate.candidate_name}",
        )
    else:
        await create_notification(
            hiring_manager.id,
            f"You have been assigned to interview {candidate.candidate_name} ({candidate.position})",
        )
        asyncio.create_task(
            asyncio.to_thread(
                email_service.send_assignment_email,
                hiring_manager.email,
                hiring_manager.name,
                candidate.candidate_name,
                current_user.name,
                candidate.position or "",
                candidate.employee_id or "",
                candidate.current_location or "",
            )
        )

    return _fmt_assignment(assignment, candidate.candidate_name, hiring_manager.name)


@router.get("/assigned")
async def list_assignments(current_user: User = Depends(get_current_user)):
    if current_user.role == Role.MAIN_MANAGER:
        assignments = await InterviewAssignment.find(
            InterviewAssignment.portfolio_manager_id == current_user.id
        ).to_list()
    elif current_user.role == Role.HIRING_MANAGER:
        assignments = await InterviewAssignment.find(
            InterviewAssignment.hiring_manager_id == current_user.id
        ).to_list()
    else:
        assignments = await InterviewAssignment.find_all().to_list()

    results = []
    for a in assignments:
        candidate = await Candidate.get(a.candidate_id)
        hm = await User.get(a.hiring_manager_id)
        results.append(_fmt_assignment(
            a,
            candidate.candidate_name if candidate else "",
            hm.name if hm else "",
            candidate.employee_id if candidate else "",
            candidate.pay_band_level if candidate else "",
        ))
    return results


@router.patch("/{assignment_id}/reassign")
async def reassign_interview(
    assignment_id: str,
    body: ReassignRequest,
    current_user: User = Depends(require_role(Role.MAIN_MANAGER)),
):
    assignment = await InterviewAssignment.get(PydanticObjectId(assignment_id))
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if str(assignment.portfolio_manager_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not own this assignment")

    new_hm = await User.get(PydanticObjectId(body.hiring_manager_id))
    if not new_hm or new_hm.role not in (Role.HIRING_MANAGER, Role.MAIN_MANAGER):
        raise HTTPException(status_code=404, detail="Assignee not found or not eligible")
    if not new_hm.is_active:
        raise HTTPException(status_code=400, detail="Selected user is not active")

    assignment.hiring_manager_id = new_hm.id
    assignment.status = AssignmentStatus.PENDING
    await assignment.save()

    candidate = await Candidate.get(assignment.candidate_id)
    cand_name = candidate.candidate_name if candidate else "a candidate"

    await create_notification(
        new_hm.id,
        f"You have been reassigned to interview {cand_name}",
    )

    asyncio.create_task(
        asyncio.to_thread(
            email_service.send_assignment_email,
            new_hm.email,
            new_hm.name,
            cand_name,
            current_user.name,                          # assigned_by
            candidate.position or "" if candidate else "",
            candidate.employee_id or "" if candidate else "",
            candidate.current_location or "" if candidate else "",
        )
    )

    return _fmt_assignment(assignment, cand_name, new_hm.name)
