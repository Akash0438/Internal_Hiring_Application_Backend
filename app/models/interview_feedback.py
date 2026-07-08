from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel, ASCENDING


class Recommendation(str, Enum):
    STRONGLY_RECOMMEND = "STRONGLY_RECOMMEND"
    RECOMMEND = "RECOMMEND"
    NEUTRAL = "NEUTRAL"
    DO_NOT_RECOMMEND = "DO_NOT_RECOMMEND"


class InterviewFeedback(Document):
    assignment_id: PydanticObjectId
    rating: int  # 1-5
    feedback: str = ""          # single free-text feedback field
    recommendation: Recommendation
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "interview_feedback"
        indexes = [
            IndexModel([("assignment_id", ASCENDING)], unique=True),
        ]
