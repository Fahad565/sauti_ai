# Sprint 5 — Retrieval-Augmented Generation (RAG)

## Sprint

Sprint 5 — Retrieval-Augmented Generation

## Goal

Implement a Retrieval-Augmented Generation pipeline allowing Gemma to answer using the local civic database.

## Planned Work

- Retrieval Service
- Context Builder
- Prompt Builder
- Intent Classifier
- LangGraph Retrieval Node
- Search APIs
- Comprehensive Tests

## Deliverables

app/services/retrieval.py

app/services/context_builder.py

app/services/classifier.py

app/services/rag.py

app/prompts/

tests/test_retrieval.py

tests/test_rag.py

tests/test_classifier.py

tests/test_context_builder.py

tests/test_search_api.py

## Constraints

No vector database.

Use existing SQLAlchemy database.

Keyword + SQL filtering only.

Remain provider-agnostic.

Maintain clean architecture.

## Status

🟢 Complete

---

## Goal

Ground every AI response using constituency data stored in the database rather than relying solely on the LLM's general knowledge.

---

## Feature 5.1 — Retrieval Service

- [x] Create RetrievalService
- [x] Search Infrastructure
- [x] Search Projects
- [x] Search Previous Submissions
- [x] Search Issues
- [x] Return ranked retrieval results

Acceptance Criteria

- Relevant infrastructure returned
- Relevant projects returned
- Duplicate reports discoverable

---

## Feature 5.2 — Context Builder

- [x] Build reusable ContextBuilder
- [x] Combine infrastructure
- [x] Combine projects
- [x] Combine previous reports
- [x] Produce structured prompt context

Acceptance Criteria

- Context contains only relevant records
- Prompt remains within token limits

---

## Feature 5.3 — Prompt Templates

- [x] Create prompts/
- [x] system_prompt.md
- [x] rag_prompt.md
- [x] summarizer_prompt.md

Acceptance Criteria

- No hardcoded prompts
- Prompt builder loads templates

---

## Feature 5.4 — Intent Classification

- [x] Infrastructure Lookup
- [x] Project Lookup
- [x] Complaint
- [x] Status Update
- [x] General Question

Acceptance Criteria

- Intent detected correctly
- Confidence score returned

---

## Feature 5.5 — LangGraph RAG Pipeline

- [x] Retrieval Node
- [x] Context Node
- [x] Generation Node
- [x] Update graph routing

Acceptance Criteria

- Graph retrieves before generation
- Grounded responses generated

---

## Feature 5.6 — Search APIs

- [x] GET /api/v1/search
- [x] GET /api/v1/projects/search
- [x] GET /api/v1/infrastructure/search

Acceptance Criteria

- Search APIs return ranked results

---

## Feature 5.7 — Testing

- [x] Retrieval tests
- [x] Context Builder tests
- [x] Prompt Builder tests
- [x] Graph tests
- [x] End-to-end RAG tests

Acceptance Criteria

- Full pytest suite passes

---

## Commit Feature

- [x] Commit
- [x] Push
- [x] Pull Request
