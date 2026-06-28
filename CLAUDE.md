# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FlexiAnalyse is a multi-tenant RAG / document-intelligence platform. A React + Vite
SPA frontend talks to a Python/Flask backend that ingests documents from external
connectors (Google Drive, Dropbox, SharePoint, SQL), embeds them into a vector store,
builds a knowledge graph, and answers questions with a LangGraph-based search agent.
The codebase is bilingual — much of the code, comments, and log strings are in French.

## Commands

### Frontend (repo root)
```bash
npm install          # install deps
npm run dev          # Vite dev server (http://localhost:5173)
npm run build        # production build → dist/
npm run lint         # eslint over the repo
npm run preview      # serve the production build
```
There is no frontend test runner configured.

The `@` import alias maps to `src/` (see `vite.config.ts`).

### Backend (`backend/`)
```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows; venv already present
pip install -r requirements.txt
python main.py                                   # Flask API on http://0.0.0.0:5000
```

Celery worker (document ingestion runs here, requires Redis):
```bash
cd backend
celery -A celery_app worker --loglevel=info
```

Database migrations (Flask-Migrate / Alembic):
```bash
cd backend
flask db migrate -m "message"   # autogenerate from model changes
flask db upgrade                # apply
```

MCP connector servers (separate Dockerized microservices):
```bash
cd backend/ai/mcp/servers
docker-compose up -d            # starts sql/drive/sharepoint/dropbox MCP servers on ports 3001-3004
```

### Configuration
Copy `.env.example` → `.env`. Frontend reads `VITE_*` vars (notably `VITE_API_URL`,
defaulting to `http://localhost:5000` or `https://flexianalyse.com` depending on the
component). Backend reads PostgreSQL (`PG_*`), Redis (`REDIS_URL`), Firebase, OpenAI,
AWS, and per-connector OAuth credentials. There is no test suite.

## Architecture

### Two backend entry points (important)
The backend has a **new MVC stack** and a **legacy AI stack** that both bind port 5000:

- `backend/main.py` → `create_app()` — the new app. Registers Flask-SQLAlchemy,
  Flask-Migrate, Celery, Flask-Admin, and all MVC blueprints. `mount_legacy_ai_routes()`
  exists to graft the legacy routes onto this app but is currently commented out.
- `backend/legacy_ai_routes.py` — the original monolithic Flask app holding the
  chat/RAG/upload endpoints (`/query`, `/upload`, `/summarize_file_stream`,
  `/summarize_repository_stream`, `/models`, `/index-directory`, `/auth/*`). The SPA's
  chat UI (`FlexiAnalyseApp.tsx`, `Sidebar.tsx`) calls these legacy endpoints, while
  org/user/connector management calls the new `/api/v2/*` routes.

When changing chat/summarize/upload behavior, look in `legacy_ai_routes.py` and the
`services/` it imports. When changing org/dept/user/role/connector/lead management,
look in the MVC layer.

### New MVC layer (`backend/`)
Layered request flow: **routes → controllers → services → repositories → models**.
- `routes/__init__.py` registers blueprints; the `api_v2` blueprint is `/api/v2`.
- `controllers/` — one module per resource (organization, department, user, role, lead,
  mcp), each exposing `register(blueprint)`. Tenant context comes from `X-User-Id` /
  `X-Organization-Id` request headers.
- `services/` — business logic; `services/locator.py` wires service instances.
- `repositories/` — DB access over SQLAlchemy models, all extending `repositories/base.py`.
- `models/` — SQLAlchemy ORM models (organization, user, role, permission, department,
  connector, resource, conversation, knowledge_graph, lead, audit_log, etc.).
- `config/` — `settings.py` (`configure_app`), `extensions.py` (`db`, `migrate`),
  `celery_config.py`. DB URI is built from `PG_*` env vars (PostgreSQL + pgvector).
- `admin.py` — Flask-Admin dashboard.

### Connectors + ingestion pipeline
- `connectors/<provider>/` (google_drive, dropbox, sharepoint, sql) each have
  `service.py`, `sync.py`, and `mcp_client.py`. They talk to the MCP servers over HTTP
  via `services/mcp_http_client.py`.
- `auth/` holds the OAuth callback blueprints for each connector.
- `ai/mcp/servers/` — standalone Dockerized MCP microservices (one per connector),
  each with its own `server.py` / `tools.py` / `Dockerfile`. URLs configured via
  `*_MCP_URL` env vars matching `docker-compose.yml` ports (3001-3004).
- Ingestion is **Celery-driven**: `ai/agents/office_manager/ingestion/tasks.py` —
  `trigger_ingestion_for_connector` → `ingest_batch` (50 files) → `ingest_single_file`.
  Heavy objects (extractor, embedder, encryption) are lazy singletons created inside the
  worker, never at import time. `ai/ingestion/{extractor,embedder}.py` do parsing/embedding.
  `ai/knowledge/knowledge_graph_builder.py` builds the KG after ingestion.

### Search agent (LangGraph)
`ai/agents/search/graph.py` compiles a `StateGraph` (state in `state.py`, nodes in
`nodes/`): `understand_query → retrieve → rerank → assemble_context → generate_answer
→ validate_answer`. On a non-grounded answer it routes through `reformulate_query` back
to `retrieve` (up to `MAX_RETRIES`). Entry point is `run_search(query, org_id, ...)`.
The `office_manager` agent is the orchestrator; `agents/{executive,finance,hr,it,legal,
operations}` are department agent stubs.

### Vector storage
Two coexisting mechanisms: legacy FAISS indices on disk (`backend/faiss_indices/`,
`backend/vector_stores_cache/session_*`) used by the legacy stack, and PostgreSQL +
pgvector for the new ingestion pipeline (`EMBEDDING_DIMENSION=1536`). Raw documents can
optionally persist to S3 when `AWS_STORAGE_ENABLED=true` (`services/aws_persistence.py`).

### Frontend (`src/`)
- Entry: `main.tsx` → `App.tsx` (routes) → `FlexiAnalyseApp.tsx` (the main authenticated
  app shell). `App1.tsx` / `FlexiAnalyseApp.tsx` contain the bulk of chat logic.
- `components/auth/AuthProvider.tsx` — Firebase auth context (`useAuth`).
- `contexts/` — `ThemeContext` and `LanguageContext` (i18n).
- `locales/{en,es,fr}/index.ts` — translation dictionaries keyed by dotted strings
  (e.g. `chat.title`). Add new UI strings to all three locales.
- `components/main/` — chat panel, file uploader/viewer, query form, sidebar, response
  rendering (markdown / structured data / PDF).
- `components/ui/` — shadcn-style primitives (`components.json`); `lib/utils.ts` has the
  `cn()` Tailwind class merge helper.
- `lib/firebase.ts` — Firebase client init.

### Auth model
Frontend authenticates with Firebase. The backend verifies Firebase tokens
(`firebase-admin`) and additionally uses JWT (`PyJWT`) in the legacy stack. Multi-tenancy
is carried through `X-User-Id` / `X-Organization-Id` headers on `/api/v2` requests.

## Deployment
`deploy_to_ec2.sh` builds the frontend and scp's `dist/` + `backend/` to an EC2 host,
serving the SPA via nginx (`nginx_flexianalyse.conf`). Production domain is
`flexianalyse.com`.

## Conventions
- Backend code, comments, docstrings, and log messages are frequently in French — match
  the surrounding language when editing a file.
- New backend features belong in the MVC layer (controller → service → repository), not
  in `legacy_ai_routes.py`; treat the legacy file as maintenance-only unless touching
  the chat/summarize flow it still serves.
- Celery tasks must keep heavy initialization lazy (inside the worker), never at module
  import time.
