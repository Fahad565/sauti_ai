"""Agent node functions for Sauti AI RAG reasoning graph.

Each node accepts an :class:`AgentState` and returns a partial state
update that LangGraph will merge into the running state.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from app.agent.state import AgentState
from app.db.session import SessionLocal
from app.services import llm as llm_module
from app.services.classifier import IntentClassifier
from app.services.context_builder import ContextBuilder
from app.services.llm import ChatMessage, GemmaClient, LLMError
from app.services.prompt_builder import render_rag_prompt, render_system_prompt
from app.services.retrieval import RetrievalService, extract_constituency

logger = logging.getLogger(__name__)


def intake_node(state: AgentState) -> dict[str, object]:
    """First node - accepts the inbound message."""
    t = time.perf_counter()
    message = state.get("input_message", "")
    steps = list(state.get("steps", []))
    steps.append("intake")

    metadata = dict(state.get("metadata", {}))
    metadata["intake_length"] = str(len(message))

    logger.info("⏱ intake_node: message_len=%d  %.3fs", len(message), time.perf_counter() - t)

    return {
        "steps": steps,
        "metadata": metadata,
    }


def classify_node(state: AgentState) -> dict[str, object]:
    """Classifies citizen intent and extracts constituency entities from inbound message."""
    t = time.perf_counter()
    message = state.get("input_message", "")
    steps = list(state.get("steps", []))
    steps.append("classify")

    classifier = IntentClassifier()
    res = classifier.classify(message)

    existing_constituency = state.get("constituency")
    extracted = extract_constituency(message)
    constituency = existing_constituency or extracted

    logger.info(
        "⏱ classify_node: intent=%s confidence=%.2f constituency=%s (extracted=%s)  %.3fs",
        res["intent"],
        res["confidence"],
        constituency or "General",
        extracted,
        time.perf_counter() - t,
    )

    update: dict[str, object] = {
        "steps": steps,
        "intent": res["intent"],
        "intent_confidence": res["confidence"],
    }
    if constituency:
        update["constituency"] = constituency

    return update


def retrieval_node(state: AgentState) -> dict[str, object]:
    """Retrieves relevant SQL database records using RetrievalService."""
    t = time.perf_counter()
    message = state.get("input_message", "")
    constituency = state.get("constituency") or extract_constituency(message)
    steps = list(state.get("steps", []))
    steps.append("retrieval")

    db = state.get("db")
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        retrieval_svc = RetrievalService(db)
        retrieval_results = retrieval_svc.search_all(query=message, constituency=constituency, limit=5)
    finally:
        if close_db:
            db.close()

    total = retrieval_results.get("total_matches", 0)
    infra_cnt = len(retrieval_results.get("infrastructure", []))
    proj_cnt = len(retrieval_results.get("projects", []))
    sub_cnt = len(retrieval_results.get("submissions", []))
    iss_cnt = len(retrieval_results.get("issues", []))

    logger.info(
        "⏱ retrieval_node: constituency=%s total=%d (infra=%d proj=%d subs=%d issues=%d)  %.3fs",
        constituency or "All",
        total,
        infra_cnt,
        proj_cnt,
        sub_cnt,
        iss_cnt,
        time.perf_counter() - t,
    )

    return {
        "steps": steps,
        "retrieved_data": retrieval_results,
    }


def context_node(state: AgentState) -> dict[str, object]:
    """Assembles prompt context from retrieval results using ContextBuilder."""
    t = time.perf_counter()
    steps = list(state.get("steps", []))
    steps.append("context")

    retrieved_data = state.get("retrieved_data", {})
    builder = ContextBuilder(max_chars=4000)
    context_str = builder.build_context(retrieved_data)

    logger.info(
        "⏱ context_node: context_chars=%d  %.3fs",
        len(context_str),
        time.perf_counter() - t,
    )

    return {
        "steps": steps,
        "retrieved_context": context_str,
    }


def analyze_node(
    state: AgentState,
    *,
    client: GemmaClient | None = None,
) -> dict[str, object]:
    """LLM-backed analysis and RAG generation node."""
    t = time.perf_counter()
    message = state.get("input_message", "")
    intent = state.get("intent", "general_question")
    confidence = state.get("intent_confidence", 1.0)
    constituency = state.get("constituency") or "General"
    retrieved_context = state.get("retrieved_context", "")

    steps = list(state.get("steps", []))
    steps.append("analyze")

    metadata = dict(state.get("metadata", {}))

    llm = client or llm_module.get_llm()
    system_prompt = render_system_prompt()
    user_prompt = render_rag_prompt(
        query=message,
        context=retrieved_context,
        intent=intent,
        confidence=confidence,
        constituency=constituency,
    )

    total_prompt_chars = len(system_prompt) + len(user_prompt)
    logger.info(
        "⏱ analyze_node: intent=%s context_chars=%d total_prompt_chars=%d — calling LLM…",
        intent,
        len(retrieved_context),
        total_prompt_chars,
    )

    try:
        completion = llm.complete(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
        )
    except LLMError as exc:
        logger.warning("LLM call failed in analyze_node: %s", exc)
        metadata["analyze_error"] = str(exc)
        return {"steps": steps, "metadata": metadata}

    elapsed = time.perf_counter() - t
    raw = completion.raw if isinstance(completion.raw, dict) else {}
    metadata["analyze_model"] = str(raw.get("model", completion.model or "unknown"))
    metadata["analyze_provider"] = completion.provider
    metadata["analyze_latency_s"] = f"{elapsed:.2f}"

    logger.info(
        "⏱ analyze_node: LLM responded in %.2fs (provider=%s model=%s)",
        elapsed,
        completion.provider,
        metadata["analyze_model"],
    )

    return {
        "steps": steps,
        "analysis": completion.text,
        "metadata": metadata,
    }


def respond_node(state: AgentState) -> dict[str, object]:
    """Final node - produces a response for the caller."""
    t = time.perf_counter()
    analysis = state.get("analysis", "")
    analyze_error = state.get("metadata", {}).get("analyze_error")
    steps = list(state.get("steps", []))
    steps.append("respond")

    if analyze_error:
        response = (
            "LLM unavailable. The analyze node reported: "
            f"{analyze_error}"
        )
    elif analysis:
        response = analysis
    else:
        message = state.get("input_message", "")
        response = f"ack: {message}"

    logger.info("⏱ respond_node: response_chars=%d  %.3fs", len(response), time.perf_counter() - t)

    return {
        "steps": steps,
        "response": response,
    }
