# RAG Architecture — Sauti AI

## Overview

Sauti AI implements a deterministic, SQL-backed Retrieval-Augmented Generation (RAG) architecture. Grounding AI responses in real constituency database records ensures that responses reference factual assets, active development projects, and historical citizen complaints rather than relying solely on LLM parametric memory.

---

## 1. Retrieval Architecture

The retrieval layer sits between intent classification and context construction in the LangGraph graph execution pipeline:

```
[Inbound Message] 
       │
       ▼
[Intake Node]
       │
       ▼
[Classify Node] (IntentClassifier)
       │
       ▼
[Retrieval Node] (RetrievalService) ◄──► [SQLite / SQLAlchemy DB]
       │
       ▼
[Context Node] (ContextBuilder)
       │
       ▼
[Analyze / RAG Node] (Gemma 4 LLM)
       │
       ▼
[Respond Node]
```

---

## 2. SQL Retrieval Strategy

In alignment with **DECISION-0011**, Sauti AI leverages existing relational database tables (`infrastructure`, `projects`, `submissions`, `issues`) instead of introducing an external vector store.

- **Infrastructure Search**: Queries `name`, `type`, `location`, `capacity_details`, filtered by `constituency`.
- **Project Search**: Queries `name`, `type`, `description`, `status`, filtered by `constituency`.
- **Submissions Search**: Queries `raw_content` and `ward` for duplicate/historical report discovery.
- **Issue Search**: Queries `title`, `category`, and `severity`.

---

## 3. Relevance Ranking

Results retrieved from SQL are dynamically scored and sorted by a keyword-based relevance model:

```python
score = sum(1.0 for kw in query_keywords if kw in text) + bonus(0.5 if kw in title/name)
```

Top results per category are selected and passed to the context builder.

---

## 4. Context Assembly & Prompt Construction

1. **Context Assembly (`ContextBuilder`)**:
   - Converts structured DB dicts into clean, human-readable Markdown sections.
   - Enforces a maximum character budget (default `4000` chars) to keep prompts within LLM context windows.

2. **Prompt Templates (`app/prompts/`)**:
   - `system_prompt.md`: Defines Sauti AI's civic persona and strict grounding policy.
   - `rag_prompt.md`: Fills template slots (`{query}`, `{context}`, `{intent}`, `{confidence}`, `{constituency}`).
   - `summarizer_prompt.md`: Formats structured summaries for reporting.

---

## 5. Search API Layer

Exposes direct search capabilities for frontends and dashboard clients:
- `GET /api/v1/search?q={query}&constituency={constituency}&limit=5`
- `GET /api/v1/projects/search?q={query}&constituency={constituency}`
- `GET /api/v1/infrastructure/search?q={query}&constituency={constituency}`

---

## 6. Future Roadmap

- **Vector Database Support**: Integration with pgvector or Qdrant for semantic similarity.
- **Hybrid Search**: Combining keyword BM25/SQL filters with dense vector embeddings.
- **Embeddings**: Local embedding generation via Gemma/sentence-transformers.
