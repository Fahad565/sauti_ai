"""RAG Service combining intent classification, SQL retrieval, context building, and LLM generation."""

from __future__ import annotations

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.agent.graph import compile_graph
from app.services.classifier import IntentClassifier
from app.services.context_builder import ContextBuilder
from app.services.llm import GemmaClient, ChatMessage, get_llm
from app.services.prompt_builder import render_rag_prompt, render_system_prompt
from app.services.retrieval import RetrievalService


class RAGPipeline:
    """End-to-end RAG pipeline orchestration service."""

    def __init__(self, db: Session, llm_client: Optional[GemmaClient] = None):
        self.db = db
        self.llm = llm_client or get_llm()
        self.classifier = IntentClassifier()
        self.retrieval_svc = RetrievalService(db)
        self.context_builder = ContextBuilder()

    def process(
        self,
        query: str,
        constituency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute complete RAG pipeline synchronously."""
        # 1. Intent Classification
        classification = self.classifier.classify(query)
        intent = classification["intent"]
        confidence = classification["confidence"]

        # 2. SQL Retrieval
        retrieval_results = self.retrieval_svc.search_all(
            query=query, constituency=constituency, limit=5
        )

        # 3. Context Construction
        context_str = self.context_builder.build_context(retrieval_results)

        # 4. Prompt Rendering & LLM Generation
        system_prompt = render_system_prompt()
        rag_prompt = render_rag_prompt(
            query=query,
            context=context_str,
            intent=intent,
            confidence=confidence,
            constituency=constituency or "General",
        )

        completion = self.llm.complete(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=rag_prompt),
            ]
        )

        return {
            "query": query,
            "constituency": constituency,
            "intent": intent,
            "intent_confidence": confidence,
            "retrieval_results": retrieval_results,
            "context": context_str,
            "response": completion.text,
            "provider": completion.provider,
            "model": completion.model,
        }

    def process_via_agent(
        self,
        query: str,
        constituency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute RAG pipeline using LangGraph compiled graph."""
        graph = compile_graph()
        initial_state = {
            "input_message": query,
            "constituency": constituency,
            "db": self.db,
            "steps": [],
            "metadata": {},
        }
        return graph.invoke(initial_state)
