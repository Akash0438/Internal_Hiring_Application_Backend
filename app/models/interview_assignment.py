from datetime import datetime
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import Field


class AssignmentStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class InterviewAssignment(Document):
    candidate_id: PydanticObjectId
    portfolio_manager_id: PydanticObjectId
    hiring_manager_id: PydanticObjectId
    assigned_date: datetime = Field(default_factory=datetime.utcnow)
    status: AssignmentStatus = AssignmentStatus.PENDING
    is_self_assigned: bool = False

    class Settings:
        name = "interview_assignments"
