# Fakturo

[![CI](https://github.com/Ros-turo/fakturo/actions/workflows/ci.yml/badge.svg)](https://github.com/Ros-turo/fakturo/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)

Fakturo is my first FastAPI project, built to learn and practice backend fundamentals: async web APIs, relational databases, background task processing, caching, and — in a later refactoring phase — SOLID/DRY/KISS software design principles applied to a real, working codebase (not a toy example).

> This is a learning project. Its purpose is to demonstrate backend engineering fundamentals and a documented refactoring process, not to serve as a production invoicing product.

## What it does

Fakturo is an invoicing API. Core flow:

1. Look up a company by its registration number (IČO) via the Czech **ARES** business registry API
2. Save the company as a client
3. Create invoices for that client, with line items and automatic VAT calculation
4. Export invoices to **PDF**
5. Track invoice status (draft → sent → paid / overdue) with an explicit, extensible transition table

Other features:
- JWT-based auth (access + refresh tokens), with token blacklisting on logout and per-IP rate limiting on login
- Redis caching (client lookups) with cache invalidation on update
- Background PDF generation and email dispatch via Celery
- Multi-tenant data isolation (users only ever see their own clients/invoices)
- Domain-specific exceptions with centralized HTTP error mapping (no raw `HTTPException` scattered across business logic)
- **Coming soon:** invoice tagging (`TagRepo` exists in the codebase, router/endpoints not yet wired up)

## Tech stack

| Layer              | Technology                         |
|--------------------|------------------------------------|
| API framework      | FastAPI (async)                    |
| Database           | PostgreSQL, via SQLAlchemy (async) |
| Migrations         | Alembic                            |
| Cache              | Redis                              |
| Background jobs    | Celery                             |
| Containerization   | Docker / docker-compose            |
| Testing            | pytest, coverage                   |
| Type checking      | mypy                               |
| Formatting/linting | ruff                               |

## Architecture

The codebase follows a layered structure:

```
routers/       → HTTP only: request parsing, calling services, shaping the response
services/      → business logic and orchestration (no FastAPI/DB-specific types)
repositories/  → persistence, typed against Protocol interfaces for testability
security/      → JWT, password hashing, rate limiting (framework-agnostic)
exceptions.py  → domain exceptions, mapped centrally to HTTP responses
```

This structure is the result of a documented SOLID/DRY/KISS refactoring pass — see the `refactor/solid-principles` branch history and [PR #26](https://github.com/Ros-turo/fakturo/pull/26) for the full before/after story.

## Running locally

### With Docker (recommended)

```bash
cp .env.example .env
cp .env.example .env.db   # only POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB are used from this file
docker compose up -d
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Without Docker

```bash
cp .env.example .env.local
# edit .env.local: point redis_host and the host part of db_url/test_db_url to localhost
uv sync
make local_up      # starts db, redis, worker in Docker; app itself runs locally
ENV_FILE=.env.local uv run uvicorn main:app --reload
```

## Testing

```bash
make local_test     # or: ENV_FILE=.env.local pytest -q
make lint            # mypy
make local_ci         # lint + test
```

Current status: 65 tests passing, 0 mypy errors, 82% coverage.

## Project status / known limitations

This is an actively evolving learning project. A few notable open items:
- Rate limiting is currently applied only to `/auth/login`, not project-wide
- Some Celery background job code duplicates repository query logic instead of reusing it
- Invoice tagging (`TagRepo`) is implemented but not yet exposed via any endpoint