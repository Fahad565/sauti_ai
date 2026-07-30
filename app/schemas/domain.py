"""Pydantic schemas for domain objects and CRUD API request/response models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# --- Base Schemas ---

class UserBase(BaseModel):
    phone_number: str
    name: Optional[str] = None
    constituency: Optional[str] = None
    ward: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionBase(BaseModel):
    user_id: int
    channel: str = "whatsapp"
    status: str = "active"


class SessionCreate(SessionBase):
    pass


class SessionResponse(SessionBase):
    id: int
    started_at: datetime
    last_active_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionBase(BaseModel):
    raw_content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    constituency: Optional[str] = None
    ward: Optional[str] = None
    status: str = "received"


class SubmissionCreate(SubmissionBase):
    user_id: int
    session_id: Optional[int] = None


class SubmissionResponse(SubmissionBase):
    id: int
    user_id: int
    session_id: Optional[int] = None
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueBase(BaseModel):
    title: str
    category: str
    severity: str = "medium"
    status: str = "open"


class IssueCreate(IssueBase):
    submission_id: int
    cluster_id: Optional[int] = None


class IssueResponse(IssueBase):
    id: int
    submission_id: int
    cluster_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InfrastructureBase(BaseModel):
    constituency: str
    name: str
    type: str
    location: Optional[str] = None
    status: str = "operational"
    capacity_details: Optional[str] = None


class InfrastructureCreate(InfrastructureBase):
    pass


class InfrastructureResponse(InfrastructureBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    constituency: str
    name: str
    type: str
    status: str
    budget: float = 0.0
    description: Optional[str] = None
    start_date: Optional[str] = None
    target_completion_date: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClusterBase(BaseModel):
    title: str
    category: str
    constituency: Optional[str] = None
    summary: str
    issue_count: int = 1


class ClusterCreate(ClusterBase):
    pass


class ClusterResponse(ClusterBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
