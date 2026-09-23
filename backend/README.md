# DeployBridge Backend

The backend for DeployBridge is a high-performance RESTful API built with FastAPI. It handles GitHub authentication, database persistence, AI-driven codebase analysis, and deployment orchestration.

## Current Scope & Architecture

The backend is built around a standard FastAPI directory structure and uses an async-first approach to handle database queries and external API calls efficiently.

### Key Technologies
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) with Uvicorn/uvloop.
- **Database**: PostgreSQL accessed asynchronously via `asyncpg` and `SQLAlchemy 2.0`.
- **Migrations**: `alembic` (configured in the project root).
- **Authentication**: JWT tokens, password hashing via `bcrypt` and `passlib`, and GitHub OAuth integration.
- **AI Integrations**: Uses the `openai` Python client to connect to OpenAI-compatible endpoints (currently configured for Gemini or Groq).
- **Background Tasks**: `APScheduler` for scheduled and asynchronous operations.
- **External Services**: Cloudinary for asset storage (like PDFs) and SMTP for email report delivery.

### Directory Structure
- `src/`: Main application source code.
  - `api/`: API router definitions and endpoint handlers.
  - `core/`: Core configurations, application settings (`pydantic-settings`), and lifecycle events (`lifespan`).
  - `db/`: Database connection setup and session management.
  - `models/`: SQLAlchemy ORM models representing database tables.
  - `schemas/`: Pydantic models for request validation and response serialization.
  - `services/`: Business logic, AI integration, and external service connectors.
  - `templates/`: Email or other text templates.
  - `main.py`: FastAPI application instance and entry point.
- `tests/`: Unit and integration tests (using `pytest`).
- `.env.example`: Template for required environment variables.
- `requirements.txt`: Python dependencies.
- `verify_integrations.py`: Script to check external service connectivity.

## Environment Variables

To run the backend, you must provide a `.env` file in the `backend/` directory. See `.env.example` for all required keys. Key configurations include:
- `DATABASE_URL`: Connection string for PostgreSQL.
- `GITHUB_CLIENT_ID` & `GITHUB_CLIENT_SECRET`: For GitHub OAuth integration.
- `JWT_SECRET_KEY`: For signing authentication tokens.
- `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL`: For LLM configuration (can be Gemini or Groq).
- `CLOUDINARY_*`: Credentials for Cloudinary uploads.
- `SMTP_*`: Credentials for email delivery.

## Setup & Running Locally

1. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Migrations**:
   Run Alembic migrations from the project root to set up the schema:
   ```bash
   alembic upgrade head
   ```

4. **Run the Development Server**:
   From the `backend` directory, start Uvicorn:
   ```bash
   python -m src.main
   ```
   Alternatively, run `uvicorn src.main:app --reload` directly.

The API will be available at `http://localhost:8000`. You can access the interactive Swagger documentation at `http://localhost:8000/docs`.
