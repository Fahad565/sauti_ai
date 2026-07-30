"""Persistence service for handling database saving during agent workflows and webhooks."""

import json
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session as DBSession

from app.db.session import SessionLocal
from app.repositories import (
    UserRepository,
    SessionRepository,
    SubmissionRepository,
    AgentActionRepository,
    AISummaryRepository,
)
from app.models.domain import User, ConversationSession, Submission

logger = logging.getLogger(__name__)


def record_inbound_message(
    phone_number: str,
    raw_content: str,
    user_name: Optional[str] = None,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None,
    db: Optional[DBSession] = None,
) -> Tuple[User, ConversationSession, Submission]:
    """Create or fetch User, active Session, and save inbound Submission."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        user_repo = UserRepository(db)
        session_repo = SessionRepository(db)
        submission_repo = SubmissionRepository(db)

        user = user_repo.get_or_create(phone_number=phone_number or "unknown", name=user_name)
        session = session_repo.get_or_create_active_session(user_id=int(user.id))  # type: ignore[arg-type]


        submission = submission_repo.create({
            "session_id": session.id,
            "user_id": user.id,
            "raw_content": raw_content,
            "media_url": media_url,
            "media_type": media_type,
            "constituency": user.constituency,
            "ward": user.ward,
            "status": "received",
        })

        return user, session, submission
    finally:
        if close_db:
            db.close()


def record_agent_execution(
    session_id: Optional[int],
    submission_id: Optional[int],
    final_state: dict,
    db: Optional[DBSession] = None,
) -> None:
    """Record agent actions and AI summary output into DB."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        action_repo = AgentActionRepository(db)
        summary_repo = AISummaryRepository(db)

        steps = final_state.get("steps", [])
        response = final_state.get("response", "")
        analysis = final_state.get("analysis", "")
        metadata = final_state.get("metadata", {})

        action_repo.create({
            "session_id": session_id,
            "submission_id": submission_id,
            "action_type": "agent_execution",
            "input_state": json.dumps({"input_message": final_state.get("input_message")}),
            "output_state": json.dumps({"response": response, "steps": steps}),
            "reasoning_notes": f"Executed steps: {', '.join(steps)}",
        })

        if analysis:
            summary_repo.create({
                "session_id": session_id,
                "submission_id": submission_id,
                "summary_text": analysis,
                "extracted_intent": metadata.get("analyze_provider", "llm_analysis"),
                "confidence_score": 1.0,
            })
    except Exception as exc:
        logger.exception("Failed to record agent execution in database: %s", exc)
    finally:
        if close_db:
            db.close()
