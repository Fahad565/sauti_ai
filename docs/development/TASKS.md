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

# Project Status

Current Sprint:
Sprint 1 — Agent Skeleton

Current Epic:
AI Agent Foundation

Current Feature:
LangGraph Agent Skeleton

Current Branch:
feature/agent-skeleton

Status:
� Code Complete — Pending Commit & PR

---

# EPIC 1 — AI Agent Foundation

Goal

Create the skeleton architecture of the LangGraph agent.

No AI reasoning should exist yet.

Only project structure and graph wiring.

## FEATURE 1.1 — Agent Skeleton

Branch

feature/agent-skeleton

Objective

## Create the initial LangGraph architecture that future intelligence will plug into.

### Tasks

- [x] Install LangGraph
- [x] Install LangChain Core
- [x] Create app/agent/
- [x] Create graph.py
- [x] Create state.py
- [x] Create nodes.py
- [x] Create router.py
- [x] Define AgentState
- [x] Create placeholder nodes
- [x] Build minimal graph
- [x] Compile graph
- [x] Add smoke test
- [x] Verify graph compiles
- [ ] Commit feature

---

### Acceptance Criteria

- Graph compiles successfully.
- Placeholder nodes execute.
- State flows through graph.
- No LLM connected.
- No tools connected.
- No memory.
- Tests pass.

---

### Expected Files

app/agent/

    __init__.py
    graph.py
    nodes.py
    router.py
    state.py

---

### Definition of Done

- Graph compiles.
- Tests pass.
- Commit created.
- PR opened.
- Merged into develop.
- Development Cloud Run deployed.

---

Status

## 🟡 In Progress

### Acceptance Criteria

- FastAPI application starts successfully.
- Root endpoint returns HTTP 200.
- Swagger UI loads correctly.
- Repository structure follows project conventions.
- requirements.txt committed.
- .env.example committed.
- No AI logic exists.
- No database exists.
- No LangGraph exists.

---

### Expected Files

README.md

requirements.txt

.env.example

app/main.py

app/config.py

.gitignore

---

### Definition of Done

- All acceptance criteria satisfied.
- Local smoke test passes.
- Git commit created.
- Pull Request opened against develop.
- Successfully merged into develop.
- Automatically deployed to Development Cloud Run.

---

Status

🟡 In Progress
