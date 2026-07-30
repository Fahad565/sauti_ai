"""SQLAlchemy domain models for Sauti AI.

Contains models for User, Session, Submission, Issue, Cluster, Infrastructure,
Project, AgentAction, and AISummary.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    """Citizen user submitting feedback/complaints via WhatsApp or web."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    constituency = Column(String(100), nullable=True, index=True)
    ward = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    sessions = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")


class ConversationSession(Base):
    """Conversation session grouping multiple interactions."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    channel = Column(String(50), default="whatsapp", nullable=False)
    status = Column(String(50), default="active", nullable=False)
    started_at = Column(DateTime, default=utcnow)
    last_active_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="sessions")
    submissions = relationship("Submission", back_populates="session", cascade="all, delete-orphan")
    agent_actions = relationship("AgentAction", back_populates="session", cascade="all, delete-orphan")
    ai_summaries = relationship("AISummary", back_populates="session", cascade="all, delete-orphan")


class Submission(Base):
    """Citizen complaint or feedback submission."""

    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    raw_content = Column(Text, nullable=False)
    media_url = Column(String(500), nullable=True)
    media_type = Column(String(100), nullable=True)
    constituency = Column(String(100), nullable=True, index=True)
    ward = Column(String(100), nullable=True)
    status = Column(String(50), default="received", nullable=False)
    submitted_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="submissions")
    session = relationship("ConversationSession", back_populates="submissions")
    issues = relationship("Issue", back_populates="submission", cascade="all, delete-orphan")
    agent_actions = relationship("AgentAction", back_populates="submission", cascade="all, delete-orphan")
    ai_summaries = relationship("AISummary", back_populates="submission", cascade="all, delete-orphan")


class Cluster(Base):
    """Grouped thematic issue summary."""

    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    constituency = Column(String(100), nullable=True, index=True)
    summary = Column(Text, nullable=False)
    issue_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)

    issues = relationship("Issue", back_populates="cluster")


class Issue(Base):
    """Categorized problem or request extracted from a submission."""

    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    severity = Column(String(50), default="medium", nullable=False)
    status = Column(String(50), default="open", nullable=False)
    created_at = Column(DateTime, default=utcnow)

    submission = relationship("Submission", back_populates="issues")
    cluster = relationship("Cluster", back_populates="issues")


class Infrastructure(Base):
    """Constituency infrastructure asset (Roads, Schools, Hospitals, etc.)."""

    __tablename__ = "infrastructure"

    id = Column(Integer, primary_key=True, index=True)
    constituency = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(100), nullable=False, index=True)
    location = Column(String(200), nullable=True)
    status = Column(String(50), default="operational", nullable=False)
    capacity_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class Project(Base):
    """Constituency project (Ongoing, Planned, Completed)."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    constituency = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # Ongoing, Planned, Completed
    budget = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
    start_date = Column(String(50), nullable=True)
    target_completion_date = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class AgentAction(Base):
    """Log of actions executed by the agent pipeline."""

    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    input_state = Column(Text, nullable=True)
    output_state = Column(Text, nullable=True)
    reasoning_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    session = relationship("ConversationSession", back_populates="agent_actions")
    submission = relationship("Submission", back_populates="agent_actions")


class AISummary(Base):
    """AI generated analysis and summaries of submissions."""

    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    summary_text = Column(Text, nullable=False)
    extracted_intent = Column(String(100), nullable=True)
    key_entities = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    submission = relationship("Submission", back_populates="ai_summaries")
    session = relationship("ConversationSession", back_populates="ai_summaries")
