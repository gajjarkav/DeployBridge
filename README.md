# DeployBridge

DeployBridge is an autonomous deployment platform designed to analyze GitHub repositories using AI and deploy applications in a single click. This repository contains both the frontend and backend components of the system.

## Current Project Scope

The project currently operates as a full-stack application with the following key capabilities:
- **GitHub Integration**: Authenticates with GitHub and retrieves repository information.
- **AI Analysis**: Uses Large Language Models (LLMs like Gemini/Groq via OpenAI-compatible endpoints) to inspect repositories and provide stack reports.
- **Automated Deployment**: Aims to bridge the gap between codebase and deployment, currently supporting GitHub Pages and Render in its ecosystem.
- **Report Generation & Delivery**: Generates analysis reports and supports sending them via email (SMTP) and storing assets via Cloudinary.

## Repository Structure

- `frontend/`: Contains the vanilla HTML, CSS (Tailwind via CDN), and JavaScript for the web interface.
- `backend/`: Contains the FastAPI-based REST backend, including database models, API routing, and third-party service integrations.
- `alembic/`: Database migration scripts.

## Tech Stack Overview

### Frontend
- HTML5 / CSS3 (TailwindCSS CDN)
- Vanilla JavaScript
- GSAP, ScrollTrigger, & Lenis for animations and smooth scrolling

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (via `asyncpg`, `SQLAlchemy 2.0+`, `alembic`)
- **Authentication**: JWT-based with `bcrypt` and `passlib`
- **Integrations**: GitHub API, LLMs (Gemini/Groq via `openai` Python client), Cloudinary, SMTP for email.
- **Task Scheduling**: `APScheduler` for background tasks.

For detailed information on how to run or configure each component, please refer to their respective documentation:
- [Frontend Documentation](./frontend/README.md)
- [Backend Documentation](./backend/README.md)