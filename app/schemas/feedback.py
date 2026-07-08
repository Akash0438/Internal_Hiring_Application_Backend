from pydantic import BaseModel, field_validator

from app.models.interview_feedback import Recommendation


class CreateFeedbackRequest(BaseModel):
    assignment_id: str
    rating: int
    feedback: str
    recommendation: Recommendation

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class FeedbackResponse(BaseModel):
    id: str
    assignment_id: str
    rating: int
    feedback: str
    recommendation: str
    submitted_at: str
