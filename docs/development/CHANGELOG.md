# CHANGELOG

**Project:** Sauti AI

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Bootstrap FastAPI project skeleton (Feature 0.1).
- `app/` Python package with sub-packages: `api`, `config`, `services`,
  `models`, `schemas`, `middleware`, `utils`.
- `app/main.py` — application entrypoint with `create_app()` factory
  and module-level `app` instance for `uvicorn app.main:app`.
- `GET /` endpoint returning `{"service": "Sauti AI", "status": "running"}`.
- `app/config/settings.py` — typed `Settings` class using
  `pydantic_settings.BaseSettings` with `.env` file support and
  `get_settings()` cached accessor.
- `requirements.txt` pinning `fastapi`, `uvicorn`, `python-dotenv`,
  `pydantic-settings`.
- `.env.example` documenting available environment variables.
- `.gitignore` covering Python, virtualenv, IDE, test, and OS artifacts.
- `tests/` package with smoke tests for the root endpoint and settings.

### Verified

- `uvicorn app.main:app` starts successfully.
- `GET /` returns HTTP 200 with the expected JSON payload.
- `GET /docs` (Swagger UI) returns HTTP 200.
- `GET /openapi.json` is auto-generated with `title="Sauti AI"`,
  `version="0.1.0"`, and `paths=["/"]`.
- `pytest` suite passes (3 passed).

---

## [0.1.0] — 2026-07-25

### Added

- Initial repository bootstrap.
