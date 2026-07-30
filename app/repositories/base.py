"""Base and concrete repository implementations for database models."""

from typing import Any, Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session
from app.db.session import Base
from app.models.domain import (
    User,
    ConversationSession,
    Submission,
    Issue,
    Cluster,
    Infrastructure,
    Project,
    AgentAction,
    AISummary,
)

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic base repository providing basic CRUD operations."""

    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()  # type: ignore[attr-defined]

    def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj_in: dict) -> T:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:  # noqa: A002
        db_obj = self.get(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
            return True
        return False


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_phone(self, phone_number: str) -> Optional[User]:
        return self.db.query(User).filter(User.phone_number == phone_number).first()

    def get_or_create(self, phone_number: str, name: Optional[str] = None, constituency: Optional[str] = None) -> User:
        user = self.get_by_phone(phone_number)
        if not user:
            user = self.create({
                "phone_number": phone_number,
                "name": name,
                "constituency": constituency,
            })
        return user


class SessionRepository(BaseRepository[ConversationSession]):
    def __init__(self, db: Session):
        super().__init__(ConversationSession, db)

    def get_active_session_for_user(self, user_id: int) -> Optional[ConversationSession]:
        return (
            self.db.query(ConversationSession)
            .filter(ConversationSession.user_id == user_id, ConversationSession.status == "active")
            .order_by(ConversationSession.started_at.desc())
            .first()
        )

    def get_or_create_active_session(self, user_id: int, channel: str = "whatsapp") -> ConversationSession:
        session = self.get_active_session_for_user(user_id)
        if not session:
            session = self.create({"user_id": user_id, "channel": channel, "status": "active"})
        return session


class SubmissionRepository(BaseRepository[Submission]):
    def __init__(self, db: Session):
        super().__init__(Submission, db)

    def list_by_constituency(self, constituency: str, skip: int = 0, limit: int = 100) -> List[Submission]:
        return (
            self.db.query(Submission)
            .filter(Submission.constituency == constituency)
            .offset(skip)
            .limit(limit)
            .all()
        )


class IssueRepository(BaseRepository[Issue]):
    def __init__(self, db: Session):
        super().__init__(Issue, db)

    def list_by_category(self, category: str, skip: int = 0, limit: int = 100) -> List[Issue]:
        return self.db.query(Issue).filter(Issue.category == category).offset(skip).limit(limit).all()


class InfrastructureRepository(BaseRepository[Infrastructure]):
    def __init__(self, db: Session):
        super().__init__(Infrastructure, db)

    def list_by_constituency(self, constituency: str) -> List[Infrastructure]:
        return self.db.query(Infrastructure).filter(Infrastructure.constituency == constituency).all()

    def list_by_type(self, infra_type: str) -> List[Infrastructure]:
        return self.db.query(Infrastructure).filter(Infrastructure.type == infra_type).all()


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: Session):
        super().__init__(Project, db)

    def list_by_constituency(self, constituency: str) -> List[Project]:
        return self.db.query(Project).filter(Project.constituency == constituency).all()

    def list_by_status(self, status: str) -> List[Project]:
        return self.db.query(Project).filter(Project.status == status).all()


class AgentActionRepository(BaseRepository[AgentAction]):
    def __init__(self, db: Session):
        super().__init__(AgentAction, db)


class AISummaryRepository(BaseRepository[AISummary]):
    def __init__(self, db: Session):
        super().__init__(AISummary, db)
