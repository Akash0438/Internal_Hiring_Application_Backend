from typing import Optional

from pydantic import BaseModel


class CreateCandidateRequest(BaseModel):
    employee_id: str
    candidate_name: str
    email: str
    phone: Optional[str] = None
    position: str
    experience: Optional[str] = None
    current_location: Optional[str] = None
    pay_band_level: Optional[str] = None
    resume_url: Optional[str] = None


class UpdateCandidateRequest(BaseModel):
    # employee_id is intentionally excluded — it must not be changed after creation
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    experience: Optional[str] = None
    current_location: Optional[str] = None
    pay_band_level: Optional[str] = None
    resume_url: Optional[str] = None


class CandidateResponse(BaseModel):
    id: str
    employee_id: str
    candidate_name: str
    email: str
    phone: Optional[str] = None
    position: str
    experience: Optional[str] = None
    current_location: Optional[str] = None
    pay_band_level: Optional[str] = None
    resume_url: Optional[str] = None
    status: str
    created_by_id: str
    created_at: str
    updated_at: str
