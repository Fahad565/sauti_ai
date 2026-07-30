"""Prompt Builder service for Sauti AI.

Loads prompt templates from app/prompts directory and dynamic parameter substitution.
"""

from __future__ import annotations

import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt_template(filename: str) -> str:
    """Load prompt markdown file content by filename."""
    file_path = PROMPTS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt template file not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def render_system_prompt() -> str:
    """Render system prompt."""
    return load_prompt_template("system_prompt.md")


def render_rag_prompt(
    query: str,
    context: str,
    intent: str = "general_question",
    confidence: float = 1.0,
    constituency: str = "General",
) -> str:
    """Render RAG prompt template with given context and metadata."""
    template = load_prompt_template("rag_prompt.md")
    formatted_context = context if context.strip() else "No specific matching constituency database records found."
    return template.format(
        query=query,
        context=formatted_context,
        intent=intent,
        confidence=f"{confidence:.2f}",
        constituency=constituency,
    )


def render_summarizer_prompt(submission_text: str) -> str:
    """Render summarizer prompt template."""
    template = load_prompt_template("summarizer_prompt.md")
    return template.format(submission_text=submission_text)
