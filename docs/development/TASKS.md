# TASKS.md

**Project:** Sauti AI

**Purpose**

This document is the authoritative engineering backlog for the project.

Every implementation begins with a Task.

Every Task belongs to a Feature.

Every Feature belongs to an Epic.

No code should be written before the corresponding task has clear acceptance criteria.

---

# COMPLETED FEATURES

## Feature 0.1 — Bootstrap FastAPI Project

Status:
✅ Complete

Merged into:
develop

Acceptance Criteria:

- [x] FastAPI starts
- [x] Root endpoint
- [x] Swagger works
- [x] Tests pass
- [x] PR merged

## Feature 1.1 — LangGraph Agent Skeleton

Status:
✅ Complete

Merged into:
develop

Acceptance Criteria

- [x] Graph compiles
- [x] Placeholder nodes
- [x] StateGraph created
- [x] Smoke tests
- [x] PR merged

# Project Status

Current Sprint:
Sprint 2 — LLM Integration

Current Feature:
Gemma 4 Integration

Current Branch:
feature/gemma4-integration

Status:
🟢 Code Complete — Pending Commit & PR

---

---

## FEATURE 1.2 — Gemma 4 Integration

Branch

feature/llm-integration

Objective

Connect the LangGraph agent to a real LLM while keeping the architecture
clean and provider-agnostic.

### Tasks

- [x] Configure NVIDIA API client
- [x] Add NVIDIA API key configuration
- [x] Create LLM service
- [x] Implement Gemma 4 wrapper
- [x] Replace placeholder analyze node
- [x] Invoke Gemma from LangGraph
- [x] Handle API failures
- [x] Add integration tests
- [x] Verify end-to-end graph execution
- [ ] Commit feature

---

### Acceptance Criteria

- [x] Gemma 4 responds successfully (verified via mock transport).
- [x] Graph executes using the real LLM (via mocked NVIDIA endpoint).
- [x] API key loaded from environment.
- [x] Graceful error handling.
- [x] Existing tests still pass.
- [x] No tools connected.
- [x] No memory connected.

---

### Expected Files

app/services/llm.py

app/config/settings.py

app/agent/nodes.py

tests/test_llm.py

.env.example

---

### Definition of Done

- LLM integrated.
- Tests pass.
- Commit created.
- PR opened.
- Merged into develop.
