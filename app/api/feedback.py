import asyncio
from datetime import datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import Role, User
from app.models.candidate import Candidate, CandidateStatus
from app.models.interview_assignment import InterviewAssignment, AssignmentStatus
from app.models.interview_feedback import InterviewFeedback
from app.schemas.feedback import CreateFeedbackRequest, FeedbackResponse
from app.services.auth_service import get_current_user, require_role
from app.services.notification_service import create_notification
from app.services import email_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: CreateFeedbackRequest,
    current_user: User = Depends(get_current_user),
):
    # Allow both Hiring Managers AND Portfolio Managers who self-assigned
    if current_user.role not in (Role.HIRING_MANAGER, Role.MAIN_MANAGER):
        raise HTTPException(status_code=403, detail="You do not have permission to submit feedback")

    assignment = await InterviewAssignment.get(PydanticObjectId(body.assignment_id))
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if str(assignment.hiring_manager_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="This assignment is not yours")

    existing = await InterviewFeedback.find_one(
        InterviewFeedback.assignment_id == assignment.id
    )
    if existing:
        raise HTTPException(status_code=400, detail="Feedback already submitted for this assignment")

    feedback = InterviewFeedback(
        assignment_id=assignment.id,
        rating=body.rating,
        feedback=body.feedback,
        recommendation=body.recommendation,
        submitted_at=datetime.utcnow(),
    )
    await feedback.insert()

    assignment.status = AssignmentStatus.COMPLETED
    await assignment.save()

    candidate = await Candidate.get(assignment.candidate_id)
    if candidate:
        candidate.status = CandidateStatus.FEEDBACK_SUBMITTED
        candidate.updated_at = datetime.utcnow()
        await candidate.save()

        portfolio_manager = await User.get(assignment.portfolio_manager_id)
        # Skip notification when the PM self-assigned — they are already aware
        is_self_assigned = str(assignment.portfolio_manager_id) == str(assignment.hiring_manager_id)
        if portfolio_manager and not is_self_assigned:
            await create_notification(
                portfolio_manager.id,
                f"Feedback submitted for {candidate.candidate_name}. Please review and make a decision.",
            )
            asyncio.create_task(
                asyncio.to_thread(
                    email_service.send_feedback_submitted_email,
                    portfolio_manager.email,
                    portfolio_manager.name,
                    candidate.candidate_name,
                )
            )

    return FeedbackResponse(
        id=str(feedback.id),
        assignment_id=str(feedback.assignment_id),
        rating=feedback.rating,
        feedback=feedback.feedback,
        recommendation=feedback.recommendation,
        submitted_at=feedback.submitted_at.isoformat(),
    )


@router.get("/{assignment_id}")
async def get_feedback(assignment_id: str, current_user: User = Depends(get_current_user)):
    assignment = await InterviewAssignment.get(PydanticObjectId(assignment_id))
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Access: the HM who did the interview OR the Portfolio Manager who owns the candidate
    is_hm = str(assignment.hiring_manager_id) == str(current_user.id)
    is_mm = str(assignment.portfolio_manager_id) == str(current_user.id)
    if not (is_hm or is_mm or current_user.role == Role.ADMIN):
        raise HTTPException(status_code=403, detail="Access denied")

    feedback = await InterviewFeedback.find_one(InterviewFeedback.assignment_id == assignment.id)
    if not feedback:
        raise HTTPException(status_code=404, detail="No feedback found for this assignment")

    return FeedbackResponse(
        id=str(feedback.id),
        assignment_id=str(feedback.assignment_id),
        rating=feedback.rating,
        feedback=feedback.feedback,
        recommendation=feedback.recommendation,
        submitted_at=feedback.submitted_at.isoformat(),
    )
