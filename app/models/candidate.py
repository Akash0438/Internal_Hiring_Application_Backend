from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class CandidateStatus(str, Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
    FEEDBACK_SUBMITTED = "FEEDBACK_SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ON_HOLD = "ON_HOLD"


class Candidate(Document):
    employee_id: str                        # unique business key — no two candidates share this
    candidate_name: str
    email: str
    phone: Optional[str] = None
    position: str
    experience: Optional[str] = None
    current_location: Optional[str] = None
    pay_band_level: Optional[str] = None
    resume_url: Optional[str] = None
    status: CandidateStatus = CandidateStatus.NEW
    created_by_id: PydanticObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "candidates"
        indexes = [
            # Primary unique index on employee_id — prevents duplicate candidates
            IndexModel([("employee_id", ASCENDING)], unique=True),
            # Secondary unique index on email
            IndexModel([("email", ASCENDING)], unique=True),
        ]
