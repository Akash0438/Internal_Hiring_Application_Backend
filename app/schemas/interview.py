from pydantic import BaseModel
from typing import Literal, Optional


class AssignInterviewRequest(BaseModel):
    candidate_id: str
    hiring_manager_id: str


class SelfAssignRequest(BaseModel):
    candidate_id: str


class ReassignRequest(BaseModel):
    hiring_manager_id: str


class AssignmentResponse(BaseModel):
    id: str
    candidate_id: str
    candidate_name: Optional[str] = None
    candidate_employee_id: Optional[str] = None
    candidate_pay_band: Optional[str] = None
    portfolio_manager_id: str
    hiring_manager_id: str
    hiring_manager_name: Optional[str] = None
    assigned_date: str
    status: str
    is_self_assigned: bool = False


class DecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "ON_HOLD"]
