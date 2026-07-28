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

## Feature 1.2 - Gemma 4 Integration

Status: Complete
Merged into: develop

# Project Status

Current Sprint:
Sprint 3 — Twilio Webhook Ingestion

Current Feature:
Twilio Webhook Ingestion

Current Branch:
feature/twilio-ingestion

Status:
🟢 Code Complete — Pending Commit & PR

---

---

# FEATURE 1.3 — Twilio WhatsApp Ingestion

Branch

feature/twilio-ingestion

Objective

Receive incoming WhatsApp messages from Twilio Sandbox and
forward them into the LangGraph agent.

### Tasks

- [x] Install Twilio SDK
- [x] Create app/api/webhook.py
- [x] Create app/services/twilio.py
- [x] Create app/schemas/webhook.py
- [x] Create POST /webhooks/twilio
- [x] Parse Twilio payload
- [x] Extract sender number
- [x] Extract message body
- [x] Invoke LangGraph graph
- [x] Return TwiML response
- [x] Add webhook tests
- [x] Verify local webhook
- [ ] Commit feature

---

## Acceptance Criteria

- [x] Webhook accepts POST requests.
- [x] Twilio payload parsed correctly.
- [x] Sender extracted.
- [x] Message extracted.
- [x] Graph invoked.
- [x] Gemma response returned.
- [x] Twilio receives valid TwiML.
- [x] Tests pass.

---

### Expected Files

app/api/webhook.py

app/services/twilio.py

app/schemas/webhook.py

tests/test_twilio_webhook.py

---

### Definition of Done

Webhook reachable locally

Ngrok tunnel works

Twilio Sandbox connected

Graph invoked

Gemma responds

Tests pass

PR merged
