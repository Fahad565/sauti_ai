"""CRUD API endpoints for civic data persistence.

Exposes RESTful endpoints for Users, Sessions, Submissions, Issues,
Infrastructure, Projects, and Clusters.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import (
    UserRepository,
    SessionRepository,
    SubmissionRepository,
    IssueRepository,
    InfrastructureRepository,
    ProjectRepository,
    BaseRepository,
)
from app.models.domain import Cluster
from app.schemas.domain import (
    UserCreate,
    UserResponse,
    SessionCreate,
    SessionResponse,
    SubmissionCreate,
    SubmissionResponse,
    IssueCreate,
    IssueResponse,
    InfrastructureCreate,
    InfrastructureResponse,
    ProjectCreate,
    ProjectResponse,
    ClusterCreate,
    ClusterResponse,
)

router = APIRouter(prefix="/api/v1", tags=["crud"])


# --- Users Endpoints ---

@router.get("/users", response_model=List[UserResponse], summary="List users")
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.list(skip=skip, limit=limit)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create user")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    existing = repo.get_by_phone(user_in.phone_number)
    if existing:
        raise HTTPException(status_code=400, detail="User with this phone number already exists")
    return repo.create(user_in.model_dump())


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID")
def get_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get(user_id)
    if not user:
        raise HTTPException(status_code=44, detail="User not found")
    return user


# --- Submissions Endpoints ---

@router.get("/submissions", response_model=List[SubmissionResponse], summary="List citizen submissions")
def list_submissions(
    constituency: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    repo = SubmissionRepository(db)
    if constituency:
        return repo.list_by_constituency(constituency, skip=skip, limit=limit)
    return repo.list(skip=skip, limit=limit)


@router.post("/submissions", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED, summary="Create submission")
def create_submission(submission_in: SubmissionCreate, db: Session = Depends(get_db)):
    repo = SubmissionRepository(db)
    user_repo = UserRepository(db)
    user = user_repo.get(submission_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return repo.create(submission_in.model_dump())


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse, summary="Get submission by ID")
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    repo = SubmissionRepository(db)
    submission = repo.get(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


# --- Infrastructure Endpoints ---

@router.get("/infrastructure", response_model=List[InfrastructureResponse], summary="List constituency infrastructure")
def list_infrastructure(
    constituency: Optional[str] = None,
    type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    repo = InfrastructureRepository(db)
    if constituency:
        return repo.list_by_constituency(constituency)
    if type:
        return repo.list_by_type(type)
    return repo.list(skip=skip, limit=limit)


@router.post("/infrastructure", response_model=InfrastructureResponse, status_code=status.HTTP_201_CREATED, summary="Create infrastructure asset")
def create_infrastructure(infra_in: InfrastructureCreate, db: Session = Depends(get_db)):
    repo = InfrastructureRepository(db)
    return repo.create(infra_in.model_dump())


@router.get("/infrastructure/{infra_id}", response_model=InfrastructureResponse, summary="Get infrastructure by ID")
def get_infrastructure(infra_id: int, db: Session = Depends(get_db)):
    repo = InfrastructureRepository(db)
    infra = repo.get(infra_id)
    if not infra:
        raise HTTPException(status_code=404, detail="Infrastructure asset not found")
    return infra


# --- Projects Endpoints ---

@router.get("/projects", response_model=List[ProjectResponse], summary="List constituency projects")
def list_projects(
    constituency: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    repo = ProjectRepository(db)
    if constituency:
        return repo.list_by_constituency(constituency)
    if status:
        return repo.list_by_status(status)
    return repo.list(skip=skip, limit=limit)


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Create project")
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    return repo.create(project_in.model_dump())


@router.get("/projects/{project_id}", response_model=ProjectResponse, summary="Get project by ID")
def get_project(project_id: int, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# --- Issues Endpoints ---

@router.get("/issues", response_model=List[IssueResponse], summary="List issues")
def list_issues(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    repo = IssueRepository(db)
    if category:
        return repo.list_by_category(category, skip=skip, limit=limit)
    return repo.list(skip=skip, limit=limit)


@router.post("/issues", response_model=IssueResponse, status_code=status.HTTP_201_CREATED, summary="Create issue")
def create_issue(issue_in: IssueCreate, db: Session = Depends(get_db)):
    repo = IssueRepository(db)
    submission_repo = SubmissionRepository(db)
    if not submission_repo.get(issue_in.submission_id):
        raise HTTPException(status_code=404, detail="Submission not found")
    return repo.create(issue_in.model_dump())


@router.get("/issues/{issue_id}", response_model=IssueResponse, summary="Get issue by ID")
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    repo = IssueRepository(db)
    issue = repo.get(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


# --- Sessions Endpoints ---

@router.get("/sessions", response_model=List[SessionResponse], summary="List sessions")
def list_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    return repo.list(skip=skip, limit=limit)


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, summary="Create session")
def create_session(session_in: SessionCreate, db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    user_repo = UserRepository(db)
    if not user_repo.get(session_in.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return repo.create(session_in.model_dump())


# --- Clusters Endpoints ---

@router.get("/clusters", response_model=List[ClusterResponse], summary="List issue clusters")
def list_clusters(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = BaseRepository(Cluster, db)
    return repo.list(skip=skip, limit=limit)


@router.post("/clusters", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED, summary="Create cluster")
def create_cluster(cluster_in: ClusterCreate, db: Session = Depends(get_db)):
    repo = BaseRepository(Cluster, db)
    return repo.create(cluster_in.model_dump())
