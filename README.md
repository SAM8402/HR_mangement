# HR Management System

Full-stack HR management platform with AI-powered features for employee management, leave tracking, performance reviews, and intelligent document search.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop)

## Quick Start

1. Clone the repository and navigate to the project root.

2. Copy the environment file and add your Google API key:

```bash
cp .env.example .env
```

Edit `.env` and set `GOOGLE_API_KEY` to your Google Gemini API key.

3. Start all services:

```bash
docker-compose up --build
```

4. Access the application:

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Default Admin Credentials

| Field    | Value            |
|----------|------------------|
| Email    | admin@hr.com     |
| Password | admin123         |

## Services

| Service    | Port  | Description                                      |
|------------|-------|--------------------------------------------------|
| Frontend   | 3000  | Vue.js SPA served via Nginx                      |
| API        | 8000  | FastAPI backend with async Python                |
| PostgreSQL | 5432  | Primary relational database                      |
| Redis      | 6379  | Caching and session store                        |

## Modules

- **Authentication** -- JWT-based login, registration, role-based access control (admin, HR, employee)
- **Employee Management** -- Employee profiles, departments, positions, org chart
- **Leave Management** -- Leave requests, approval workflows, leave balance tracking
- **Performance Reviews** -- Review cycles, self-assessments, manager evaluations
- **AI Chatbot** -- Gemini-powered assistant for HR policy questions and document search
- **Document Search** -- ChromaDB-backed vector search across uploaded HR documents

## Stopping Services

```bash
docker-compose down
```

To remove all data (including the database volume):

```bash
docker-compose down -v
```
