# HR Management System

Full-stack HR management platform with AI-powered features for employee management, leave tracking, attendance, work updates, and intelligent document search.

## Tech Stack

| Layer     | Technology                                                                    |
|-----------|-------------------------------------------------------------------------------|
| Frontend  | Vue 3, Pinia, Vue Router, Axios, Vite                                         |
| Backend   | FastAPI, SQLAlchemy 2.0 (async), Pydantic, LangChain, LangGraph               |
| Database  | PostgreSQL 16 (primary), SQLite (dev fallback)                                |
| Cache     | Redis 7                                                                       |
| AI        | Google Gemini 2.0 Flash, ChromaDB (vector search), BM25 (hybrid retrieval)    |
| Auth      | JWT (access + refresh tokens), bcrypt, RBAC (admin, HR, employee)             |
| Infra     | Docker Compose, Nginx                                                         |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- A [Google Gemini API key](https://aistudio.google.com/app/apikey) (for AI features)

## Quick Start (Docker)

1. Clone the repository and navigate to the project root.

2. Copy the environment file and configure your API key:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set `GOOGLE_API_KEY` to your Gemini API key.

3. Start all services:

```bash
docker compose up --build
```

4. Access the application:

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Manual Setup (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
cp .env.example .env       # Edit .env with your settings
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Default Credentials

| Role      | Email             | Password   |
|-----------|-------------------|------------|
| Admin     | admin@hr.com      | admin123   |
| HR        | (create via UI)   | —          |
| Employee  | (create via UI)   | —          |

## Services

| Service    | Port  | Description                                   |
|------------|-------|-----------------------------------------------|
| Frontend   | 3000  | Vue.js SPA served via Nginx                   |
| API        | 8000  | FastAPI backend with async Python              |
| PostgreSQL | 5432  | Primary relational database                    |
| Redis      | 6379  | Caching and session store                      |

## Architecture

```
┌──────────┐     ┌──────────┐     ┌────────────┐
│  Vue 3   │────▶│ FastAPI  │────▶│ PostgreSQL │
│ Frontend │     │ Backend  │     │     DB     │
└──────────┘     ├──────────┤     ├────────────┤
                 │  Redis   │     │  ChromaDB  │
                 │ (Cache)  │     │ (Vectors)  │
                 ├──────────┤     └────────────┘
                 │  Gemini  │
                 │   AI     │
                 └──────────┘
```

## Features

- **Authentication & RBAC** — JWT-based login with access/refresh tokens; role-based access (admin, HR, employee)
- **Employee Management** — User profiles, departments, positions, org chart
- **Leave Management** — Leave requests, approval workflows, balance tracking
- **Attendance Tracking** — Clock in/out, attendance records, overview dashboard
- **Work Updates** — Daily/weekly work logs with review capabilities
- **Company Roles & Rules** — Define and manage organizational roles and company policies
- **AI Chatbot (Aura)** — Gemini-powered conversational assistant with:
  - HR policy Q&A via RAG (ChromaDB vector search + BM25 hybrid retrieval)
  - Multi-model fallback chain for reliability
  - Chat history with session management
  - User feedback (thumbs up/down)
- **Document Search** — Upload and semantic search across HR documents (DOCX, PDF)
- **Evaluation Dashboard** — Performance review cycles and assessments

## API Endpoints

| Prefix               | Description                  |
|----------------------|------------------------------|
| `/api/auth`          | Login, register, token refresh |
| `/api/users`         | User CRUD and profile management |
| `/api/departments`   | Department management        |
| `/api/leaves`        | Leave requests and approvals |
| `/api/attendance`    | Clock in/out and records     |
| `/api/work-updates`  | Work log submissions         |
| `/api/roles`         | Company role definitions     |
| `/api/rules`         | Company policy/rules CRUD    |
| `/api/chat`          | AI chatbot conversations     |
| `/api/docs`          | Document upload and search   |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── ai/              # AI agent, embeddings, LangGraph tools
│   │   ├── core/            # Config, security, dependencies
│   │   ├── db/              # Database session and base models
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── routers/         # API route handlers
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   └── utils/           # Utility functions
│   ├── tests/               # Pytest test suite
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios API clients
│   │   ├── components/      # Reusable Vue components
│   │   ├── pages/           # Route page components
│   │   ├── stores/          # Pinia state stores
│   │   ├── composables/     # Vue composables
│   │   └── router/          # Vue Router config
│   ├── dist/                # Production build output
│   └── Dockerfile
├── Docs/                    # Sample HR documents (roles, policies)
├── demo/                    # Demo assets and documentation
└── docker-compose.yml
```

## Stopping Services

```bash
docker compose down
```

To remove all data (including the database volume):

```bash
docker compose down -v
```
