"""End-to-end and integration tests for RAG pipeline."""

import pytest
from sqlalchemy.orm import Session

from app.db.session import Base, SessionLocal, engine
from app.db.seed import seed_database
from app.services.llm import ChatCompletion, GemmaClient
from app.services.rag import RAGPipeline
from app.services.prompt_builder import render_rag_prompt, render_system_prompt


class MockLLM(GemmaClient):
    """Mock LLM client for RAG tests."""

    def complete(self, messages):
        return ChatCompletion(
            text="Grounded answer: Likoni Level 4 Hospital is fully operational.",
            model="mock-gemma",
            provider="mock",
            raw={},
        )


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_database(session)
    yield session
    session.close()


def test_prompt_builder_rendering():
    system = render_system_prompt()
    assert "Sauti AI" in system

    rag_prompt = render_rag_prompt(
        query="Where is the hospital?",
        context="Likoni Hospital located in Shelly Beach.",
        intent="infrastructure_lookup",
        confidence=0.9,
        constituency="Likoni",
    )
    assert "Where is the hospital?" in rag_prompt
    assert "Likoni Hospital located in Shelly Beach." in rag_prompt
    assert "Likoni" in rag_prompt


def test_rag_pipeline_execution(db: Session):
    mock_llm = MockLLM()
    pipeline = RAGPipeline(db=db, llm_client=mock_llm)

    res = pipeline.process(query="Where is the hospital?", constituency="Likoni")
    assert res["query"] == "Where is the hospital?"
    assert res["constituency"] == "Likoni"
    assert res["intent"] == "infrastructure_lookup"
    assert "Grounded answer" in res["response"]
    assert "infrastructure" in res["retrieval_results"]


def test_rag_pipeline_via_agent(db: Session, monkeypatch: pytest.MonkeyPatch):
    mock_llm = MockLLM()
    from app.services import llm as llm_module
    monkeypatch.setattr(llm_module, "get_llm", lambda: mock_llm)

    pipeline = RAGPipeline(db=db, llm_client=mock_llm)
    final_state = pipeline.process_via_agent(query="Where is Likoni level 4 hospital?", constituency="Likoni")

    assert final_state["steps"] == ["intake", "classify", "retrieval", "context", "analyze", "respond"]
    assert "retrieved_data" in final_state
    assert "retrieved_context" in final_state
    assert final_state["intent"] == "infrastructure_lookup"
    assert "Grounded answer" in final_state["response"]
