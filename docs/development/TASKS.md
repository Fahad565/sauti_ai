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

# Sprint 4 – Resilient Multi-Provider LLM Backend

## Objective

Replace the current NVIDIA-only implementation with a provider-agnostic architecture that supports multiple LLM providers and gracefully handles failures.

---

## Background

The current webhook depends entirely on NVIDIA's hosted endpoint.

Observed issues:

- API latency occasionally exceeds 60 seconds.
- Read timeout exceptions.
- Webhook processing becomes slow.
- Future providers cannot be added without modifying business logic.

We are migrating to a provider abstraction.

Google AI Studio (Gemini API) will become the primary provider.

NVIDIA remains optional as a future fallback.

---

## Deliverables

### 1. Provider Interface

Create an abstract provider interface.

Example:

app/services/llm/providers/base.py

Responsibilities:

- generate()
- health_check()
- provider_name()

Business logic must never depend on a specific vendor.

---

### 2. Google Provider

Create

app/services/llm/providers/google_provider.py

Requirements

- Use the official google-genai SDK.
- Authenticate with GOOGLE_API_KEY.
- Support configurable model names.
- Return a normalized response object.
- Raise custom exceptions on failures.

---

### 3. NVIDIA Provider

Move the existing NVIDIA implementation into

app/services/llm/providers/nvidia_provider.py

No functional changes except conforming to the new provider interface.

---

### 4. Provider Factory

Create

app/services/llm/provider_factory.py

Select provider using

LLM_PROVIDER=google
or

LLM_PROVIDER=nvidia

No application code should instantiate providers directly.

---

### 5. Configuration

Extend Settings with:

GOOGLE_API_KEY

GOOGLE_MODEL

LLM_PROVIDER

LLM_TIMEOUT

LLM_MAX_RETRIES

LLM_RETRY_DELAY

---

### 6. Retry Logic

Implement exponential backoff.

Retry transient failures.

Retry conditions:

- Timeout
- 429
- 500
- 502
- 503
- Connection errors

Do not retry validation errors.

---

### 7. Graceful Failure

The Twilio webhook must NEVER crash because of an LLM failure.

If every provider fails:

- Log the error.
- Return a friendly TwiML response.
- Return HTTP 200.

---

### 8. Logging

Log:

- provider
- selected model
- latency
- retries
- success/failure
- exception type

---

### 9. Tests

Create unit tests for:

✓ Google provider

✓ Provider factory

✓ Retry logic

✓ Timeout handling

✓ Provider selection

✓ Failure fallback

✓ Twilio webhook degradation

---

### 10. Documentation

Update:

README.md

ARCHITECTURE.md

API.md

CHANGELOG.md

Describe:

- Provider architecture
- Configuration
- Environment variables
- Failure handling
- Retry policy

---

## Acceptance Criteria

✓ Business logic contains no vendor-specific code.

✓ Provider can be changed using only environment variables.

✓ Google AI Studio is the default provider.

✓ Webhook remains responsive during provider failures.

✓ All existing tests continue to pass.

## ✓ New provider can be added by implementing the Provider interface without modifying existing business logic.

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
