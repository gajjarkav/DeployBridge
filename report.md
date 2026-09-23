<!-- ============================================================ -->
<!--  DeployBridge — Final Project Report                          -->
<!--  Generated from a full read of github.com/gajjarkav/DeployBridge -->
<!--  Page breaks are HTML divs — honoured by Typora, VS Code        -->
<!--  "Markdown PDF", Pandoc (HTML→PDF) and most MD→PDF exporters.   -->
<!-- ============================================================ -->

<div align="center">

<br><br><br>

# A PROJECT REPORT ON

<br>

# **DeployBridge**
## AI-Powered Deployment Automation Platform
### *(GitHub Pages · Render · Agentic AI Deploy Assistant)*

<br><br>

**Submitted by**

<br>

| Sr. No. | Name of Student | Enrollment No. |
|:-------:|:----------------|:---------------|
| 1 | Kavy | &nbsp; |
| 2 | Lakhan | &nbsp; |
| 3 | Anshul | &nbsp; |

<br><br>

**Under the Guidance of**

*Internal Guide Name*

<br><br>

**FACULTY OF ENGINEERING AND TECHNOLOGY**

**BACHELOR OF ENGINEERING**

in

**Computer Engineering / Information Technology**

<br>

**Noble University, Junagadh**

**Academic Year 2025 – 2026**

<br><br>

Repository: `https://github.com/gajjarkav/DeployBridge`

</div>

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  PAGE 2 — ABSTRACT                                             -->
<!-- ============================================================ -->

## ABSTRACT

Deploying a web application is still one of the most confusing steps for students and beginner developers. After writing the code and pushing it to GitHub, a developer has to understand hosting platforms, build commands, start commands, CI/CD workflow files, environment variables, DNS records and many other DevOps details before anyone can open the project in a browser.

**DeployBridge** is a web platform that removes this friction. A user signs in with GitHub, sees all of their repositories, clicks **Deploy**, and DeployBridge automatically:

1. **Inspects the repository** (root files, `package.json`, `requirements.txt`, `next.config.*`, `Gemfile`, `Dockerfile`, …) to detect what kind of project it is.
2. **Chooses the right hosting platform** — **GitHub Pages** for static sites (plain HTML, Jekyll, React/Vite/Vue/Astro builds, Next.js static export) or **Render** for server applications (Python/FastAPI/Django/Flask, Node/Express, Docker).
3. **Generates and commits the correct GitHub Actions workflow**, configures GitHub Pages, or creates a Render web service with the correct build/start commands, then **triggers the deployment**.
4. **Tracks the deployment** in its own PostgreSQL database, polls the platform for live status, downloads build logs when something fails, supports one-click redeploy and custom-domain attachment with the exact DNS records the user must add.

On top of this deterministic deployment engine, DeployBridge adds an **AI layer** built with an OpenAI-compatible LLM (Google Gemini / Groq) and a **hand-written agent loop with tool calling — no LangChain or other agent framework**:

* An **Analysis Report Agent** that explores a repository with tools (`list_file_tree`, `read_file`), writes a structured Markdown audit report, converts it to PDF, uploads it to Cloudinary and e-mails it to the user.
* A conversational **Deploy Agent** that can detect stacks, read files, read Render logs, diagnose failed deployments, and — only after an explicit **human approval step (confirm-gate)** — deploy to GitHub Pages or Render, open pull requests, or attach custom domains. Environment-variable **values never enter the LLM conversation**; only the keys do.

The backend is built with **Python 3.12, FastAPI, SQLAlchemy 2 (async), PostgreSQL, Alembic, httpx, PyJWT, Fernet encryption and APScheduler**. The frontend is a **framework-free multi-page application** written in **HTML5, CSS3 and Vanilla JavaScript** with Tailwind CSS (CDN), GSAP and Lenis for motion. The system exposes **41 REST endpoints** across 8 routers, persists **6 database tables**, ships **4 workflow templates**, and is covered by an async **pytest** suite.

This report documents the motivation, technology stack, project structure, configuration, database design, every API endpoint with its business logic, the AI/agentic layer, security design, testing approach, current scope and limitations, achievements, and future work — with system-design and system-flow diagrams drawn in Mermaid.

**Keywords:** DevOps automation, CI/CD, GitHub Pages, GitHub Actions, Render, FastAPI, Agentic AI, LLM tool calling, human-in-the-loop, OAuth 2.0, JWT, Fernet.

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  PAGE 3 — INDEX                                                -->
<!-- ============================================================ -->

## INDEX

<!-- Page numbers are intentionally left blank: fill them in after the final print layout is fixed. -->

| Sr. No. | Chapter No. | Topic Name | Page No. |
|:-------:|:-----------:|:-----------|:--------:|
| 1 | — | Title Page | |
| 2 | — | Abstract | |
| 3 | — | Index | |
| 4 | **1** | **Introduction** | |
| | 1.1 | What is DeployBridge? (in simple language) | |
| | 1.2 | The Problem it Solves | |
| | 1.3 | Objectives | |
| | 1.4 | Target Users | |
| | 1.5 | Key Features at a Glance | |
| | 1.6 | Development Timeline (Phases) | |
| | 1.7 | Project Statistics | |
| 5 | **2** | **Technology Stack** | |
| | 2.1 | Frontend Technologies | |
| | 2.2 | Backend Technologies | |
| | 2.3 | Database & Migrations | |
| | 2.4 | AI / LLM Layer | |
| | 2.5 | External Platforms & APIs | |
| | 2.6 | Testing, Tooling & DevOps | |
| | 2.7 | Complete Dependency Table | |
| 6 | **3** | **System Architecture & Design** | |
| | 3.1 | High-Level System Architecture | |
| | 3.2 | Backend Layered Architecture | |
| | 3.3 | Request Lifecycle | |
| | 3.4 | Deployment Topology | |
| | 3.5 | Design Principles | |
| 7 | **4** | **Project Structure (Tree) Explanation** | |
| | 4.1 | Root Directory | |
| | 4.2 | Backend Tree — File by File | |
| | 4.3 | Frontend Tree — File by File | |
| | 4.4 | Alembic Migrations | |
| 8 | **5** | **Environment Variables & Configuration** | |
| 9 | **6** | **Database Design** | |
| | 6.1 | ER Diagram | |
| | 6.2 | Table-wise Description | |
| | 6.3 | Migration History | |
| 10 | **7** | **API Services & Business Logic** | |
| | 7.1 | Health | |
| | 7.2 | Authentication | |
| | 7.3 | GitHub Data | |
| | 7.4 | GitHub Pages Deployment | |
| | 7.5 | Render Deployment | |
| | 7.6 | Deployments (Unified History) | |
| | 7.7 | AI Analysis Reports | |
| | 7.8 | Deploy Agent (Chat) | |
| 11 | **8** | **AI Layer — Agentic AI & Tool Calling** | |
| | 8.1 | LLM Client | |
| | 8.2 | Why a Simple Loop and not LangChain | |
| | 8.3 | Report Agent | |
| | 8.4 | Deploy Agent | |
| | 8.5 | The Confirm-Gate (Human-in-the-Loop) | |
| | 8.6 | The Secrets Rule | |
| | 8.7 | Guardrails & Cost Control | |
| 12 | **9** | **Security Design** | |
| 13 | **10** | **Frontend Application Flow** | |
| 14 | **11** | **Testing** | |
| 15 | **12** | **Current Scope, Limitations & Achievements** | |
| 16 | **13** | **Future Enhancements** | |
| 17 | **14** | **Conclusion** | |
| 18 | **15** | **References** | |
| 19 | — | Appendix A — Endpoint Quick Reference | |
| 20 | — | Appendix B — Setup & Run Guide | |
| 21 | — | Appendix C — Glossary | |

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 1                                                     -->
<!-- ============================================================ -->

# CHAPTER 1 — INTRODUCTION

## 1.1 What is DeployBridge? (in simple language)

Imagine you have just finished building a website or a small API and pushed the code to GitHub. Now you want to show it to your friends, your teacher, or a recruiter — you want a **live link**.

Normally, this means you have to:

* pick a hosting service and learn how it works,
* figure out whether your project is a "static site" or a "server app",
* write a YAML workflow file for GitHub Actions, or type the right build and start commands into a hosting dashboard,
* set up environment variables,
* wait, read confusing logs when it fails, fix, and try again,
* and, if you want your own domain, learn about CNAME and A records.

**DeployBridge is the bridge between "code on GitHub" and "live on the internet".**

You log in with your GitHub account, pick a repository, and click **Deploy**. DeployBridge looks at your code, understands what it is, decides whether it belongs on **GitHub Pages** (free static hosting) or **Render** (free tier for server apps), writes the needed configuration for you, starts the deployment and shows you the live URL. If something goes wrong, you can ask the built-in **AI Deploy Agent** in plain English — "why did my deploy fail?" — and it reads the real logs and tells you the exact line that caused the problem. It can even open a pull request with the fix, but only after you click **Approve**.

DeployBridge also has an **AI Analysis Report** feature: click one button and an AI agent explores your repository, writes a professional audit report (overview, tech stack, structure, activity, recommendations), and sends it to your e-mail as a PDF.

In one sentence: **DeployBridge is a self-hosted, AI-assisted DevOps assistant that turns a GitHub repository into a deployed application with the least possible knowledge of DevOps.**

## 1.2 The Problem it Solves

| Pain point for a beginner developer | How DeployBridge answers it |
|---|---|
| "Which platform should I use for my project?" | Automatic **stack detection** decides Pages vs Render and explains *why* (`reason` field in every detect response). |
| "I don't know how to write a GitHub Actions workflow." | Four battle-tested **workflow templates** (`html`, `jekyll`, `node-static`, `next-static`) are committed to the repo automatically, with base-path fixes, package-manager detection and lockfile fallbacks already handled. |
| "What build/start command do I put on Render?" | The Render detector proposes `pip install -r requirements.txt` + `uvicorn main:app --host 0.0.0.0 --port $PORT` (or gunicorn/Django/npm equivalents) and pre-fills a form. |
| "My deploy failed and the log is 400 lines long." | Failed deployments automatically pull the platform logs into the `error` column; the Deploy Agent quotes the root-cause line. |
| "My deployment history is scattered across dashboards." | A **unified Deployments page** with status, URL, refresh, redeploy, delete — persisted in PostgreSQL, not in the browser. |
| "How do I connect my own domain?" | Custom-domain endpoints for both platforms return the **exact DNS record** (type, name, value) and a **Verify** button that polls until HTTPS is live. |
| "Is my code well-structured? What should I improve?" | The **Report Agent** produces a 5-section audit report with recommendations, PDF + e-mail delivery. |
| "I'm scared an AI might do something destructive." | Every side-effect action goes through a **confirm-gate**; secrets never reach the model. |

## 1.3 Objectives

1. Provide **one-click deployment** of GitHub repositories to GitHub Pages and Render.
2. Implement **framework-aware detection** so the platform, profile, runtime and commands are chosen automatically and explained.
3. Persist **deployment history** and provide **live status tracking**, redeploy and log retrieval.
4. Integrate an **LLM-based agentic layer** (tool calling, planning, human approval) without relying on heavyweight agent frameworks.
5. Generate **AI repository analysis reports** with PDF, cloud storage and e-mail delivery, plus optional weekly scheduling.
6. Keep the system **secure**: GitHub OAuth, short-lived JWT sessions, Fernet-encrypted third-party tokens, per-user data isolation, and secret redaction from AI prompts.
7. Build a **clean, framework-free frontend** to demonstrate HTML/CSS/JS fundamentals while still delivering a modern UX (dark mode, animations, modals, polling).
8. Follow good engineering practice: layered architecture, Pydantic schemas, Alembic migrations, automated tests, environment-based configuration.

## 1.4 Target Users

* **Students & beginners** who want a live URL for their project without learning DevOps first.
* **Hackathon teams** who need to ship quickly.
* **Solo developers / freelancers** who deploy many small static sites and APIs.
* **Educators** who want to demonstrate CI/CD, OAuth, and AI tool-calling in a single, readable codebase.

## 1.5 Key Features at a Glance

| # | Feature | Where it lives |
|---|---|---|
| 1 | GitHub OAuth login with CSRF `state` check and JWT session | `api/v1/auth.py`, `core/security.py`, `js/auth.js` |
| 2 | Repository explorer with 9 parallel GitHub API calls (languages, commits, contributors, branches, README, tree, tech-stack, Pages status) | `services/github.py`, `js/repositories.js` |
| 3 | GitHub Pages deployment with 4 profiles + manual override + "Deploy to Render instead" recommendation | `services/github_pages.py`, `templates/github_pages/*.yml` |
| 4 | Render deployment with runtime detection (python/node/docker), env-var form, auto-deploy | `services/render.py` |
| 5 | Unified deployment history with pull-on-view refresh (8 s), redeploy, delete, log capture | `services/deployment_service.py`, `js/deployments.js` |
| 6 | Custom domains for both platforms with DNS record derivation and verification | `github_pages.py`, `render.py` |
| 7 | AI Analysis Report agent → Markdown → PDF → Cloudinary → SMTP e-mail, 10/day quota, background execution | `services/report_agent.py`, `report_job.py`, `pdf_service.py`, `storage_service.py`, `email_service.py` |
| 8 | Weekly scheduled reports (APScheduler cron) | `services/scheduler.py` |
| 9 | Conversational Deploy Agent with 11 tools, confirm-gate, persisted sessions, trace | `services/deploy_agent.py`, `js/agent.js` |
| 10 | Encrypted-at-rest GitHub tokens & Render API keys with automatic startup migration | `core/crypto.py`, `core/lifespan.py` |
| 11 | Settings: preferred deploy branch, Render connect/disconnect | `templates/settings.html` |
| 12 | Landing page, public docs, dark/light theme with View-Transition circular reveal | `index.html`, `docs.html`, `js/app-shell.js` |

## 1.6 Development Timeline (Phases)

The repository's `phases/` folder and git history (60 commits, 12 June 2026 → 21 September 2026, 3 contributors) show an incremental build:

```mermaid
timeline
    title DeployBridge development phases
    section Phase 1 (June 2026)
        Project skeleton : FastAPI app, config, logger, exceptions, lifespan
                         : health endpoint, frontend folders, SupportDocs
    section Phase 2 (June–July 2026)
        GitHub OAuth : login + callback, token exchange
                     : User table, Alembic initial migration
                     : frontend login page, localStorage session
    section Phase 3 (July–Aug 2026)
        GitHub Pages (static) : repo verification, workflow upsert
                              : Pages configuration, workflow dispatch
    section Phase 4 (Aug 2026)
        Framework-aware Pages : html / jekyll / node-static / next-static profiles
                              : detect endpoint, manual override, stale workflow cleanup
                              : deploy_branch preference
    section Phase 5 (Sept 2026)
        AI Reports : LLM client, report agent loop, PDF, Cloudinary, SMTP
                   : repo_reports table, quota, scheduler
        Render : connect / detect / deploy / services / custom domains
        Deployments : unified history, refresh, redeploy, logs
        Deploy Agent : sessions, messages, tools, confirm-gate
        Hardening : Fernet encryption, JWT-only auth, CORS, tests
```

## 1.7 Project Statistics

| Metric | Value |
|---|---|
| Total tracked files | 122 |
| Backend Python (application) | ≈ 9,990 lines across 46 modules |
| Backend tests | 9 files, 24 test functions, ≈ 370 lines |
| Alembic migrations | 9 revisions |
| Frontend JavaScript | 9 modules, ≈ 3,120 lines |
| Frontend HTML (landing + docs + 9 templates) | ≈ 15,500 lines |
| Frontend CSS | 2 files, ≈ 720 lines |
| GitHub Actions workflow templates | 4 (≈ 400 lines of YAML) |
| REST endpoints | **41** across 8 routers |
| Database tables | **6** |
| LLM agents | **2** (Report Agent, Deploy Agent) |
| Agent tools | 3 (report) + 11 (deploy: 7 read-only, 4 side-effect) |
| Git history | 60 commits, 3 contributors, 12 Jun 2026 → 21 Sep 2026 |

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 2                                                     -->
<!-- ============================================================ -->

# CHAPTER 2 — TECHNOLOGY STACK

DeployBridge is deliberately split into a **framework-free frontend** and an **async Python backend**, connected only by JSON over HTTP. Every technology below was verified from the repository (`backend/requirements.txt`, root `requirements.txt`, HTML `<script>`/`<link>` tags, and import statements).

## 2.1 Frontend Technologies

The frontend is a **Multi-Page Application (MPA)** — every screen is its own `.html` file with its own `.js` module. There is **no bundler, no npm, no React/Vue/Angular**. This was a conscious decision to keep the project transparent and to demonstrate core web fundamentals.

| Technology | Version | Role in DeployBridge |
|---|---|---|
| **HTML5** | Living standard | Semantic page structure for 11 pages (`index.html`, `docs.html`, 9 templates). Uses `<dialog>`-style overlays, `<details>` for collapsible traces, `data-*` attributes for behaviour hooks. |
| **CSS3** | Living standard | Custom properties (`--bg-color`, `--surface-color`, …) drive the light/dark theme; grid & flexbox layouts; `mask-image` gradients; `::view-transition-*` pseudo-elements; `backdrop-filter`. Files: `static/css/app.css` (app shell), `static/css/styles.css` (auth). |
| **JavaScript (Vanilla)** | ES2017+ (async/await, template literals, optional chaining `?.`, spread) | All application logic — 9 modules under `frontend/js/`. No transpilation. |
| **Fetch API** | Browser built-in | Every backend call (`fetch(\`${BACKEND_API_URL}/…\`)`) with `Authorization: Bearer <JWT>`. |
| **Web Storage API** | Browser built-in | `localStorage` for session + preferences (`db_session_token`, `gh_username`, `db_theme`, `db_sidebar_collapsed`, …); `sessionStorage` for one-shot data (`oauth_state`, `agent_prefill_question`). |
| **View Transitions API** | Browser built-in (Chromium) | `document.startViewTransition` + `clipPath: circle()` animation for the circular dark/light theme reveal (`app-shell.js`). Graceful fallback when unsupported. |
| **History API** | Browser built-in | `history.replaceState` to scrub the OAuth `?code=` from the URL after login. |
| **Clipboard API** | Browser built-in | Copy DNS records / URLs (`deployments.js`). |
| **Tailwind CSS** | v3 (Play CDN `cdn.tailwindcss.com`) | Utility classes on the landing page, docs and several templates; a custom `tailwind.config` maps `db_*` colour tokens to CSS variables and registers `Ubuntu`/`Montenegrin Gothic One` font families. |
| **GSAP** | 3.12.5 (cdnjs) | Landing-page intro timeline, pinned "How it works" card stack, features expansion. |
| **GSAP ScrollTrigger** | 3.12.5 (cdnjs) | Scroll-scrubbed pinning for landing sections. |
| **Lenis** | 1.1.18 (unpkg) | Smooth scrolling on the landing page; `lenis.scrollTo` for step buttons and back-to-top. |
| **marked.js** | latest (jsDelivr) | Markdown → HTML rendering of AI report content (`reports.html`). `repositories.js` additionally ships a small hand-written `simpleMarkdownToHtml()` fallback. |
| **Google Fonts** | — | `Ubuntu` (UI), `JetBrains Mono` (code/mono accents), `Montenegrin Gothic One` (display headings). |
| **placehold.co / GitHub identicons** | — | Avatar fallbacks. |
| **GitHub Pages** (hosting) | — | `.github/workflows/deploy-frontend-pages.yml` publishes the `frontend/` folder on every push to `main`. |

### Frontend architectural choices

* **Shared app shell** — `js/app-shell.js` is loaded by every authenticated page and provides `initializeAppShell(activePage)`: auth guard (redirect to `auth.html` if no JWT), theme + sidebar persistence, user hydration (`[data-user-name]`, `[data-user-avatar]`), logout, active-nav highlighting, and global `showCustomAlert / showCustomConfirm` promise-based dialogs (replacing native `alert/confirm`).
* **Per-page modules** — each page owns exactly one script (`overview.js`, `repositories.js`, `deployments.js`, `reports.js`, `agent.js`, `profile.js`, `settings.js`) that runs on `window.onload` / `DOMContentLoaded`.
* **Polling instead of WebSockets** — deployments auto-refresh every **8 s** while any row is `pending`/`building`; report generation is polled until `generated|delivered|failed`.

## 2.2 Backend Technologies

| Technology | Version (pinned) | Role in DeployBridge |
|---|---|---|
| **Python** | **3.12+** required | Nested double quotes inside f-strings (`services/github.py`, PEP 701) and `X \| Y` union types at runtime require 3.12. |
| **FastAPI** | 0.137.2 | Web framework: routers, dependency injection (`Depends(get_current_user)`, `Depends(get_db)`), `BackgroundTasks`, automatic OpenAPI docs at `/docs`. |
| **Starlette** | 1.3.1 | ASGI toolkit under FastAPI (CORS middleware, `Response`). |
| **Uvicorn** | 0.49.0 (+ `uvloop` 0.22.1, `httptools` 0.8.0, `watchfiles` 1.2.0, `websockets` 16.0) | ASGI server; `python -m src.main` runs `uvicorn.run("src.main:app", reload=True)`. |
| **Pydantic** | 2.13.4 (`pydantic_core` 2.46.4) | Request/response schemas in `src/schemas/`, `Literal` enums for platforms/statuses/profiles, `from_attributes` ORM mode. |
| **pydantic-settings** | 2.14.1 | `Settings(BaseSettings)` in `core/config.py` reads `backend/.env`, with `field_validator`s for blank strings, DEBUG parsing and DB URL normalisation. `@lru_cache get_settings()`. |
| **SQLAlchemy** | 2.0.51 (async, `DeclarativeBase`, `Mapped[]`) | ORM models in `src/models/`; `create_async_engine` with `pool_pre_ping`, `pool_size=5`, `max_overflow=10`, `statement_cache_size=0` (pgbouncer/Neon-safe). |
| **asyncpg** | 0.31.0 | Async PostgreSQL driver (`postgresql+asyncpg://`). |
| **psycopg2-binary** | 2.9.12 | Sync driver available for tooling (root requirements). |
| **Alembic** | 1.18.4 | Schema migrations (`alembic/`, 9 revisions), async `env.py` using `async_engine_from_config`. |
| **httpx** | 0.28.1 | Async HTTP client for GitHub, Render and Cloudinary-adjacent calls; also the ASGI test transport. |
| **PyJWT** | 2.13.0 | HS256 session tokens (`core/security.py`) with `sub/iat/exp/jti/iss` claims. |
| **cryptography (Fernet)** | 49.0.0 | Symmetric encryption of `users.github_token` and `users.render_api_key` (`core/crypto.py`). |
| **python-jose / passlib / bcrypt** | 3.5.0 / 1.7.4 / 5.0.0 | Present in requirements (auth toolbox); JWT work is done with PyJWT. |
| **openai (Python SDK)** | 3.13.0 | `AsyncOpenAI(base_url=…)` pointed at an **OpenAI-compatible** provider (Gemini or Groq). Used for Chat Completions **with `tools=`** (function calling). |
| **APScheduler** | 3.10.4 | `AsyncIOScheduler` cron job — every Monday 09:00 — generates scheduled repository reports. |
| **Markdown** | 3.10.3 | Markdown → HTML (`tables`, `fenced_code` extensions) before PDF generation. |
| **xhtml2pdf** | 0.2.18 (+ reportlab 5.0.1, pyHanko, svglib, html5lib, pypdf) | HTML → PDF for analysis reports (`services/pdf_service.py`). |
| **cloudinary** | 1.46.2 | Upload report PDFs as `resource_type="raw"` → secure URL (`services/storage_service.py`). |
| **smtplib / email.mime** | stdlib | Multipart (plain + HTML + PDF attachment) e-mail over STARTTLS (`services/email_service.py`). |
| **python-dotenv** | 1.2.2 | `.env` loading support. |
| **PyYAML** | 6.0.3 | Available for YAML handling (workflow templates are read as text). |
| **python-multipart** | 0.0.32 | Form parsing support for FastAPI. |
| **logging** | stdlib | `core/logger.py` — single stdout handler, `%(asctime)s \| %(levelname)-8s \| %(name)s \| %(message)s`. |
| **asyncio** | stdlib | `asyncio.gather` fan-out of GitHub calls, `asyncio.create_task` in the scheduler, `asyncio.sleep` retry back-off. |
| **zipfile / io / base64 / hashlib / secrets / uuid / re** | stdlib | GitHub Actions log unzip, base64 content decode/encode, token hashing for logs, OAuth `state`, UUID PKs, Next.js config regex. |

## 2.3 Database & Migrations

| Item | Detail |
|---|---|
| Engine | **PostgreSQL** (cloud-hosted friendly — the `normalize_database_url` validator rewrites `sslmode=` → `ssl=` and strips `channel_binding`, which are the parameters Neon-style connection strings carry). |
| Driver | `asyncpg` via SQLAlchemy async engine |
| PK strategy | `UUID(as_uuid=True)` with `uuid.uuid4` defaults, indexed |
| Timestamps | `DateTime(timezone=True)` with UTC defaults and `onupdate` |
| Referential integrity | All child tables `ForeignKey("users.id", ondelete="CASCADE")`; `agent_messages.session_id → agent_sessions.id CASCADE` |
| Migrations | Alembic, async env, autogenerate against `Base.metadata` (`backend.src.models` imported for discovery) |
| Test DB | SQLite in-memory via `aiosqlite` 0.22.1 (`sqlite+aiosqlite:///:memory:`) |

## 2.4 AI / LLM Layer

| Item | Detail |
|---|---|
| Access method | **OpenAI Chat Completions API shape** through the official `openai` SDK's `AsyncOpenAI` client with a custom `base_url`. |
| Default provider | **Google Gemini** — `GROQ_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`, `GROQ_MODEL=gemini-1.5-flash` (the `.env.example` also documents `gemini-2.5-flash`; the e-mail template defaults to that label). |
| Alternative provider | **Groq** — `https://api.groq.com/openai/v1`, e.g. `llama-3.1-8b-instant`. Switching providers is a **config change only**. |
| Variable naming | Variables are prefixed `GROQ_*` for historical reasons (Groq was integrated first); they are provider-agnostic. |
| Agent framework | **None.** No LangChain, LlamaIndex, CrewAI or AutoGen. Both agents are **hand-written `for step in range(MAX_STEPS)` loops** that (1) call the model with `tools=[…]`, (2) execute returned `tool_calls` in Python, (3) append `role="tool"` messages, and (4) repeat until the model answers in plain text or a plan is produced. |
| Tool schema format | OpenAI **function-calling JSON schema** (`{"type":"function","function":{"name","description","parameters"}}`). |
| Determinism | `temperature=0.2`, `max_tokens` budgeted per step. |

## 2.5 External Platforms & APIs

| Platform | API used | Purpose |
|---|---|---|
| **GitHub OAuth (web flow)** | `github.com/login/oauth/authorize`, `/access_token` | Login; scopes `read:user user:email repo workflow`. |
| **GitHub REST API v3** | `/user`, `/user/emails`, `/user/repos`, `/repos/{o}/{r}` (+ `/languages`, `/commits`, `/contributors`, `/branches`, `/readme`, `/contents/*`, `/git/trees/{sha}?recursive=1`, `/git/refs`, `/pulls`, `/pages`, `/pages/builds`, `/actions/workflows/{file}/dispatches`, `/actions/runs`, `/actions/runs/{id}/logs`) | Repo inspection, workflow upsert, Pages config, dispatch, run status, log download, PR creation, CNAME commit. |
| **GitHub Actions** | Workflow templates using `actions/checkout@v4`, `actions/configure-pages@v4`, `actions/setup-node@v4`, `actions/jekyll-build-pages@v1`, `actions/upload-pages-artifact@v3`, `actions/deploy-pages@v4` | Build & publish static sites. |
| **GitHub Pages** | Pages API + `build_type: "workflow"` | Static hosting target. |
| **Render REST API v1** | `/owners`, `/services`, `/services/{id}`, `/services/{id}/deploys`, `/services/{id}/deploys/{did}/logs`, `/services/{id}/custom-domains`, `/custom-domains/{id}/verify` | Server-app hosting target (`web_service`, region `oregon`, plan `free`). |
| **Cloudinary** | Upload API (`resource_type="raw"`) | Report PDF storage → `secure_url`. |
| **SMTP provider** (e.g. Gmail app password) | STARTTLS on port 587 | Report e-mail delivery. |
| **LLM provider** | Gemini / Groq OpenAI-compatible endpoints | Report Agent & Deploy Agent. |

## 2.6 Testing, Tooling & DevOps

| Tool | Version | Use |
|---|---|---|
| pytest | 9.1.1 | Test runner (`backend/pytest.ini` sets `pythonpath = .`). |
| pytest-asyncio | 1.4.0 | `@pytest.mark.asyncio` tests, async fixtures. |
| pytest-cov / coverage | 7.1.0 / 7.16.1 | Coverage reporting. |
| aiosqlite | 0.22.1 | In-memory async SQLite for tests. |
| httpx `ASGITransport` | 0.28.1 | In-process HTTP client against the FastAPI app. |
| unittest.mock | stdlib | Patching `GitHubService`, `RenderService`, `DeployAgentRunner`, etc. |
| Git + GitHub | — | Version control, 60 commits, PR-based collaboration. |
| GitHub Actions | — | Frontend auto-deploy to GitHub Pages on push to `main`. |
| VS Code Live Server | ports 5500/5501 | Default CORS allow-list targets these origins for local development. |
| `verify_integrations.py` | — | Smoke script checking reachability of GitHub and Render APIs. |

## 2.7 Complete Dependency Table (backend `requirements.txt`)

| Package | Version | | Package | Version |
|---|---|---|---|---|
| alembic | 1.18.4 | | pydantic | 2.13.4 |
| annotated-doc | 0.0.4 | | pydantic-settings | 2.14.1 |
| annotated-types | 0.7.0 | | pydantic_core | 2.46.4 |
| anyio | 4.14.0 | | PyJWT | 2.13.0 |
| APScheduler | 3.10.4 | | python-dotenv | 1.2.2 |
| asyncpg | 0.31.0 | | python-jose | 3.5.0 |
| bcrypt | 5.0.0 | | python-multipart | 0.0.32 |
| certifi | 2026.6.17 | | PyYAML | 6.0.3 |
| cffi | 2.0.0 | | rsa | 4.9.1 |
| click | 8.4.1 | | six | 1.17.0 |
| cryptography | 49.0.0 | | SQLAlchemy | 2.0.51 |
| ecdsa | 0.19.2 | | starlette | 1.3.1 |
| fastapi | 0.137.2 | | typing-inspection | 0.4.2 |
| greenlet | 3.5.2 | | typing_extensions | 4.15.0 |
| h11 | 0.16.0 | | uvicorn | 0.49.0 |
| httpcore | 1.0.9 | | uvloop | 0.22.1 |
| httptools | 0.8.0 | | watchfiles | 1.2.0 |
| httpx | 0.28.1 | | websockets | 16.0 |
| idna | 3.18 | | openai | 3.13.0 |
| Mako | 1.3.12 | | passlib | 1.7.4 |
| MarkupSafe | 3.0.3 | | pyasn1 / pycparser | 0.6.3 / 3.0 |

Additional packages pinned in the **root** `requirements.txt` (report pipeline, testing): `Markdown 3.10.3`, `xhtml2pdf 0.2.18`, `reportlab 5.0.1`, `pyHanko 0.37.0`, `svglib 2.2.0`, `pypdf 6.18.1`, `pillow 12.3.0`, `cloudinary 1.46.2`, `aiohttp 3.14.3`, `aiosqlite 0.22.1`, `psycopg2-binary 2.9.12`, `pytest 9.1.1`, `pytest-asyncio 1.4.0`, `pytest-cov 7.1.0`, `coverage 7.16.1`, `tzlocal 5.4.4`, `pytz 2026.3.post1`.

<div style="page-break-after: always;"></div>
<!-- ============================================================ -->
<!--  CHAPTER 3                                                     -->
<!-- ============================================================ -->

# CHAPTER 3 — SYSTEM ARCHITECTURE & DESIGN

## 3.1 High-Level System Architecture

DeployBridge is a **three-tier system** (browser → FastAPI backend → PostgreSQL) that orchestrates **five external platforms** (GitHub, Render, an LLM provider, Cloudinary, SMTP). The backend is the *only* component that holds secrets; the browser holds only a short-lived session JWT.

```mermaid
flowchart TB
    subgraph CLIENT["Browser — Frontend (Vanilla JS MPA, served by GitHub Pages or Live Server)"]
        LP["index.html / docs.html<br/>Landing & Public Docs"]
        AUTH["auth.html + auth.js<br/>GitHub OAuth"]
        SHELL["app-shell.js<br/>auth guard · theme · sidebar · dialogs"]
        PAGES["dashboard · repositories · deployments<br/>reports · agent · profile · settings"]
        LS[("localStorage<br/>db_session_token, prefs")]
        AUTH --> LS
        SHELL --> LS
        PAGES --> SHELL
    end

    subgraph BACKEND["FastAPI Backend (Uvicorn, Python 3.12, async)"]
        MW["CORS Middleware<br/>Lifespan: Fernet check, token migration, scheduler"]
        ROUTER["/v1 API Router (41 endpoints)"]
        DEP["Dependencies<br/>get_current_user (JWT) · get_db (AsyncSession)"]
        subgraph SERVICES["Service Layer"]
            GH["GitHubService"]
            GP["GitHubPagesService"]
            RS["RenderService"]
            DS["DeploymentService"]
            RA["Report Agent + ReportService"]
            DA["DeployAgentRunner"]
            LLMC["GroqLLMClient (OpenAI SDK)"]
            PDF["PDFService"]
            STO["StorageService"]
            MAIL["EmailService"]
            SCH["APScheduler"]
        end
        CORE["Core: config · security (JWT) · crypto (Fernet) · logger · exceptions"]
        MW --> ROUTER --> DEP --> SERVICES
        SERVICES --> CORE
    end

    subgraph DATA["Persistence"]
        PG[("PostgreSQL<br/>users · repositories · repo_reports<br/>deployments · agent_sessions · agent_messages")]
    end

    subgraph EXT["External Platforms"]
        GHAPI["GitHub REST API + OAuth<br/>Actions · Pages · Contents · PRs"]
        RENDER["Render REST API v1"]
        LLM["LLM Provider<br/>Gemini / Groq (OpenAI-compatible)"]
        CLD["Cloudinary"]
        SMTP["SMTP Server"]
    end

    PAGES -- "fetch() JSON + Bearer JWT" --> MW
    AUTH -- "/auth/login, /auth/callback" --> MW
    DEP --> PG
    DS --> PG
    RA --> PG
    DA --> PG
    SCH --> PG
    GH --> GHAPI
    GP --> GHAPI
    RS --> RENDER
    RA --> LLMC
    DA --> LLMC
    RS -. "Django folder guess" .-> LLMC
    LLMC --> LLM
    STO --> CLD
    MAIL --> SMTP
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| **Frontend MPA** | Presentation, OAuth redirect handling, storing the JWT, calling the API, polling, rendering plan cards / DNS cards / report modals. Never talks to GitHub or Render directly except when GitHub's OAuth page redirects the browser. |
| **API routers** (`src/api/v1/*`) | Thin HTTP layer: parse/validate with Pydantic, resolve the user, call a service, map domain exceptions → `HTTPException`. |
| **Dependencies** | `get_current_user` (Bearer JWT → `User` row) and `get_db` (one `AsyncSession` per request with commit/rollback). |
| **Services** | All business logic and all outbound HTTP. Stateless classmethods that receive already-decrypted tokens. |
| **Core** | Settings, JWT mint/verify, Fernet encrypt/decrypt, logging, exception hierarchy, startup/shutdown hooks. |
| **Models / Schemas** | SQLAlchemy ORM tables vs Pydantic wire contracts — kept strictly separate. |
| **PostgreSQL** | System of record for users, deployments, reports, agent conversations. |

## 3.2 Backend Layered Architecture

```mermaid
flowchart LR
    subgraph L1["Layer 1 — Transport"]
        A1["main.py<br/>FastAPI app + CORS + lifespan"]
        A2["api/router.py<br/>prefix /v1, tags"]
    end
    subgraph L2["Layer 2 — Endpoints (api/v1)"]
        B1["health.py"]
        B2["auth.py"]
        B3["github.py"]
        B4["github_pages.py"]
        B5["render.py"]
        B6["deployments.py"]
        B7["reports.py"]
        B8["agent.py"]
    end
    subgraph L3["Layer 3 — Cross-cutting"]
        C1["api/dependencies.py<br/>get_current_user"]
        C2["db/session.py<br/>engine, get_db, Base"]
        C3["schemas/*<br/>Pydantic contracts"]
        C4["core/*<br/>config · security · crypto · logger · exception"]
    end
    subgraph L4["Layer 4 — Services (business logic)"]
        D1["github.py"]
        D2["github_pages.py"]
        D3["render.py"]
        D4["deployment_service.py"]
        D5["report_service.py · report_agent.py · report_job.py"]
        D6["deploy_agent.py"]
        D7["llm_client.py"]
        D8["pdf_service.py · storage_service.py · email_service.py"]
        D9["scheduler.py"]
    end
    subgraph L5["Layer 5 — Data"]
        E1["models/*<br/>User · Repository · RepoReport<br/>Deployment · AgentSession · AgentMessage"]
        E2[("PostgreSQL")]
        E3["templates/github_pages/*.yml"]
    end
    A1 --> A2 --> L2
    L2 --> C1 & C2 & C3 & C4
    L2 --> L4
    L4 --> C4
    L4 --> E1 --> E2
    D2 --> E3
    D3 --> D2
    D4 --> D1 & D2 & D3
    D5 --> D1 & D7 & D8
    D6 --> D1 & D2 & D3 & D4 & D7
    D9 --> D5
```

**Rule of thumb used throughout the codebase:** *endpoints decrypt tokens and translate errors; services never touch the DB session for auth and never see ciphertext.* (`RenderService` and `GitHubPagesService` take the plaintext key as their first argument; `DeploymentService` is the one service that receives `db` because it owns the `deployments` rows.)

## 3.3 Request Lifecycle (authenticated endpoint)

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser (page.js)
    participant M as CORSMiddleware
    participant R as Router /v1/...
    participant D as get_current_user
    participant S as get_db (AsyncSession)
    participant SV as Service
    participant X as External API
    participant PG as PostgreSQL

    B->>M: fetch(url, {Authorization: Bearer <JWT>})
    M->>R: route match + Pydantic body validation
    R->>D: Depends(get_current_user)
    D->>D: _extract_bearer_token → decode_session_jwt (HS256, iss, exp, jti)
    D->>PG: SELECT users WHERE id = sub
    PG-->>D: User row (or 401)
    R->>R: decrypt_secret(user.github_token / render_api_key)
    R->>SV: call service with plaintext token + validated args
    SV->>X: httpx request(s)
    X-->>SV: JSON
    SV->>PG: (optional) write rows via db
    SV-->>R: Pydantic response model / domain exception
    alt domain exception (GitHubPagesError / RenderError / TokenDecryptionError)
        R-->>B: HTTPException(exc.status_code, exc.detail)
    else success
        S->>PG: COMMIT (get_db exit)
        R-->>B: 200 JSON
    end
```

## 3.4 Deployment Topology

```mermaid
flowchart LR
    subgraph DEV["Developer machine / VM"]
        UV["uvicorn src.main:app<br/>0.0.0.0:8000 (reload)"]
        ENV[".env (secrets)"]
        UV --- ENV
    end
    subgraph GHP["GitHub Pages (frontend hosting)"]
        FE["frontend/ folder published by<br/>deploy-frontend-pages.yml on push to main"]
    end
    subgraph LOCAL["Local dev alternative"]
        LSV["VS Code Live Server<br/>127.0.0.1:5500 / 5501"]
    end
    subgraph CLOUD["Managed services"]
        NEON[("PostgreSQL<br/>(Neon-style URL with ssl)")]
        GEM["Gemini / Groq"]
        CL["Cloudinary"]
        SM["SMTP"]
    end
    subgraph TARGETS["Deployment targets controlled on behalf of the user"]
        GHA["GitHub Actions runners"]
        GPAGES["GitHub Pages sites<br/>https://owner.github.io/repo"]
        RSVC["Render web services<br/>https://name.onrender.com"]
    end
    USER((User)) --> FE
    USER --> LSV
    FE -- "CORS-allowed origin" --> UV
    LSV --> UV
    UV --> NEON
    UV --> GEM
    UV --> CL
    UV --> SM
    UV -- "workflow_dispatch" --> GHA --> GPAGES
    UV -- "POST /v1/services" --> RSVC
```

> **Note:** The frontend currently points at `http://127.0.0.1:8000/v1` (hard-coded `BACKEND_API_URL`). The published GitHub Pages copy therefore works only when the backend is running locally on the visitor's machine, or the constant is changed to a public backend URL and that origin is added to `CORS_ALLOWED_ORIGINS`. See Chapter 12.

## 3.5 Design Principles

1. **"The LLM decides WHAT, Python decides HOW."** The model only chooses tools and arguments; every real action is executed by deterministic, already-tested service code.
2. **One user action = one atomic operation.** Deploy endpoints write the `deployments` row *after* the platform accepts the request, in the same DB transaction — no separate "create deployment" endpoint, no orphan rows.
3. **Pull-on-view, zero background infrastructure for status.** The frontend asks `/refresh` while the page is open; terminal rows (`live`/`failed`) are never re-polled.
4. **Same inspection code for both platforms.** `GitHubPagesService.build_repository_context()` feeds both the Pages profile detector and the Render runtime detector, so the two never disagree about what a repo is.
5. **Secrets stay server-side and encrypted.** Fernet at rest, decrypted only in memory for the duration of a request, never logged (only truncated SHA-256 hashes appear in logs).
6. **Fail loudly with actionable messages.** Every `GitHubAPIError`/`RenderError` carries a human-readable `detail` telling the user *what to do* (re-login, add `output: 'export'`, delete an unused Render service, …).
7. **Consistency = predictability.** Pagination (`page`, `page_size`, `total`, `items`) and the try/except pattern are identical across reports, deployments and agent sessions.

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 4                                                     -->
<!-- ============================================================ -->

# CHAPTER 4 — PROJECT STRUCTURE (TREE) EXPLANATION

## 4.1 Root Directory

```text
DeployBridge/
├── .github/
│   └── workflows/
│       └── deploy-frontend-pages.yml   # CI: publish frontend/ to GitHub Pages on push to main
├── alembic/                            # Database migration environment (async)
│   ├── env.py                          # Loads Settings.DATABASE_URL, imports models, runs async migrations
│   ├── README
│   ├── script.py.mako                  # Template for new revision files
│   └── versions/                       # 9 revision files (see §4.4)
├── alembic.ini                         # Alembic config (script_location = ./alembic)
├── backend/                            # FastAPI application (see §4.2)
├── frontend/                           # Vanilla JS multi-page app (see §4.3)
├── phases/
│   ├── 1.md  2.md  3.md  4.md          # Phase-wise progress reports written during development
├── SupportDocs/                        # College report templates (Title, Certificate, Ack, Index, Chapters, Weekly report)
├── belt_svgs.html                      # Scratch file: SVG icon "belt" markup used on the landing page
├── requirements.txt                    # Full dev environment freeze (backend + report pipeline + tests)
├── .gitignore
└── README.md                           # Currently a one-line title
```

| Path | Why it exists |
|---|---|
| `.github/workflows/deploy-frontend-pages.yml` | DeployBridge "eats its own dog food": the same `configure-pages → upload-pages-artifact → deploy-pages` pattern it generates for users is used to host its own frontend. |
| `alembic/` + `alembic.ini` at the **root** (not inside `backend/`) | `env.py` imports `backend.src.core.config` and `backend.src.models`, so Alembic must run from the repository root (`alembic upgrade head`). |
| `phases/*.md` | Living documentation of what was built in each academic phase; useful for weekly progress reports. |
| Two `requirements.txt` files | `backend/requirements.txt` = minimal runtime set for the API; root `requirements.txt` = complete freeze including PDF/Cloudinary/testing packages and two local editable packages (`deploybridge_tree`, `deploybridgetree`) that were experiments and are not part of the app. |

## 4.2 Backend Tree — File by File

```text
backend/
├── .env.example            # Documented template of every environment variable
├── .gitignore
├── README.md               # (empty placeholder)
├── pytest.ini              # pythonpath = .  → tests import `src.*`
├── requirements.txt
├── verify_integrations.py  # Smoke script: can we reach api.github.com and api.render.com?
├── src/
│   ├── __init__.py
│   ├── main.py             # get_app(): FastAPI(title, version, docs_url, lifespan) + CORS + include api_router
│   ├── api/
│   │   ├── router.py       # api_router = APIRouter(prefix="/v1"); includes 8 sub-routers with tags
│   │   ├── dependencies.py # get_current_user(): Bearer → JWT → User row; 401 with WWW-Authenticate
│   │   └── v1/
│   │       ├── health.py        # GET /health
│   │       ├── auth.py          # login, callback, profile GET/PATCH, refresh, logout
│   │       ├── github.py        # repos/info, user, user/repos proxies
│   │       ├── github_pages.py  # detect, deploy, custom-domains add/verify
│   │       ├── render.py        # connect/disconnect/status, detect, deploy, services, redeploy, custom-domain
│   │       ├── deployments.py   # list, detail, refresh, redeploy, delete
│   │       ├── reports.py       # generate (202), history, detail, delete, send-email, pdf
│   │       └── agent.py         # sessions CRUD, messages (run loop), approve
│   ├── core/
│   │   ├── config.py       # Settings(BaseSettings) + validators + get_settings() lru_cache
│   │   ├── constants.py    # MIN_TOKEN_LENGTH, FERNET_TOKEN_PREFIX="gAAAA"
│   │   ├── crypto.py       # get_fernet(), is_encrypted(), encrypt_secret(), decrypt_secret(), TokenDecryptionError
│   │   ├── enums.py        # Environment(str, Enum): production | local
│   │   ├── exception.py    # DeployBridgeError → ConfigGenerationError, GitHubPagesError → RepositoryNotFoundError, GitHubAPIError; RenderError
│   │   ├── lifespan.py     # startup: validate Fernet key, encrypt legacy plaintext tokens, start scheduler; shutdown: stop scheduler
│   │   ├── logger.py       # get_logger(): stdout handler, LOG_LEVEL from settings
│   │   └── security.py     # create_session_jwt(user_id), decode_session_jwt(token)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py         # (empty — Base lives in session.py)
│   │   └── session.py      # engine, AsyncSessionLocal, Base(DeclarativeBase), get_db()
│   ├── models/
│   │   ├── __init__.py     # re-exports all models (needed by Alembic autogenerate)
│   │   ├── user.py         # users
│   │   ├── repository.py   # repositories (scheduled-report flags)
│   │   ├── repo_report.py  # repo_reports
│   │   ├── deployment.py   # deployments
│   │   └── agent_session.py# agent_sessions + agent_messages
│   ├── schemas/
│   │   ├── user.py         # UserProfileResponse, UserDeployBranchUpdate
│   │   ├── repo_info.py    # 17 models: RepoBasicInfo, LanguageInfo, TechStackInfo, CommitsInfo, … RepositoryInfoResponse
│   │   ├── github_pages.py # DeploymentProfile literals, Detect/Deploy/CustomDomain request+response
│   │   ├── render.py       # RenderRuntime/RenderPlan literals, Connect/Status/Detect/Deploy/Service/Redeploy/CustomDomain
│   │   ├── deployment.py   # DeploymentPlatform/Status literals, Item/List/Refresh/Redeploy/Delete
│   │   ├── reports.py      # Generate/History/Detail/Delete
│   │   └── agent.py        # Session/Message/Send/Approve request+response
│   ├── services/
│   │   ├── github.py            # 1006 lines — OAuth exchange, profile, parallel repo info, tech-stack heuristics,
│   │   │                        #   recursive tree, read file, create branch+file+PR, workflow run status, log unzip
│   │   ├── github_pages.py      # 1363 lines — RepositoryContext, profile detection, Render recommendation,
│   │   │                        #   workflow upsert/cleanup, Pages config, dispatch (retry), CNAME custom domains
│   │   ├── render.py            # 933 lines — Render API facade: owners, services, deploys, logs, custom domains,
│   │   │                        #   runtime detection (with LLM-assisted Django folder guess)
│   │   ├── deployment_service.py# 529 lines — deployments rows: create_from_*_deploy, list, get, refresh, redeploy
│   │   ├── llm_client.py        # 117 lines — GroqLLMClient(AsyncOpenAI) .chat_completion(messages, tools)
│   │   ├── report_service.py    # 228 lines — v0 single-shot report + _summarize_repo_info() context builder
│   │   ├── report_agent.py      # 305 lines — tool-calling agent loop (list_file_tree, read_file, create_pull_request)
│   │   ├── report_job.py        # 110 lines — background pipeline: generating → generated → delivering → delivered
│   │   ├── deploy_agent.py      # 1076 lines — DeployAgentRunner: 11 tools, confirm-gate, message replay, trace
│   │   ├── pdf_service.py       # Markdown → styled HTML → PDF (xhtml2pdf)
│   │   ├── storage_service.py   # Cloudinary raw upload
│   │   ├── email_service.py     # 359 lines — HTML "bento" template + plain text + PDF attachment via SMTP
│   │   └── scheduler.py         # APScheduler cron (Mon 09:00) → run_report_job for is_scheduled repos
│   └── templates/
│       └── github_pages/
│           ├── html.yml         # upload "." → deploy-pages
│           ├── jekyll.yml       # jekyll-build-pages → _site → deploy-pages
│           ├── node-static.yml  # pnpm/yarn/npm detection, base-path injection, build, artifact path discovery, asset path normalisation
│           └── next-static.yml  # same as node-static but Next.js-aware (NEXT_PUBLIC_BASE_PATH, `out/`)
└── tests/
    ├── conftest.py         # in-memory SQLite engine, get_db override, ASGI client, test_user, auth_headers
    └── api/
        ├── test_health.py  test_auth.py  test_github.py  test_github_pages.py
        ├── test_render.py  test_deployments.py  test_reports.py  test_agent.py
```

### 4.2.1 Entry & wiring

* **`main.py`** — builds the app from settings (`APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`, `DOCS_URL`, `REDOC_URL`), splits `CORS_ALLOWED_ORIGINS` by comma, attaches `CORSMiddleware` (`allow_credentials=True`, all methods/headers), includes `api_router`. Running the module directly starts Uvicorn with reload.
* **`api/router.py`** — one place that defines the public URL space:

| Prefix | Router | OpenAPI tag |
|---|---|---|
| `/v1/health` | health | Health |
| `/v1/auth` | auth | Authentication |
| `/v1/github` | github | GitHub Data |
| `/v1/github-pages` | github_pages | GitHub Pages |
| `/v1/reports` | reports | Reports |
| `/v1/render` | render | Render |
| `/v1/deployments` | deployments | Deployment |
| `/v1/agent` | agent | Deploy Agent |

* **`api/dependencies.py`** — `get_current_user` is the single authentication gate. It parses `Authorization: Bearer …`, verifies the JWT (`decode_session_jwt` enforces algorithm, issuer and required claims), loads the `User`, and raises `401` with an RFC-6750 `WWW-Authenticate` header on any failure. Tokens are never logged; a 12-char SHA-256 prefix is logged instead.

### 4.2.2 Core

* **`config.py`** — see Chapter 5 for every field. Notable validators: `DEBUG` accepts `prod/release/dev/debug/on/off/yes/no`; blank strings for optional settings become `None`; blank `PORT` → 8000; `DATABASE_URL` is normalised for asyncpg.
* **`security.py`** — JWT payload `{sub, iat, exp, jti, iss:"DeployBridge"}`; `exp = now + ACCESS_TOKEN_EXPIRE_MINUTES`.
* **`crypto.py`** — Fernet wrapper with three-way decrypt (empty → passthrough, plaintext → passthrough + WARNING, ciphertext → decrypt or `TokenDecryptionError`). `get_fernet()` is `lru_cache`d and called eagerly at boot so a malformed key fails startup rather than the first request.
* **`lifespan.py`** — boot sequence: log banner → `get_fernet()` → `_encrypt_existing_github_tokens()` (idempotent one-time migration of plaintext rows) → `start_scheduler()`; shutdown → `stop_scheduler()`.
* **`exception.py`** — domain exceptions carry `message`, `detail`, `status_code` so endpoints can do `raise HTTPException(exc.status_code, exc.detail or exc.message)` uniformly.

### 4.2.3 Data access

* **`db/session.py`** — async engine (`pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`, `statement_cache_size=0` for pooled Postgres), `AsyncSessionLocal(expire_on_commit=False, autoflush=False)`, `Base`, and `get_db()` which **commits on success and rolls back on exception** — endpoints therefore usually only `flush()`.
* **`models/`** — six tables, documented in Chapter 6.
* **`schemas/`** — Pydantic v2 models with `Literal` unions used as lightweight enums (`DeploymentStatus = Literal["pending","building","live","failed"]`, `RenderRuntime = Literal["python","node","docker"]`, `DeploymentProfile = Literal["auto","html","jekyll","node-static","next-static"]`).

### 4.2.4 Services (the heart of the backend)

Each service is a class of `@classmethod`s (stateless) except `DeployAgentRunner`, which is instantiated per user message because it carries conversation state and a trace list.

| Service | Key public methods | Talks to |
|---|---|---|
| `GitHubService` | `get_access_token`, `get_user_profile`, `get_repository_info` (1 + 8 parallel calls), `detect_tech_stack_simple`, `list_file_tree_recursive`, `read_file_content` (30 KB cap), `create_file_and_pull_request`, `get_workflow_run_status`, `get_workflow_run_logs` (zip → text, 30 KB cap) | GitHub |
| `GitHubPagesService` | `detect`, `build_repository_context`, `detect_render_recommendation`, `deploy`, `add_custom_domain`, `verify_custom_domain`; private `_detect_profile`, `_validate_profile_override`, `_remove_other_workflows`, `_upsert_workflow`, `_configure_pages`, `_dispatch_workflow`, DNS helpers | GitHub |
| `RenderService` | `validate_key_and_resolve_owner`, `detect`, `create_web_service`, `trigger_deploy`, `list_services`, `get_service`, `add_custom_domain`, `verify_custom_domain`, `get_deploy_logs`; `_raise_for` error mapper | Render (+ LLM for Django guess) |
| `DeploymentService` | `create_from_pages_deploy`, `create_from_render_deploy`, `list_for_user`, `get_one`, `refresh` (+ `_refresh_render`, `_refresh_pages`), `redeploy` (+ `_redeploy_render`, `_redeploy_pages`) | DB, GitHub, Render |
| `GroqLLMClient` | `chat_completion(messages, temperature, max_tokens, tools)` → `{content, model, prompt_tokens, completion_tokens, tool_calls, raw_message}` | LLM |
| `ReportService` | `_summarize_repo_info` (context builder), `generate_report` (v0 single call, kept for reference) | LLM |
| `report_agent.run_agent_loop` | multi-step tool loop → markdown + trace | GitHub, LLM |
| `report_job.run_report_job` | background orchestration + status updates | DB, PDF, Cloudinary, SMTP |
| `DeployAgentRunner` | `run_user_message`, `resume_after_approval`, `_run_loop`, `_execute_readonly_tool`, `_execute_sideeffect_tool` | everything above |
| `PDFService` / `StorageService` / `EmailService` | `generate_pdf_from_markdown`, `upload_pdf`, `send_report_email` | local, Cloudinary, SMTP |
| `scheduler` | `start_scheduler`, `stop_scheduler`, `generate_scheduled_reports` | DB |

### 4.2.5 Workflow templates

All four templates share: trigger on `push` to `__DEFAULT_BRANCH__` (substituted at upsert time) **and** `workflow_dispatch`; `permissions: contents:read, pages:write, id-token:write`; `concurrency: group: pages`; final `actions/deploy-pages@v4` step with the `github-pages` environment. The Node/Next templates additionally: detect the package manager from lockfiles (pnpm → yarn → npm ci → npm install, with fallback when `npm ci` fails on an out-of-sync lockfile), compute the Pages base path `/<repo>/`, inject `--base` (Vite) / `--base-href` (Angular) / `PUBLIC_URL` / `NEXT_PUBLIC_BASE_PATH`, enable `--openssl-legacy-provider` for CRA/webpack 4, discover the artifact directory (`dist`, `build`, `out`, `public`, `.output/public`, `.vitepress/dist`, `dist/<pkg>/browser`), and rewrite root-relative asset paths so the site works under a sub-path.

## 4.3 Frontend Tree — File by File

```text
frontend/
├── README.md                 # (empty placeholder)
├── index.html                # Public landing page (2037 lines): intro animation, hero, how-it-works, features, CTA
├── docs.html                 # Public documentation page (1367 lines): 4-step guide, supported profiles
├── js/
│   ├── app-shell.js          # Shared shell (348 lines) — see below
│   ├── auth.js               # GitHub OAuth start + callback handling (95 lines)
│   ├── overview.js           # Dashboard metrics (repos, public/private, deployments) + fresh activity (89 lines)
│   ├── repositories.js       # Repo table, repo-info modal (10 sections), AI report trigger + polling (1169 lines)
│   ├── deployments.js        # Deployment table, filters, refresh/redeploy/delete, 8-s auto-refresh,
│   │                         #   inspect modal, Ask-Agent handoff, Render custom-domain claim/verify (614 lines)
│   ├── reports.js            # Report history pagination, detail modal (marked.js), PDF download, resend e-mail (219 lines)
│   ├── agent.js              # Chat UI: sessions, send message, plan cards, env-var form, approve/cancel, trace (462 lines)
│   ├── profile.js            # GitHub profile card via /v1/github/user proxy (116 lines)
│   └── settings.js           # Minimal page boot (10 lines); heavy logic is inline in settings.html
├── static/
│   ├── assets/test.jpg
│   └── css/
│       ├── app.css           # App-shell layout: sidebar, topbar, cards, tables, badges, modals, dark theme (662 lines)
│       └── styles.css        # Auth page styles (58 lines)
└── templates/
    ├── auth.html             # "Sign in with GitHub" screen
    ├── dashboard.html        # Overview: metric cards, recent deployments, fresh activity
    ├── repositories.html     # Repository list + Deploy buttons (Pages / Render) + info modal + AI report section
    ├── deployments.html      # Unified deployment history
    ├── reports.html          # AI report history + viewer
    ├── agent.html            # Deploy Agent chat
    ├── profile.html          # GitHub profile details
    ├── settings.html         # Deploy branch preference, Render connect/disconnect, theme, session
    └── docs.html             # In-app copy of the docs
```

### 4.3.1 `app-shell.js` — the glue

| Function | Purpose |
|---|---|
| `getAuthSession()` | Reads the 8 session keys from `localStorage` into one object. |
| `requireAuthSession()` | Redirects to `auth.html` when `db_session_token` is missing. |
| `initializeAppShell(activePage)` | Runs the whole boot: theme, sidebar, user hydration, theme/sidebar/logout bindings, active nav. Returns the session. |
| `applySavedTheme()` / `bindThemeButton()` | Persists `db_theme`; animates the switch with the View Transitions API (`circle()` clip-path from the click point). |
| `applySavedSidebarState()` / `bindSidebarButtons()` | Persists `db_sidebar_collapsed`; toggles `#appShell.collapsed`. |
| `hydrateUser(session)` | Fills every `[data-user-name]` / `[data-user-avatar]`. |
| `logoutUser()` | Clears all session keys → `auth.html` (backend `/auth/logout` is a no-op today). |
| `rememberDeployment()` / `readRecentDeployments()` | Legacy localStorage cache (`deploybridge_recent_deployments`) still used by the dashboard metric card. |
| `showCustomAlert()` / `showCustomConfirm()` | Promise-based themed dialogs injected on demand (`ensureCustomDialogDOM`). |

### 4.3.2 Page → API mapping

| Page | JS | Backend endpoints used |
|---|---|---|
| `auth.html` | `auth.js` | `GET /auth/login`, `GET /auth/callback?code=` |
| `dashboard.html` | `overview.js` + inline | `GET /github/user`, `GET /github/user/repos?sort=updated&per_page=50` |
| `repositories.html` | `repositories.js` + inline | `GET /github/user`, `GET /github/user/repos`, `POST /github/repos/info`, `POST /github-pages/detect`, `POST /github-pages/deploy`, `POST /render/detect`, `POST /render/deploy`, `POST /reports/generate`, `GET /reports/{id}` (poll) |
| `deployments.html` | `deployments.js` | `GET /deployments`, `POST /deployments/{id}/refresh`, `POST /deployments/{id}/redeploy`, `DELETE /deployments/{id}`, `POST /render/services/{sid}/custom-domain`, `POST /render/services/{sid}/custom-domain/{d}/verify` |
| `reports.html` | `reports.js` | `GET /reports/history`, `GET /reports/{id}`, `DELETE /reports/{id}`, `GET /reports/{id}/pdf`, `POST /reports/{id}/send-email` |
| `agent.html` | `agent.js` | `POST/GET /agent/sessions`, `GET /agent/sessions/{id}`, `POST /agent/sessions/{id}/messages`, `POST /agent/messages/{id}/approve` |
| `profile.html` | `profile.js` | `GET /github/user` |
| `settings.html` | `settings.js` + inline | `GET/PATCH /auth/profile`, `GET /github/user`, `GET /render/status`, `POST /render/connect`, `DELETE /render/connect` |

## 4.4 Alembic Migrations

```mermaid
flowchart LR
    M1["61fec428af4e<br/>2026-06-20<br/>initial users table"] --> M2["9f3021b89fdf<br/>2026-07-05<br/>github_token, token_type, scope"]
    M2 --> M3["62cad5c4cb44<br/>2026-08-15<br/>users.deploy_branch"]
    M3 --> M4["95780adea624<br/>2026-09-12<br/>repo_reports table"]
    M4 --> M5["471657679a4a<br/>2026-09-12<br/>repositories table"]
    M5 --> M6["dad6b157e666<br/>2026-09-17<br/>render_api_key, render_owner_id"]
    M6 --> M7["7f09806a3b0b<br/>2026-09-17<br/>widen render_api_key (ciphertext)"]
    M7 --> M8["9f8ae6414de0<br/>2026-09-19<br/>deployments + agent tables"]
    M8 --> M9["dece5564cf24<br/>2026-09-19<br/>deployments table (head)"]
```

`alembic/env.py` reads `Settings.DATABASE_URL`, sets `target_metadata = Base.metadata`, and runs migrations through an async engine (`connection.run_sync(do_run_migrations)`). New schema changes are produced with `alembic revision --autogenerate -m "…"` from the repository root and applied with `alembic upgrade head`.

<div style="page-break-after: always;"></div>
<!-- ============================================================ -->
<!--  CHAPTER 5                                                     -->
<!-- ============================================================ -->

# CHAPTER 5 — ENVIRONMENT VARIABLES & CONFIGURATION

All configuration is centralised in `backend/src/core/config.py` (`class Settings(BaseSettings)`). Values are read from **`backend/.env`** (path computed as `BASE_DIR / "backend" / ".env"`, where `BASE_DIR` is the repository root), then from real environment variables; matching is **case-insensitive** and unknown keys are ignored (`extra="ignore"`). `get_settings()` is wrapped in `@lru_cache` so the file is parsed once per process.

## 5.1 How configuration is loaded

```mermaid
flowchart LR
    ENVF["backend/.env"] --> PS["pydantic-settings<br/>Settings()"]
    OSENV["OS environment"] --> PS
    PS --> V1["field_validator DEBUG<br/>prod/release/false/0/off/no → False<br/>dev/debug/true/1/on/yes → True"]
    PS --> V2["field_validator blank → None<br/>DOCS_URL, REDOC_URL, HOST, LOG_LEVEL, GROQ_API_KEY"]
    PS --> V3["field_validator PORT<br/>blank → 8000"]
    PS --> V4["field_validator DATABASE_URL<br/>asyncpg: sslmode→ssl, drop channel_binding"]
    V1 & V2 & V3 & V4 --> S["@lru_cache get_settings()"]
    S --> APP["main.py / services / crypto / security"]
```

## 5.2 Variable reference

Legend: **R** = required (app refuses to start without it), **O** = optional (default shown).

### Application

| Variable | R/O | Default | Purpose |
|---|---|---|---|
| `APP_NAME` | O | `DeployBridge` | FastAPI title, logger name, log banner. |
| `APP_VERSION` | O | `0.1.0` (`.env.example` sets `1.0.0`) | Shown in OpenAPI docs and startup log. |
| `APP_DESCRIPTION` | O | `DevOps automation ai powered agent` | OpenAPI description. |
| `DEBUG` | O | `False` | Flexible boolean parsing (see validator). Logged at startup. |
| `ENV_TYPE` | O | `local` | `Environment` enum: `local` or `production`. |
| `DOCS_URL` | O | `/docs` | Swagger UI path; blank → disabled (`None`). |
| `REDOC_URL` | O | `None` | ReDoc path; blank → disabled. |
| `HOST` | O | `0.0.0.0` | Uvicorn bind host when running `python -m src.main`. |
| `PORT` | O | `8000` | Uvicorn port. |
| `LOG_LEVEL` | O | `INFO` | Root logger level for the `DeployBridge` logger. |
| `CORS_ALLOWED_ORIGINS` | O | `http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:5501,http://localhost:5501` | Comma-separated browser origins allowed to call the API (VS Code Live Server defaults). Must include the GitHub Pages origin for a hosted frontend. |

### Database

| Variable | R/O | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | **R** | — | `postgresql+asyncpg://user:pass@host/db?sslmode=require`. Normalised automatically for asyncpg. Also consumed by `alembic/env.py`. |

### GitHub OAuth & token protection

| Variable | R/O | Default | Purpose |
|---|---|---|---|
| `GITHUB_CLIENT_ID` | **R** | — | OAuth App client id; embedded in the login URL. |
| `GITHUB_CLIENT_SECRET` | **R** | — | Used server-side only to exchange the `code` for an access token. |
| `GITHUB_TOKEN_ENCRYPTION_KEY` | **R** | — | 32-byte url-safe base64 **Fernet key**. Encrypts `users.github_token` and `users.render_api_key`. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Rotating it without re-encrypting rows causes `TokenDecryptionError` (users must re-login). |

### Session (JWT & cookie settings)

| Variable | R/O | Default | Purpose |
|---|---|---|---|
| `JWT_SECRET_KEY` | **R** | — | HMAC secret for session JWTs. |
| `JWT_ALGORITHM` | O | `HS256` | Signing algorithm; `decode_session_jwt` only accepts this one (prevents `alg=none`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | O | `10000` (~6.9 days) | Session lifetime. `/auth/refresh` mints a new token before expiry. |
| `SESSION_COOKIE_NAME` | O | `deploybridge_session` | Reserved for a future cookie-based session (currently the frontend stores the JWT in localStorage). |
| `SESSION_COOKIE_SECURE` | O | `False` | Set `True` in production (HTTPS only). |
| `SESSION_COOKIE_SAMESITE` | O | `lax` | `lax` / `strict` / `none`. |
| `SESSION_COOKIE_DOMAIN` | O | `None` | e.g. `.deploybridge.dev`. |
| `SESSION_COOKIE_PATH` | O | `/` | Cookie path. |

### LLM provider (OpenAI-compatible)

| Variable | R/O | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | O* | `None` | API key for Gemini **or** Groq. *If missing, `GroqLLMClient()` raises `LLMClientError` and the report/agent endpoints return **503** — the rest of the app still works.* |
| `GROQ_BASE_URL` | O | `https://generativelanguage.googleapis.com/v1beta/openai/` | Gemini's OpenAI-compatible endpoint. Use `https://api.groq.com/openai/v1` for Groq. |
| `GROQ_MODEL` | O | `gemini-1.5-flash` | Model name; `gemini-2.5-flash` or `llama-3.1-8b-instant` are documented alternatives. |
| `GROQ_TIMEOUT_SECONDS` | O | `60.0` | Per-request timeout on the OpenAI client. |

### Report delivery — Cloudinary & SMTP

| Variable | R/O | Default | Purpose |
|---|---|---|---|
| `CLOUDINARY_CLOUD_NAME` | O | `None` | If all three Cloudinary values are present, report PDFs are uploaded and `repo_reports.cloudinary_url` is filled; otherwise upload is skipped silently. |
| `CLOUDINARY_API_KEY` | O | `None` | — |
| `CLOUDINARY_API_SECRET` | O | `None` | — |
| `REPORT_DELIVERY_ENABLED` | O | `False` (`.env.example` sets `True`) | Master switch for e-mail sending. |
| `SMTP_HOST` | O | `None` | e.g. `smtp.gmail.com`. All of host/user/password/from must be set or sending is skipped with a warning. |
| `SMTP_PORT` | O | `587` | STARTTLS port. |
| `SMTP_USER` | O | `None` | Login user. |
| `SMTP_PASSWORD` | O | `None` | App password. |
| `SMTP_FROM` | O | `None` | From address (rendered as `DeployBridge <from>`). |

## 5.3 Graceful degradation matrix

| Missing configuration | Effect |
|---|---|
| `GROQ_API_KEY` | `/reports/generate`, `/agent/.../messages`, `/agent/.../approve` → 503 "AI provider is not configured". Render's Django folder guess silently falls back to a heuristic. Everything else works. |
| Cloudinary trio | Reports still generate; `cloudinary_url` stays `null`; e-mail (if enabled) has no cloud link but still attaches the PDF. |
| SMTP / `REPORT_DELIVERY_ENABLED=False` | Reports still generate and can be downloaded as PDF from the UI; status still reaches `delivered`. |
| `GITHUB_TOKEN_ENCRYPTION_KEY` malformed | **Startup fails** with an actionable error (by design). |
| `DATABASE_URL`, GitHub OAuth pair, `JWT_SECRET_KEY` | **Startup fails** (Pydantic validation error). |

## 5.4 Frontend configuration

The frontend has a single hard-coded constant repeated in each module: `const BACKEND_API_URL = "http://127.0.0.1:8000/v1";` (`auth.js`, `deployments.js`, `reports.js`, `agent.js`, inline in `repositories.html`, `settings.html`, `dashboard.html`, `profile.js`). Deploying the backend elsewhere requires changing this value (see Chapter 13 for the proposed `config.js`).

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 6                                                     -->
<!-- ============================================================ -->

# CHAPTER 6 — DATABASE DESIGN

## 6.1 ER Diagram

```mermaid
erDiagram
    USERS ||--o{ REPOSITORIES : "schedules"
    USERS ||--o{ REPO_REPORTS : "generates"
    USERS ||--o{ DEPLOYMENTS : "owns"
    USERS ||--o{ AGENT_SESSIONS : "chats in"
    USERS ||--o{ AGENT_MESSAGES : "authors"
    AGENT_SESSIONS ||--o{ AGENT_MESSAGES : "contains"

    USERS {
        uuid id PK
        string github_id UK "GitHub numeric id as string"
        string username
        string email UK "nullable, primary verified email"
        string avatar_url
        string github_token "Fernet ciphertext"
        string github_token_type "bearer"
        string github_scope "read:user user:email repo workflow"
        string deploy_branch "nullable preference"
        string render_api_key "Fernet ciphertext, nullable"
        string render_owner_id "tea-... workspace id"
        datetime created_at
        datetime updated_at
        datetime last_login
    }

    REPOSITORIES {
        uuid id PK
        uuid user_id FK
        string owner
        string name
        boolean is_scheduled "default false"
        string schedule_frequency "daily | weekly"
        datetime created_at
    }

    REPO_REPORTS {
        uuid id PK
        uuid user_id FK
        string owner
        string repository
        string repo_full_name "indexed owner/repo"
        text report_markdown
        string model_used
        int prompt_tokens
        int completion_tokens
        int duration_ms
        string status "pending|generating|generated|delivering|delivered|failed"
        string cloudinary_url
        text error_message
        datetime generated_at
        datetime created_at
    }

    DEPLOYMENTS {
        uuid id PK
        uuid user_id FK
        string platform "github_pages | render"
        string owner
        string repo
        string branch
        string profile "html|jekyll|node-static|next-static|python|node|docker"
        string status "pending|building|live|failed"
        string service_id "workflow filename OR srv-..."
        string external_deploy_id "Actions run id OR dep-..."
        string url
        text error "captured logs on failure"
        datetime created_at
        datetime updated_at
    }

    AGENT_SESSIONS {
        uuid id PK
        uuid user_id FK
        string title "first message, 80 chars"
        string state "idle|running|awaiting_approval|error"
        datetime created_at
        datetime updated_at
    }

    AGENT_MESSAGES {
        uuid id PK
        uuid session_id FK
        uuid user_id FK
        string role "user|assistant|tool|assistant_tool_call|assistant_plan|user_approval"
        text content
        string tool_name "tool name or tool_call_id"
        int prompt_tokens
        int completion_tokens
        datetime created_at
    }
```

## 6.2 Table-wise Description

### `users`
The identity table. One row per GitHub account. Created/updated on every successful OAuth callback (upsert by `github_id`). Holds **two encrypted secrets**: the GitHub OAuth token (needed for every GitHub call on the user's behalf) and, optionally, a Render API key plus the cached Render workspace id. `deploy_branch` lets a user force deployments from a branch other than the repo default. The `render_connected` property (not a column) tells the UI whether a key is stored without ever exposing it.

### `repositories`
Bookkeeping for **scheduled reports**: which `owner/name` repositories should be analysed automatically and how often. Scanned by the APScheduler cron job. *There is currently no API endpoint that inserts into this table — rows must be created directly in the database (see Chapter 12).*

### `repo_reports`
One row per AI analysis run. Created immediately in `pending` state by `POST /reports/generate` (so the daily quota counts in-flight work), then updated by the background job through `generating → generated → delivering → delivered` (or `failed` with `error_message`). Stores the full Markdown, token accounting and duration for cost transparency, and the Cloudinary PDF URL. Composite index `(user_id, generated_at)` serves the history page.

### `deployments`
The unified deployment ledger for **both platforms**. `platform` discriminates how `service_id` / `external_deploy_id` are interpreted:

| platform | `service_id` | `external_deploy_id` | `url` |
|---|---|---|---|
| `github_pages` | workflow filename (e.g. `node-static.yml`) — used to post-filter the Actions runs API | GitHub Actions run id (learned on first refresh) | `https://owner.github.io/repo` (set when live) |
| `render` | `srv-…` service id | `dep-…` deploy id (from create or latest redeploy) | `https://name.onrender.com` |

`error` stores the **actual build logs** (≤ 30 KB) when a deployment fails, which the Deploy Agent later reads.

### `agent_sessions`
A chat thread. `state` drives the UI (`awaiting_approval` shows the Approve/Cancel card). `title` is derived from the first user message. `updated_at` orders the sidebar.

### `agent_messages`
Every message in a thread, deliberately shaped like the **OpenAI message format** so rows can be replayed to the model without translation. Beyond the standard roles, three DeployBridge-specific roles exist:

| role | content | Fed back to the LLM? |
|---|---|---|
| `user` | user text | yes |
| `assistant` | final text answer | yes |
| `assistant_tool_call` | JSON `{content, tool_calls:[…]}` — the model's own tool request | yes (replayed verbatim, required by the API) |
| `tool` | tool result string (≤ 30 KB); `tool_name` holds the `tool_call_id` | yes |
| `assistant_plan` | JSON list of gated side-effect steps | **no** (UI state) |
| `user_approval` | `"approved"` / `"cancelled"` | **no** (audit) |

Token counts are stored per message so the total cost of a session is a simple `SUM`.

## 6.3 Migration History

| # | Revision | Date | Change |
|---|---|---|---|
| 1 | `61fec428af4e` | 2026-06-20 | Create `users` (id, github_id, username, email, avatar_url, timestamps). |
| 2 | `9f3021b89fdf` | 2026-07-05 | Add `github_token`, `github_token_type`, `github_scope` to `users`. |
| 3 | `62cad5c4cb44` | 2026-08-15 | Add `users.deploy_branch`. |
| 4 | `95780adea624` | 2026-09-12 | Create `repo_reports` + composite index. |
| 5 | `471657679a4a` | 2026-09-12 | Create `repositories`. |
| 6 | `dad6b157e666` | 2026-09-17 | Add `users.render_api_key`, `users.render_owner_id`. |
| 7 | `7f09806a3b0b` | 2026-09-17 | Widen `render_api_key` to hold Fernet ciphertext. |
| 8 | `9f8ae6414de0` | 2026-09-19 | Create `agent_sessions`, `agent_messages` (and deployments scaffolding). |
| 9 | `dece5564cf24` | 2026-09-19 | Create `deployments` (current head). |

<div style="page-break-after: always;"></div>
<!-- ============================================================ -->
<!--  CHAPTER 7                                                     -->
<!-- ============================================================ -->

# CHAPTER 7 — API SERVICES & BUSINESS LOGIC

All endpoints live under the prefix **`/v1`**. Unless marked *public*, every endpoint requires `Authorization: Bearer <session JWT>` and resolves the caller through `get_current_user`. Responses are Pydantic models; errors follow FastAPI's `{"detail": "..."}` shape.

Common guard pattern used by GitHub- and Render-backed endpoints:

```text
if not current_user.github_token:      → 400 "token missing, please re-authenticate"
decrypt_secret(...)  TokenDecryptionError → 500 (key mismatch / tampering — user must re-login)
GitHubPagesError / RenderError / GitHubAPIError → HTTP exc.status_code, detail = exc.detail or exc.message
LLMClientError                          → 503 (AI provider not configured / failed)
```

---

## 7.1 Health — `health.py`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/health` | public | Liveness probe. Returns `{"status": "Ok"}`. Used by uptime checks and the first test in the suite. |

---

## 7.2 Authentication — `auth.py`

### Overview of the login flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as auth.html / auth.js
    participant BE as FastAPI /v1/auth
    participant GH as GitHub OAuth
    participant API as GitHub REST API
    participant DB as PostgreSQL

    U->>FE: click "Sign in with GitHub"
    FE->>BE: GET /auth/login
    BE-->>FE: {login_url, state}
    FE->>FE: sessionStorage.oauth_state = state
    FE->>GH: redirect to login_url (scope read:user user:email repo workflow)
    GH-->>FE: redirect back ?code=…&state=…
    FE->>FE: compare state with sessionStorage (CSRF check)
    FE->>BE: GET /auth/callback?code=…
    BE->>GH: POST /login/oauth/access_token (client_id, client_secret, code)
    GH-->>BE: access_token, token_type, scope
    BE->>API: GET /user, GET /user/emails
    API-->>BE: profile + primary verified email
    BE->>DB: upsert users by github_id (token stored Fernet-encrypted)
    BE->>BE: create_session_jwt(user.id)
    BE-->>FE: {session_token, user{...}, scope, token_type, last_login}
    FE->>FE: localStorage.db_session_token = JWT (+ gh_* fields)
    FE->>U: redirect to dashboard.html
```

### Endpoints

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/v1/auth/login` | public | — | `{login_url, state}` |
| GET | `/v1/auth/callback` | public | query `code` | `{message, user{id,username,email,avatar_url,last_login,scope,token_type}, session_token, scope, token_type, last_login}` |
| GET | `/v1/auth/profile` | JWT | — | `UserProfileResponse{id, username, email, avatar_url, deploy_branch, render_connected}` |
| PATCH | `/v1/auth/profile` | JWT | `{deploy_branch}` | `UserProfileResponse` |
| POST | `/v1/auth/refresh` | JWT | — | `{session_token}` |
| POST | `/v1/auth/logout` | — | — | `{message: "Logged out"}` |

### Business logic

* **`/login`** builds the GitHub authorize URL with `client_id`, the four scopes and a fresh `secrets.token_urlsafe(16)` **state**. The state is returned to the frontend, which stores it in `sessionStorage` and verifies it when GitHub redirects back — protecting against login-CSRF. (The `workflow` scope is mandatory: without it GitHub refuses to write files under `.github/workflows/`.)
* **`/callback`** exchanges the code (`GitHubService.get_access_token`), fetches profile + the **primary verified e-mail** (`get_user_profile`), then **upserts** the user by `github_id`: new users are inserted, returning users get username/email/avatar/token/scope/`last_login` refreshed. The access token is stored **encrypted** (`encrypt_secret`). Finally a session JWT is minted and returned. The response is intentionally flat + nested so older frontend code keeps working.
* **`/profile` GET** validates the ORM row straight into `UserProfileResponse` (`from_attributes=True`). The `render_connected` boolean lets the Settings page show a "Connected" badge without a second call.
* **`/profile` PATCH** trims and saves `deploy_branch`; an empty string clears the preference (`None`). All Pages/Render detect and deploy calls honour this branch and validate it exists (`_branch_exists`).
* **`/refresh`** issues a new JWT for a still-valid one (sliding session). The old token remains valid until its own `exp` — rotation/denylist is future work.
* **`/logout`** is currently a **no-op** on the server (no denylist table yet); the frontend clears `localStorage`.

---

## 7.3 GitHub Data — `github.py`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/v1/github/repos/info` | JWT | `{owner, repository}` | `RepositoryInfoResponse` (see below) |
| GET | `/v1/github/user` | JWT | — | raw GitHub `/user` JSON |
| GET | `/v1/github/user/repos` | JWT | any GitHub query params (`sort`, `per_page`, …) | raw GitHub `/user/repos` JSON array |

### Business logic — `repos/info` (the repository explorer)

`GitHubService.get_repository_info()` performs **1 sequential + 8 parallel** GitHub calls with `asyncio.gather(..., return_exceptions=True)` so one failing sub-fetch never breaks the whole response:

```mermaid
flowchart TB
    A["GET /repos/{o}/{r} → basic_info<br/>(name, description, visibility, default_branch, stars, forks, issues, topics, size, dates)"] --> B{"repo found?"}
    B -- no --> ERR["success=false, message, errors"]
    B -- yes --> G["asyncio.gather (parallel)"]
    G --> D1["deployment_status<br/>/pages + /pages/builds + platform config files<br/>(vercel.json, netlify.toml, railway.json, render.yaml, Procfile, Dockerfile)"]
    G --> D2["languages → percentages"]
    G --> D3["commits (recent, short_sha, author, date)"]
    G --> D4["contributors (top N)"]
    G --> D5["branches (≤20, default flagged)"]
    G --> D6["readme (decoded)"]
    G --> D7["root file_tree"]
    G --> D8["detect_tech_stack_simple<br/>package.json deps → framework/build tool/tests<br/>requirements.txt/pyproject/setup.py → Django/Flask/FastAPI<br/>go.mod, Cargo.toml, pom.xml/build.gradle, lockfiles → package manager"]
    D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 --> R["RepositoryInfoResponse<br/>success, api_calls_made=9, fetched_at, errors[]"]
```

The response feeds three consumers: the **repo-info modal** (10 sections in `repositories.js`), the **Report Agent's base context** (`ReportService._summarize_repo_info`), and the Deploy Agent's `analyze_repository` tool.

### Business logic — proxies
`/user` and `/user/repos` exist so the browser **never holds the GitHub token**: the backend decrypts it, forwards the request (passing through query params for `/user/repos`) and returns GitHub's JSON unchanged. Non-200 upstream responses are mirrored as the same status code.

---

## 7.4 GitHub Pages Deployment — `github_pages.py`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/v1/github-pages/detect` | JWT | `{owner, repository}` | `GitHubPagesDetectResponse{detected_profile, supported_profiles, reason, branch, recommended_platform}` |
| POST | `/v1/github-pages/deploy` | JWT | `{owner, repository, deployment_profile="auto"}` | `GitHubPagesDeployResponse{success, message, resolved_profile, workflow_template, branch}` |
| POST | `/v1/github-pages/custom-domains/{owner}/{repository}` | JWT | `{domain, branch?}` | `GitHubPagesCustomDomainResponse{domain, branch, cname_target, record_type, record_name, https_enabled, status}` |
| POST | `/v1/github-pages/custom-domains/{owner}/{repository}/{domain}/verify` | JWT | — | `GitHubPagesCustomDomainResponse` |

### 7.4.1 Repository context (shared with Render)

`_build_repository_context()` makes the GitHub calls once and produces a `RepositoryContext` dataclass: `default_branch`, `selected_branch` (user preference validated via `/branches/{name}`), root item names & directories (lower-cased), parsed `package.json` (`dependencies`, `devDependencies`, `scripts`, `name`), the first existing `next.config.{js,mjs,ts}` text and the `Gemfile` text. Every detection rule below is a pure function over this context — **no further network calls**.

### 7.4.2 Profile detection decision tree

```mermaid
flowchart TD
    S["RepositoryContext"] --> Q0{"Dockerfile / docker-compose at root?"}
    Q0 -- yes --> R0["recommend Render<br/>(Pages cannot run containers)"]
    Q0 -- no --> Q1{"server markers in package.json?<br/>express fastify koa @nestjs/core hono socket.io remix next-auth"}
    Q1 -- yes --> R1["recommend Render"]
    Q1 -- no --> Q2{"Next.js signal?<br/>dep 'next' or next.config.* or script 'next …'"}
    Q2 -- yes --> Q3{"static export?<br/>script 'next export' or output: 'export'"}
    Q3 -- yes --> P4["profile = next-static"]
    Q3 -- no --> R2["recommend Render (SSR)"]
    Q2 -- no --> Q4{"requirements.txt or *.py at root?"}
    Q4 -- yes --> R3["recommend Render (Python)"]
    Q4 -- no --> Q5{"Jekyll?<br/>_config.yml or _posts/ or Gemfile mentions jekyll/github-pages"}
    Q5 -- yes --> P2["profile = jekyll"]
    Q5 -- no --> Q6{"Node static?<br/>package.json with react/vite/vue/svelte/astro/gatsby/angular/nuxt/eleventy/preact<br/>or a build/generate script (and no server-only markers)"}
    Q6 -- yes --> P3["profile = node-static"]
    Q6 -- no --> Q7{"Plain HTML?<br/>index.html/404.html/styles.css/main.js/app.js, any .html/.css/.js,<br/>or assets/static/css/js/images dirs — and no package.json"}
    Q7 -- yes --> P1["profile = html"]
    Q7 -- no --> X["400 Unsupported repository type"]
```

`detect` returns `recommended_platform="render"` (HTTP 200, not an error) whenever the Render branch is hit, so the frontend can show a **"Deploy to Render instead"** button. When the user passes an explicit profile, `_validate_profile_override` checks it is plausible (e.g. `next-static` requires a Next.js repo *with* static export; `html` refuses framework repos) and returns a 400 with a corrective message otherwise.

### 7.4.3 Deploy sequence

```mermaid
sequenceDiagram
    autonumber
    participant FE as repositories.html
    participant API as POST /github-pages/deploy
    participant GP as GitHubPagesService
    participant GH as GitHub API
    participant DS as DeploymentService
    participant DB as PostgreSQL

    FE->>API: {owner, repository, deployment_profile}
    API->>GP: deploy(token, owner, repo, profile, preferred_branch)
    GP->>GH: GET /repos/{o}/{r} (verify + X-OAuth-Scopes must contain "workflow")
    GP->>GH: contents/, package.json, next.config.*, Gemfile (build context)
    GP->>GP: resolve profile (auto-detect or validate override)
    loop for each other DeployBridge workflow file
        GP->>GH: GET + DELETE .github/workflows/<stale>.yml (on selected + default branch)
    end
    GP->>GH: GET sha → PUT .github/workflows/<profile>.yml (template with __DEFAULT_BRANCH__ replaced)
    GP->>GH: GET /pages → POST (create) or PUT (update) {build_type: workflow, source: branch}
    GP->>GH: POST /actions/workflows/<file>/dispatches {ref: branch} (retry ×3 on 404/422, 1 s apart)
    GP-->>API: GitHubPagesDeployResponse
    API->>DS: create_from_pages_deploy(status=pending, service_id=<file>.yml)
    DS->>DB: INSERT deployments
    API-->>FE: {success, resolved_profile, workflow_template, branch}
    FE->>FE: toast + redirect to deployments.html (auto-refresh begins)
```

Key business rules:

* **Scope enforcement** — `_ensure_required_scopes` reads the `X-OAuth-Scopes` response header; a token without `workflow` gets a 403 telling the user to log out and log in again.
* **Idempotent workflow upsert** — if the file exists, its `sha` is included so GitHub performs an update instead of a conflict.
* **Stale-workflow cleanup** — switching a repo from `html` to `node-static` removes the old DeployBridge workflow so two Pages workflows never race.
* **Row written last** — a failure at any GitHub step raises before the `deployments` row is created; no phantom deployments.

### 7.4.4 Custom domains (file-based)

For Pages, "attach a domain" literally means **committing a `CNAME` file** containing the hostname to the deploy branch root via the Contents API. The service then derives what the user must add at their registrar:

| Domain shape | `record_type` | `record_name` | `cname_target` |
|---|---|---|---|
| Subdomain `notes.kumar.dev` | `CNAME` | `notes` | `kumar.github.io` |
| Apex `kumar.dev` or `owner.github.io` | `A` | `@` | first of `185.199.108.153 … 185.199.111.153` (UI shows all four) |

`/verify` re-reads the Pages configuration (`cname`, `https` fields) and, once GitHub has issued the certificate, tries to enable **HTTPS enforcement** on the user's behalf. Status progresses `waiting_for_dns → verified → live`; the endpoint never blocks.

---

## 7.5 Render Deployment — `render.py`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/v1/render/connect` | JWT | `{api_key}` | `RenderConnectResponse{connected, owner_id, owner_name, owner_email, owner_type}` |
| DELETE | `/v1/render/connect` | JWT | — | `RenderStatusResponse{connected:false}` |
| GET | `/v1/render/status` | JWT | — | `RenderStatusResponse{connected, owner_id, …}` |
| POST | `/v1/render/detect` | JWT | `{owner, repository}` | `RenderDetectResponse{runtime, build_command, start_command, dockerfile_path, plan, branch, reason, env_var_suggestions}` |
| POST | `/v1/render/deploy` | JWT | `RenderDeployRequest{owner, repository, branch, service_name, runtime, build_command?, start_command?, dockerfile_path?, plan="free", auto_deploy=true, env_vars[]}` | `RenderDeployResponse{success, service_id, deploy_id, service_url, dashboard_url, message}` |
| GET | `/v1/render/services` | JWT | — | `list[RenderServiceSummary]` |
| GET | `/v1/render/services/{service_id}` | JWT | — | `RenderServiceDetail` (+ latest deploy status/id) |
| POST | `/v1/render/services/{service_id}/redeploy` | JWT | — | `RenderRedeployResponse{success, deploy_id, message}` |
| POST | `/v1/render/services/{service_id}/custom-domain` | JWT | `{domain}` | `RenderCustomDomainResponse{id, name, cname_target, verification_status, …}` |
| POST | `/v1/render/services/{service_id}/custom-domain/{domain_name_or_id}/verify` | JWT | — | `RenderCustomDomainResponse` |

### 7.5.1 Connect / status

Render uses **personal API keys** (`rnd_…`), not OAuth. `/connect` validates the key by calling `GET /v1/owners`, picks the personal workspace (`type="user"`), stores the key **encrypted** and caches the `tea-…` owner id on the user row. `/status` never returns the key. `DELETE` nulls both columns but does **not** delete anything on Render.

### 7.5.2 Runtime detection

`RenderService.detect` reuses the Pages `RepositoryContext` and applies this precedence:

```mermaid
flowchart TD
    C["RepositoryContext"] --> D1{"Dockerfile / docker-compose?"}
    D1 -- yes --> O1["runtime=docker<br/>dockerfile_path=./Dockerfile"]
    D1 -- no --> D2{"Next.js without static export?"}
    D2 -- yes --> O2["runtime=node<br/>build: npm install && npm run build<br/>start: npm start"]
    D2 -- no --> D3{"requirements.txt / pyproject / setup.py<br/>or .py at root without package.json?"}
    D3 -- yes --> D4{"manage.py or django dep?"}
    D4 -- yes --> O3["runtime=python (Django)<br/>start: gunicorn <folder>.wsgi:application --bind 0.0.0.0:$PORT<br/>folder = LLM-assisted guess over root dirs, fallback repo_name"]
    D4 -- no --> D5{"main.py or fastapi/uvicorn dep?"}
    D5 -- yes --> O4["runtime=python (FastAPI)<br/>start: uvicorn main:app --host 0.0.0.0 --port $PORT"]
    D5 -- no --> O5["runtime=python (Flask-style)<br/>start: gunicorn app:app --bind 0.0.0.0:$PORT"]
    D3 -- no --> D6{"package.json with server markers?"}
    D6 -- yes --> O6["runtime=node<br/>build: npm install (+ npm run build)<br/>start: scripts.start or node server.js"]
    D6 -- no --> D7{"package.json at all?"}
    D7 -- yes --> O7["runtime=node (fallback, review commands)"]
    D7 -- no --> O8["runtime=docker (last resort, add a Dockerfile)"]
```

Every branch returns a human `reason`. Python builds always use `pip install -r requirements.txt`. `env_var_suggestions` proposes `NODE_ENV=production` for Node and deliberately **never** sets `PORT` (Render injects it). The Django branch is the one place where the LLM assists a heuristic: it is asked to pick the project folder among root directories (temperature 0.1, 20 tokens); any failure silently falls back to `repo-name → repo_name`.

### 7.5.3 Deploy sequence

```mermaid
sequenceDiagram
    autonumber
    participant FE as repositories.html (modal)
    participant API as POST /render/deploy
    participant RS as RenderService
    participant R as Render API
    participant DS as DeploymentService
    participant DB as PostgreSQL

    FE->>API: RenderDeployRequest (service_name, runtime, commands, env_vars)
    API->>API: _require_render_key → decrypt key, owner_id must exist
    API->>RS: create_web_service(api_key, owner_id, request)
    RS->>RS: build payload: type=web_service, repo URL, branch,<br/>autoDeploy "yes"/"no", envVars (value | generateValue),<br/>serviceDetails{runtime, plan, region oregon, numInstances 1,<br/>envSpecificDetails{buildCommand,startCommand} | {dockerfilePath, dockerContext}}
    RS->>R: POST /v1/services (60 s timeout)
    R-->>RS: {service{id, serviceDetails.url, dashboardUrl}, deployId}
    RS-->>API: RenderDeployResponse
    API->>DS: create_from_render_deploy(status=building, service_id, deploy_id, url)
    DS->>DB: INSERT deployments
    API-->>FE: {service_id, deploy_id, service_url, dashboard_url}
```

Render-specific rules encoded in the service (verified against the live API docs by the authors): `autoDeploy` and `clearCache` are **string enums** (`"yes"/"no"`, `"clear"/"do_not_clear"`), native runtimes **require both** build and start commands, docker runtime uses `dockerfilePath` instead, the public URL lives at `serviceDetails.url`, and `POST /services` auto-triggers the first deploy (its `deployId` is returned so polling can start immediately).

### 7.5.4 Error mapping (`_raise_for`)

| Render status | DeployBridge response |
|---|---|
| 401 | 400 "Invalid Render API key" + link to generate a new one |
| 402 | 402 "Render free-tier limit reached" (25 services / 750 h / 500 build min) |
| 403 | 403 permission / IP allow-list hint |
| 404 | 404 resource not found in this workspace |
| 429 | 429 with `RateLimit-Limit` / `RateLimit-Reset` headers surfaced |
| other 4xx | same status, short summary (raw body suppressed — it may echo env values) |
| 5xx | 502 "Render is unavailable" |

### 7.5.5 Services, redeploy, logs, custom domains

* `list_services` strips Render's `{service, cursor}` wrapper and filters by `ownerId[]`.
* `get_service` = service + most recent deploy (two calls) → `latest_deploy_status`, `latest_deploy_id`.
* `trigger_deploy` → `POST /services/{id}/deploys` with `clearCache: do_not_clear`.
* `get_deploy_logs` → `GET /services/{sid}/deploys/{did}/logs?limit=200`, joins `text` fields, caps at 30 KB, treats 404 as "no logs yet".
* Custom domains: Render's API returns only `verificationStatus`, so the CNAME target is **derived from the service's `onrender.com` host**; `/verify` polls Render's verify endpoint.

---

## 7.6 Deployments (Unified History) — `deployments.py`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/v1/deployments?page=1&page_size=10` | JWT | query (page ≥ 1, 1 ≤ page_size ≤ 50) | `DeploymentListResponse{items[], total, page, page_size}` newest first |
| GET | `/v1/deployments/{id}` | JWT | — | `DeploymentItem` |
| POST | `/v1/deployments/{id}/refresh` | JWT | — | `DeploymentRefreshResponse` (item + `refreshed: bool`) |
| POST | `/v1/deployments/{id}/redeploy` | JWT | — | `DeploymentRedeployResponse{success, id, platform, external_deploy_id, message}` |
| DELETE | `/v1/deployments/{id}` | JWT | — | `DeploymentDeleteResponse{success, id, message}` |

There is intentionally **no `POST /deployments`** — rows are created by the two deploy endpoints (and by the Deploy Agent's side-effect tools). Every query is scoped by `user_id`; a foreign id yields 404, never 403 (no existence leak).

### Status state machine & refresh logic

```mermaid
stateDiagram-v2
    [*] --> pending : Pages workflow dispatched
    [*] --> building : Render service created
    pending --> building : Actions run not yet visible (first refresh)
    building --> live : Render deploy "live" / Actions conclusion "success"
    building --> failed : build_failed, update_failed, canceled, deactivated / Actions failure, cancelled, timed_out, startup_failure
    live --> [*] : terminal — refresh returns refreshed=false
    failed --> [*] : terminal — logs stored in error
    failed --> building : redeploy (new external_deploy_id)
    live --> building : redeploy
```

`DeploymentService.refresh`:

1. Terminal rows return immediately (`refreshed=false`) — saves API quota.
2. **Render:** `get_service` → `_RENDER_STATUS_TO_DB` map (`created/building/update_in_progress → building`, `live → live`, `build_failed/update_failed/canceled/deactivated → failed`). Updates `url` and `external_deploy_id`; on failure fetches `get_deploy_logs` into `error`.
3. **Pages:** `get_workflow_run_status` — by cached `run_id`, else latest run on the branch **post-filtered by workflow path** (`.github/workflows/<service_id>`). `queued/in_progress/waiting → building`, `completed+success → live` (sets `https://owner.github.io/repo`), `completed+failure|cancelled|timed_out|… → failed` (downloads the run's **zip logs**, concatenates the `.txt` files, stores ≤ 30 KB in `error`). If no run is visible yet, `pending → building` and the frontend simply retries in 8 s.

`redeploy`: Render → `trigger_deploy` (new deploy id stored); Pages → re-dispatch the recorded workflow on the recorded branch (run id learned on next refresh). `delete` removes only the history row — the live site/service is untouched.

---

## 7.7 AI Analysis Reports — `reports.py`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/v1/reports/generate` | JWT | `{owner, repository}` | **202 Accepted** `ReportGenerateResponse{success, report_id, repo_full_name, message}` |
| GET | `/v1/reports/history?page&page_size` | JWT | — | `ReportHistoryResponse{items[], total, page, page_size}` |
| GET | `/v1/reports/{id}` | JWT | — | `ReportDetailResponse{…, report_markdown, status, model_used, tokens, duration_ms, cloudinary_url, error_message}` |
| DELETE | `/v1/reports/{id}` | JWT | — | `ReportDeleteResponse` |
| POST | `/v1/reports/{id}/send-email` | JWT | — | `{success, message}` (background) |
| GET | `/v1/reports/{id}/pdf` | JWT | — | `application/pdf` (inline, `<owner>_<repo>_analysis.pdf`) |

### Generation pipeline

```mermaid
flowchart LR
    A["POST /reports/generate"] --> Q{"quota: reports in last 24 h < 10?"}
    Q -- no --> E429["429 daily limit reached"]
    Q -- yes --> P["INSERT repo_reports status=pending"]
    P --> BT["BackgroundTasks.add_task(run_report_job)"]
    BT --> R202["202 {report_id}"]
    subgraph JOB["run_report_job (own AsyncSession)"]
        G["status=generating"] --> AG["report_agent.run_agent_loop<br/>(≤ 8 LLM rounds, tools)"]
        AG --> GEN["status=generated<br/>markdown, model, tokens, duration_ms"]
        GEN --> DEL["status=delivering"]
        DEL --> PDF["PDFService: markdown → HTML → PDF"]
        PDF --> CLD["StorageService.upload_pdf → cloudinary_url (optional)"]
        CLD --> MAIL["EmailService.send_report_email<br/>HTML + text + PDF attachment (optional)"]
        MAIL --> DONE["status=delivered"]
        AG -. LLMClientError / Exception .-> FAIL["status=failed + error_message"]
    end
    R202 --> POLL["frontend polls GET /reports/{id} until generated | delivered | failed"]
```

Business rules:

* **Quota** — `COUNT(repo_reports) WHERE user_id AND created_at ≥ now-24h ≥ 10 → 429`. Because the pending row is inserted *before* the job runs, concurrent requests cannot bypass the limit.
* **Asynchronous** — the HTTP request returns in milliseconds; the heavy work runs in FastAPI `BackgroundTasks` with its **own** `AsyncSessionLocal()` (the request session is already closed).
* **Resilient delivery** — PDF, Cloudinary and e-mail failures are logged but never flip a *generated* report to *failed*; the Markdown is always preserved.
* **PDF on demand** — `/pdf` regenerates the PDF from the stored Markdown each time (no file storage on the server).
* **Resend** — `/send-email` rebuilds the PDF and re-sends to the user's e-mail in the background.

---

## 7.8 Deploy Agent (Chat) — `agent.py`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/v1/agent/sessions` | JWT | `{title?, prefill_question?, prefill_deployment_id?}` | **201** `AgentSessionResponse{id, title, state, created_at, updated_at}` |
| GET | `/v1/agent/sessions?page&page_size` | JWT | — | `AgentSessionListResponse{items[], total}` (by `updated_at` desc) |
| GET | `/v1/agent/sessions/{id}` | JWT | — | `AgentSessionDetailResponse{…, messages[]}` (plans parsed into `plan`) |
| DELETE | `/v1/agent/sessions/{id}` | JWT | — | `{success, message}` (cascades messages) |
| POST | `/v1/agent/sessions/{id}/messages` | JWT | `{content, env_var_values?}` | `AgentSendMessageResponse{session_state, message, trace[]}` |
| POST | `/v1/agent/messages/{message_id}/approve` | JWT | `{approved, env_var_values?}` | `AgentApproveResponse{session_state, message, trace[]}` |

Business logic:

* **Create** — inserts an empty session; if `prefill_question` is given (the *"🤖 Ask Agent"* button on a failed deployment card passes *"Why did my deploy fail?"* plus context), a `user` message is pre-inserted and becomes the title. The loop is **not** run here — the frontend posts the message explicitly, keeping create fast and side-effect free.
* **Send message** — instantiates `DeployAgentRunner` (503 if no LLM key), appends the user message and runs the loop (Chapter 8). The response is either a final assistant message (`idle`) or a plan (`awaiting_approval`).
* **Approve** — loads the `assistant_plan` message (404 if not the caller's, 400 if the wrong role), then `resume_after_approval`: on approve, executes each planned side-effect tool in order (merging `env_var_values` server-side), records synthetic `assistant_tool_call` + `tool` rows, and re-enters the loop so the model can report the result; on cancel, records `user_approval="cancelled"` and lets the model acknowledge.
* All errors are mapped: `TokenDecryptionError`/`LLMClientError → 500`, `RenderError`/`GitHubAPIError → their status`.

<div style="page-break-after: always;"></div>
<!-- ============================================================ -->
<!--  CHAPTER 8                                                     -->
<!-- ============================================================ -->

# CHAPTER 8 — AI LAYER: AGENTIC AI & TOOL CALLING

DeployBridge contains **two agents** built on the same primitive — an LLM that may return *tool calls* instead of text, and Python code that executes those calls and feeds the results back. Everything in this chapter was verified against `services/llm_client.py`, `services/report_agent.py` and `services/deploy_agent.py`.

## 8.1 LLM Client — `GroqLLMClient`

```python
class GroqLLMClient:
    def __init__(self):
        settings = get_settings()
        if not settings.GROQ_API_KEY: raise LLMClientError("GROQ_API_KEY is not configured")
        self._client = AsyncOpenAI(api_key=..., base_url=settings.GROQ_BASE_URL, timeout=settings.GROQ_TIMEOUT_SECONDS)
        self._model = settings.GROQ_MODEL

    async def chat_completion(self, messages, temperature=0.2, max_tokens=..., tools=None) -> dict:
        kwargs = {"model": self._model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if tools: kwargs["tools"] = tools; kwargs["tool_choice"] = "auto"
        completion = await self._client.chat.completions.create(**kwargs)
        return {"content": ..., "model": ..., "prompt_tokens": ..., "completion_tokens": ...,
                "tool_calls": message.tool_calls, "raw_message": message}
```

* One thin wrapper around `openai.AsyncOpenAI`. The class name says *Groq* because Groq was integrated first; today the default `base_url` is Gemini's OpenAI-compatible endpoint. **Provider switching is purely configuration.**
* Returns a plain dict so callers never depend on SDK object shapes (except `raw_message`/`tool_calls`, which are replayed verbatim to the API).
* Any SDK exception is wrapped into `LLMClientError`, which endpoints translate to **503**.

## 8.2 Why a Simple Loop and not LangChain

The repository imports **no** LangChain, LangGraph, LlamaIndex, CrewAI, AutoGen or similar. The agent behaviour is implemented with two hand-written loops:

| | LangChain-style agent | DeployBridge's loop |
|---|---|---|
| Orchestration | `AgentExecutor` / graph runtime | `for step in range(MAX_STEPS)` |
| Tool declaration | `@tool` decorators, auto schema | explicit OpenAI function JSON schemas (`TOOLS`, `SIDEEFFECT_TOOLS`) |
| Memory | `ConversationBufferMemory`, checkpointers | `agent_messages` table, rebuilt into the OpenAI message list every step |
| Human-in-the-loop | interrupts / callbacks | native: a side-effect tool call is **persisted as a plan** and the HTTP request ends; a second endpoint resumes |
| Token/cost control | callbacks | per-step `max_tokens` budget computed from accumulated prompt tokens |
| Dependencies | dozens of transitive packages | `openai` SDK only |

Reasons this was the right choice for the project:

1. **Transparency for an academic audit** — every step of the reasoning loop is readable Python (≈150 lines for the core loop).
2. **Persistence-first design** — because each step reloads the conversation from PostgreSQL, the process can be interrupted (HTTP request returns, user approves minutes later) without in-memory state or checkpointers.
3. **Security** — the secrets rule (§8.6) is a few explicit lines rather than a framework hook.
4. **Free-tier friendliness** — the token budgeting for Groq's TPM limits (`prompt + max_tokens`) is easier to reason about without abstraction layers.

The trade-off is accepted: no streaming, no parallel tool execution, no automatic retries beyond the manual nudge and forced-summary fallbacks.

## 8.3 Report Agent — `report_agent.run_agent_loop`

**Goal:** produce a Markdown audit report with exactly five `##` sections (*Project Overview, Technology Stack, Repository Structure & Code Organization, Recent Activity & Maintenance Health, Recommendations*) plus an appended **Agent Trace** section.

| Tool | Description given to the model | Backed by |
|---|---|---|
| `list_file_tree` | full recursive tree of the default branch (`path`, `type`, `size`) | `GitHubService.list_file_tree_recursive` |
| `read_file` | contents of one file (≤ 30 KB) | `GitHubService.read_file_content` |
| `create_pull_request` | create a branch, add a file, open a PR | `GitHubService.create_file_and_pull_request` |

```mermaid
flowchart TD
    A["build base context<br/>GitHubService.get_repository_info → _summarize_repo_info<br/>(basic info, languages, tech stack, recent commits, contributors, README snippet)"] --> B["messages = [system prompt, user request + context]"]
    B --> C{"step < 8?"}
    C -- yes --> D["chat_completion(messages, tools, temp 0.2,<br/>max_tokens = min(4000, max(500, 8000 − prompt − 500)))"]
    D --> E{"tool_calls?"}
    E -- yes --> F["append assistant message with tool_calls"]
    F --> G["execute each tool in Python<br/>list_file_tree / read_file / create_pull_request"]
    G --> H["append role=tool results (≤ 30 KB)<br/>trace += tool name + args"]
    H --> C
    E -- no --> I["final markdown = content"]
    C -- no --> J["force final call without tools:<br/>'Write the report now with what you have'"]
    J --> I
    I --> K["append '## Agent Trace' (rounds, tools used, files read, tokens)"]
    K --> L["return {markdown, model, prompt_tokens, completion_tokens, duration_ms}"]
```

The report job (`report_job.py`) wraps this loop, stores the result and continues with PDF/Cloudinary/e-mail (Chapter 7.7). The `create_pull_request` tool in *this* agent runs directly (no approval gate) — a known limitation listed in Chapter 12.

## 8.4 Deploy Agent — `DeployAgentRunner`

**Goal:** a conversational operator that can inspect, diagnose and — with approval — act.

### 8.4.1 Tool taxonomy (11 tools)

| Kind | Tool | What Python does |
|---|---|---|
| Read-only (auto-run) | `detect_stack(owner, repo)` | Pages detect + Render detect in one shot → recommendation summary |
| | `read_repo_file(owner, repo, path)` | `GitHubService.read_file_content` |
| | `get_render_status(service_id)` | `RenderService.get_service` |
| | `get_render_logs(service_id, deploy_id?)` | `RenderService.get_deploy_logs` (latest deploy if id omitted) |
| | `list_deployments(status?, platform?)` | `DeploymentService.list_for_user` (includes `error` excerpts) |
| | `list_repositories(limit)` | GitHub `/user/repos` |
| | `analyze_repository(owner, repo)` | `GitHubService.get_repository_info` summary |
| Side-effect (gated) | `deploy_github_pages(owner, repo, profile)` | `GitHubPagesService.deploy` + `DeploymentService.create_from_pages_deploy` |
| | `deploy_render(owner, repo, branch, service_name, runtime, build_command, start_command, dockerfile_path, env_var_keys)` | `RenderService.create_web_service` + `create_from_render_deploy` |
| | `create_pull_request(owner, repo, branch_name, file_path, file_content, title, body)` | `GitHubService.create_file_and_pull_request` |
| | `add_render_custom_domain(service_id, domain)` | `RenderService.add_custom_domain` |

### 8.4.2 The loop

```mermaid
flowchart TD
    U["POST /agent/sessions/{id}/messages"] --> A["append role=user"]
    A --> L["_run_loop"]
    L --> R["_load_messages_for_llm<br/>system prompt + replay of user / assistant / assistant_tool_call / tool rows<br/>(assistant_plan & user_approval skipped)"]
    R --> C["chat_completion(tools = READ-ONLY + SIDE-EFFECT schemas)"]
    C --> T{"tool_calls present?"}
    T -- "any side-effect tool" --> P["Branch A — PLAN<br/>persist role=assistant_plan (JSON list of tool/args/summary)<br/>session.state = awaiting_approval<br/>return plan to UI  ⟵ request ends here"]
    T -- "only read-only tools" --> X["persist role=assistant_tool_call<br/>execute each tool → persist role=tool (≤ 30 KB)<br/>trace += 'tool(args)'"]
    X --> S{"step < 8?"}
    S -- yes --> R
    T -- "no tool_calls, content present" --> F["Branch B — FINAL<br/>persist role=assistant, state = idle, return"]
    T -- "no tool_calls, empty content" --> N["nudge: '(Please respond with your next action or your final answer.)'"]
    N --> S
    S -- no --> Z["forced summary call without tools<br/>'You have reached the maximum number of tool steps…'"]
    Z --> F
```

Details worth noting:

* **Conversation is rebuilt from the database on every step** (`_load_messages_for_llm`). Nothing lives only in RAM, so a plan can be approved in a later HTTP request or even after a server restart.
* `assistant_tool_call` rows store the model's own tool-call payload (`id`, `function.name`, `arguments`); `tool` rows store the `tool_call_id` in `tool_name`. This is exactly what the OpenAI API requires for replay.
* Every tool exception (`RenderError`, `GitHubAPIError`, `GitHubPagesError`) is turned into a **tool result string** (`"Error: … Detail: …"`) rather than a crash, so the model can explain the problem to the user.
* `trace` (list of `tool(args…)` strings) is returned with each response and rendered as a collapsible **"Agent trace"** in the UI.

### 8.4.3 Session state machine

```mermaid
stateDiagram-v2
    [*] --> idle : POST /agent/sessions
    idle --> running : POST messages (loop starts)
    running --> idle : final assistant answer
    running --> awaiting_approval : side-effect tool requested → plan persisted
    awaiting_approval --> running : POST /approve {approved:true} → tools executed → loop resumes
    awaiting_approval --> running : POST /approve {approved:false} → cancelled note → loop resumes
    running --> error : LLM call failed (assistant error text stored)
    error --> running : user sends another message
```

## 8.5 The Confirm-Gate (Human-in-the-Loop)

```mermaid
sequenceDiagram
    autonumber
    participant U as User (agent.html)
    participant API as /v1/agent
    participant RUN as DeployAgentRunner
    participant LLM as Gemini / Groq
    participant SVC as Render / Pages services
    participant DB as PostgreSQL

    U->>API: POST sessions/{id}/messages "Deploy my notes-api to Render"
    API->>RUN: run_user_message
    RUN->>LLM: messages + tools
    LLM-->>RUN: tool_call detect_stack(owner, repo)
    RUN->>SVC: Pages detect + Render detect
    RUN->>DB: assistant_tool_call + tool rows
    RUN->>LLM: (loop) messages incl. tool result
    LLM-->>RUN: tool_call read_repo_file(".env.example")
    RUN->>DB: rows…
    RUN->>LLM: (loop)
    LLM-->>RUN: tool_call deploy_render(..., env_var_keys=["DATABASE_URL","SECRET_KEY"])
    Note over RUN: side-effect detected → NOT executed
    RUN->>DB: role=assistant_plan, session.state=awaiting_approval
    RUN-->>U: {session_state: awaiting_approval, plan[...]}
    U->>U: plan card renders summary + one input per env key
    U->>API: POST messages/{plan_id}/approve {approved:true, env_var_values:{DATABASE_URL:"…", SECRET_KEY:"…"}}
    API->>RUN: resume_after_approval
    RUN->>DB: role=user_approval "approved"
    RUN->>SVC: RenderService.create_web_service (values merged server-side)
    RUN->>DB: deployments row + synthetic assistant_tool_call/tool rows (id planexec_<msg>_<tool>)
    RUN->>LLM: (loop) tool result "Render service created: srv-… url …"
    LLM-->>RUN: final text "Your app is building at https://notes-api.onrender.com …"
    RUN->>DB: role=assistant, state=idle
    RUN-->>U: {session_state: idle, message}
```

Design consequences:

* **Nothing irreversible happens inside the first request.** The plan is data; the user can close the tab and approve tomorrow.
* The plan card shows a **human summary** per step (`_summarize_plan_step`: e.g. *"Create Render service 'notes-api' (python, free plan, auto-deploy on) with 2 env var(s)"* or *"Deploy owner/repo to GitHub Pages (profile=auto)"*), so approval is informed.
* **Cancel** is a first-class path: the model is told the plan was cancelled and asked to acknowledge/offer alternatives.

## 8.6 The Secrets Rule

> *The LLM sees environment-variable **keys**; it never sees **values**.*

Implementation points:

1. The `deploy_render` tool schema exposes only `env_var_keys: string[]`. There is no `env_var_values` parameter for the model to fill.
2. The system prompt instructs: *"NEVER invent env-var values… Tell the user which keys are needed and stop."*
3. The frontend plan card renders one **password-style input per key**; values are posted **only** to `/approve`.
4. `_execute_sideeffect_tool` merges `env_var_values` (from the HTTP body) into Render's `envVars` payload **after** the model has finished. Missing values become empty strings, which Render rejects with a clear error that the model can then explain.
5. Render 4xx bodies are never echoed (they may contain env values); tool results describing the created service contain only ids and URLs.

## 8.7 Guardrails & Cost Control

| Guard | Value / rule | Why |
|---|---|---|
| `MAX_STEPS` | 8 LLM rounds per user message | Prevents infinite tool loops; a forced summary is generated when exhausted. |
| Per-step `max_tokens` | `min(4000, max(500, 8000 − prompt_tokens − 500))` | Keeps `prompt + completion` under free-tier TPM windows (Groq counts both). |
| `MAX_OUTPUT_TOKENS` | 4000 | Final answers / forced summaries. |
| `MAX_TOOL_RESULT_CHARS` | 30 000 | Tool outputs (logs, files, trees) are truncated before being stored or shown to the model. |
| `temperature` | 0.2 | Deterministic, operational answers. |
| Empty-response nudge | one synthetic user turn | Recovers from a blank completion without burning all steps. |
| Report quota | 10 per user per 24 h | Caps LLM spend and GitHub API usage. |
| Token accounting | `prompt_tokens`/`completion_tokens` on every message and report row | Cost transparency per session/report. |

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 9                                                     -->
<!-- ============================================================ -->

# CHAPTER 9 — SECURITY DESIGN

## 9.1 Threat model in brief

DeployBridge holds credentials that can **modify a user's GitHub repositories** and **create billable resources on Render**, and it lets an LLM propose actions. The design therefore focuses on: (a) never leaking third-party tokens to the browser or the model, (b) strong per-user isolation, and (c) explicit human approval for side effects.

## 9.2 Controls

| Area | Control | Location |
|---|---|---|
| **Authentication** | GitHub OAuth 2.0 (authorization-code flow) with a random `state` verified by the frontend before the code is used. | `auth.py`, `auth.js` |
| **Session** | Stateless JWT (HS256) with `sub`, `iat`, `exp`, `jti`, `iss="DeployBridge"`. Decoding enforces the configured algorithm, the issuer and required claims; expired/invalid → 401 with `WWW-Authenticate: Bearer`. | `core/security.py`, `api/dependencies.py` |
| **Secrets at rest** | GitHub token and Render API key are Fernet-encrypted (AES-128-CBC + HMAC-SHA256) with `GITHUB_TOKEN_ENCRYPTION_KEY`. Startup validates the key and migrates legacy plaintext rows. Decryption happens per request, in memory. | `core/crypto.py`, `core/lifespan.py` |
| **No token exposure to the browser** | GitHub `/user` and `/user/repos` are proxied; Render status never returns the key; the profile response only says `render_connected`. | `github.py`, `render.py` |
| **Logging hygiene** | Tokens are logged only as truncated SHA-256 prefixes (`hashlib.sha256(token)[:12]`). Render error bodies are not echoed. | `dependencies.py`, `render.py` |
| **Tenant isolation** | Every query on `deployments`, `repo_reports`, `agent_sessions`, `agent_messages` filters by `user_id`; foreign ids return 404. Cascade deletes on user removal. | services & models |
| **Scope least-privilege check** | Pages deploy verifies the token's `X-OAuth-Scopes` contains `workflow` before attempting to write workflow files. | `github_pages.py` |
| **Human-in-the-loop for AI** | Side-effect tools are never executed inside the model loop; they require `/approve`. | `deploy_agent.py` |
| **Prompt-side secret redaction** | Only env-var *keys* are in the model context; values travel browser → `/approve` → Render. | `deploy_agent.py`, `agent.js` |
| **Input validation** | Pydantic models with `min_length`, `Literal` unions, `ge/le` bounds on pagination, branch existence checks, domain sanity checks. | `schemas/*` |
| **CORS** | Explicit allow-list from `CORS_ALLOWED_ORIGINS`; credentials allowed only for those origins. | `main.py` |
| **Rate/quota** | 10 reports / 24 h per user; Render 429s are surfaced with `RateLimit-*` headers; workflow dispatch retries are bounded (3 × 1 s). | `reports.py`, `render.py`, `github_pages.py` |
| **Fail-closed configuration** | Missing/invalid Fernet key, DB URL, OAuth pair or JWT secret aborts startup. | `config.py`, `lifespan.py` |

## 9.3 Known gaps (see Chapter 12)

Server-side logout/refresh do not revoke previous JWTs (no `jti` denylist yet); the JWT is stored in `localStorage` rather than an `HttpOnly` cookie (the `SESSION_COOKIE_*` settings exist for that migration); the Report Agent's `create_pull_request` tool is not gated.

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 10                                                    -->
<!-- ============================================================ -->

# CHAPTER 10 — FRONTEND APPLICATION FLOW

## 10.1 Page navigation

```mermaid
flowchart LR
    IDX["index.html<br/>Landing"] --> DOCS["docs.html"]
    IDX -- "Get started" --> AUTH["templates/auth.html"]
    AUTH -- "OAuth OK" --> DASH["dashboard.html"]
    subgraph SHELL["Authenticated app shell (sidebar)"]
        DASH --> REPOS["repositories.html"]
        DASH --> DEPL["deployments.html"]
        DASH --> AGENT["agent.html"]
        DASH --> REPORTS["reports.html"]
        DASH --> PROFILE["profile.html"]
        DASH --> SETTINGS["settings.html"]
        DASH --> IDOCS["templates/docs.html"]
    end
    REPOS -- "Deploy → success toast" --> DEPL
    REPOS -- "Generate AI report → done" --> REPORTS
    DEPL -- "Ask Agent (failed card)<br/>sessionStorage prefill" --> AGENT
    DEPL -- "Render deploy needs key" --> SETTINGS
    SHELL -- "Logout → clear localStorage" --> AUTH
```

Every authenticated page calls `initializeAppShell("<page>")` first; without `db_session_token` it bounces to `auth.html` before rendering.

## 10.2 Client-side storage

| Store | Key | Written by | Purpose |
|---|---|---|---|
| localStorage | `db_session_token` | `auth.js` | Session JWT, sent as Bearer on every request |
| localStorage | `gh_username`, `gh_avatar`, `gh_email`, `gh_user_id`, `gh_scope`, `gh_token_type`, `gh_last_login` | `auth.js` | Cached profile for instant shell hydration |
| localStorage | `db_theme` | `app-shell.js` | `light` / `dark` |
| localStorage | `db_sidebar_collapsed` | `app-shell.js` | `"true"` / `"false"` |
| localStorage | `deploybridge_recent_deployments` | `rememberDeployment()` | Legacy cache (≤ 12) used for the dashboard metric |
| sessionStorage | `oauth_state` | `auth.js` | CSRF check for the OAuth round-trip |
| sessionStorage | `agent_prefill_question`, `agent_prefill_deployment_id` | `deployments.js` | One-shot hand-off to the agent page |

## 10.3 Key UI flows

### Repositories page — deploy decision

```mermaid
flowchart TD
    A["User clicks Deploy on a repo"] --> B["POST /github-pages/detect"]
    B --> C{"recommended_platform == render?"}
    C -- no --> D["Show profile modal<br/>(auto / html / jekyll / node-static / next-static)"]
    D --> E["POST /github-pages/deploy"]
    E --> F["toast + redirect deployments.html"]
    C -- yes --> G["Suggest Render + reason"]
    G --> H{"Render connected? (GET /render/status)"}
    H -- no --> I["Link to settings.html to paste rnd_ key"]
    H -- yes --> J["POST /render/detect → pre-filled form<br/>service name, runtime, build/start, plan, env vars"]
    J --> K["POST /render/deploy"]
    K --> F
```

### Deployments page — live tracking

* Loads `GET /deployments?page=N&page_size=10` (client-side pagination), renders cards with platform badge, status pill, URL, branch, profile, timestamps.
* Filters by status/platform; search by owner/repo.
* **Auto-refresh:** every 8 s, if any card is `pending`/`building`, it posts `/refresh` for those ids only; terminal cards are never re-polled.
* **Failed cards** expose **View logs** (from `error`) and **Ask Agent**, which stores a prefilled question in `sessionStorage` and opens `agent.html`, where a session is created with `prefill_question` and the message is sent automatically.
* Render cards expose **Custom domain** → claim modal → shows `cname_target` → **Verify** button.

### Agent page — plan card

The plan card (`renderPlanCard` in `agent.js`) lists each step's summary, renders an input per `env_var_keys` entry, and has **Approve** / **Cancel** buttons that call `/approve` with `{approved, env_var_values}`. While `session_state === "awaiting_approval"` the composer is disabled; after approval the trace expands to show which tools ran.

### Theme switch

`bindThemeButton` uses `document.startViewTransition(() => toggle class)` and animates `::view-transition-new(root)` with a `clip-path: circle()` growing from the click coordinates; browsers without the API just toggle the class.

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 11                                                    -->
<!-- ============================================================ -->

# CHAPTER 11 — TESTING

## 11.1 Strategy

The backend has an **API-level integration test suite**: each test drives the real FastAPI app through `httpx.AsyncClient(transport=ASGITransport(app))`, with the PostgreSQL dependency swapped for an **in-memory SQLite** database and every external system (GitHub, Render, LLM) replaced by `unittest.mock` patches. This exercises routing, dependency injection, Pydantic validation, auth, DB writes and error mapping without network access.

## 11.2 Fixtures (`tests/conftest.py`)

| Fixture | Scope | What it provides |
|---|---|---|
| `test_engine` | session | `sqlite+aiosqlite:///:memory:` engine; `Base.metadata.create_all` |
| `db_session` | function | `AsyncSession` on the shared engine |
| `client` | function | `AsyncClient` with `app.dependency_overrides[get_db]` → test session |
| `test_user` | function | Inserted `User` (`github_id=12345`, `testuser`, placeholder GitHub token `fake_encrypted_token`, scope `repo`) |
| `auth_headers` | function | `{"Authorization": "Bearer <create_session_jwt(test_user.id)>"}` |

## 11.3 Test inventory (24 tests)

| File | Tests | Test functions and what they verify |
|---|---|---|
| `test_health.py` | 1 | `test_health_check` — `/health` returns `{"status":"Ok"}` |
| `test_auth.py` | 7 | `test_get_github_login_url` (login URL + state), `test_github_callback` (mocked `get_access_token` + `get_user_profile` → user upserted, JWT returned), `test_get_user_profile_unauthorized` (401), `test_get_user_profile`, `test_update_user_profile` (PATCH `deploy_branch`), `test_refresh_session`, `test_logout` |
| `test_github.py` | 2 | `test_get_repository_info` (mocked `GitHubService.get_repository_info` → 200 payload), `test_get_repository_info_unauthorized` (401) |
| `test_github_pages.py` | 4 | `test_detect_github_pages_profile` (mocked detect), `test_deploy_to_github_pages` (mocked deploy + `create_from_pages_deploy` called), `test_add_pages_custom_domain`, `test_verify_pages_custom_domain` |
| `test_render.py` | 4 | `test_connect_render` (mocked owner validation → key stored encrypted, owner id cached), `test_render_status`, `test_disconnect_render` (columns cleared), `test_list_render_services` (mocked `_require_render_key` + `list_services`) |
| `test_deployments.py` | 2 | `test_get_deployments` (paginated list for the test user), `test_get_deployments_unauthorized` (401) |
| `test_reports.py` | 2 | `test_get_reports` (history list), `test_get_reports_unauthorized` (401) |
| `test_agent.py` | 2 | `test_get_agent_sessions` (session list), `test_get_agent_sessions_unauthorized` (401) |

What the suite demonstrates: routing and prefixes, JWT authentication (positive and negative), Pydantic validation, real DB writes/reads through the ORM (Render connect stores the encrypted key), service-layer mocking boundaries, and the error-mapping pattern. What it does **not** yet cover: the detection heuristics themselves, `DeploymentService.refresh` mapping tables, the agent loop branches, and the report pipeline (see Chapter 13).

Run with:

```bash
cd backend
pytest -q            # uses pytest.ini → pythonpath=.
pytest --cov=src     # coverage
```

## 11.4 Manual / integration checks

* `backend/verify_integrations.py` — quick reachability test of `api.github.com` and `api.render.com` with the configured credentials.
* Phase documents (`phases/*.md`) record manual end-to-end runs: OAuth login, Pages deploy of html/jekyll/node/next repos, Render deploy of FastAPI/Node apps, failed-deploy log capture, agent approval flow.
* The Render integration notes in `services/render.py` document behaviours verified against the live API (string enums for `autoDeploy`/`clearCache`, `serviceDetails.url`, auto-deploy on create).

<div style="page-break-after: always;"></div>
<!-- ============================================================ -->
<!--  CHAPTER 12                                                    -->
<!-- ============================================================ -->

# CHAPTER 12 — CURRENT SCOPE, LIMITATIONS & ACHIEVEMENTS

## 12.1 What is in scope today (boundaries)

```mermaid
mindmap
  root((DeployBridge v1 scope))
    Identity
      GitHub OAuth only
      One GitHub account per user
    Sources
      Repositories the user can access via the repo scope
      Deploy branch = default or user preference
    Static hosting
      GitHub Pages
      Profiles html · jekyll · node-static · next-static
      Custom domains via CNAME file
    Server hosting
      Render web services
      Runtimes python · node · docker
      Plan free by default, region oregon
      Custom domains via Render API
    Tracking
      Unified deployment history
      Pull-on-view refresh, logs on failure
      Redeploy, delete history
    AI
      Report agent with PDF + e-mail
      Deploy agent with 11 tools and approval gate
      Gemini or Groq via OpenAI-compatible API
    Frontend
      Static MPA, Vanilla JS
      Hosted on GitHub Pages, backend run locally
```

## 12.2 Limitations (honest assessment from the code)

### Product / functional

| # | Limitation | Impact | Where |
|---|---|---|---|
| L1 | Only **two hosting platforms** (GitHub Pages, Render). No Vercel, Netlify, Railway, Fly.io, AWS. | Users of other platforms cannot use DeployBridge for deployment (the info modal does *detect* their config files). | `github_pages.py`, `render.py` |
| L2 | Pages supports **4 profiles**; frameworks with unusual output dirs may need the manual override or fall back to "unsupported". | Some static generators (Hugo, Docusaurus with custom paths) are not first-class. | `templates/github_pages/*.yml` |
| L3 | Render runtimes limited to **python / node / docker**; Go, Rust, Ruby, Elixir, static sites on Render not detected. | Such repos get the `docker` fallback with a "add a Dockerfile" reason. | `RenderService.detect` |
| L4 | Render **region fixed to `oregon`**, `numInstances 1`, `plan free` default. | No region/plan choice for latency or paid tiers (plan is accepted in the schema but UI defaults to free). | `render.py` |
| L5 | Pages live URL is **assumed** as `https://owner.github.io/repo` on success; user/organisation root sites (`owner.github.io` repos) and custom domains are not reflected in `url`. | Occasional wrong link on the card. | `deployment_service.py` |
| L6 | **Scheduled reports are dormant** — the cron job and `repositories` table exist, but no endpoint or UI writes `is_scheduled=true`. | Feature usable only by direct DB edits. | `scheduler.py`, `models/repository.py` |
| L7 | Report **history `total`** loads all report ids for the user before counting. | Fine for ≤ hundreds of reports; inefficient at scale (should be `COUNT(*)`). | `reports.py` |
| L8 | **No streaming** of agent responses; the browser waits for the whole loop (up to 8 LLM rounds). | Perceived latency of several seconds per message. | `deploy_agent.py`, `agent.js` |
| L9 | Deploy Agent handles **one plan per message**; if the model requests several side-effect tools at once they are executed sequentially on a single approval. | Coarse-grained approval. | `resume_after_approval` |
| L10 | **Render is API-key based**; users must create and paste a key (no OAuth). | Extra onboarding step; key has full workspace rights. | `render.py`, `settings.html` |

### Engineering / code quality

| # | Limitation | Impact | Where |
|---|---|---|---|
| E1 | `BACKEND_API_URL` **hard-coded** to `http://127.0.0.1:8000/v1` in ~8 places. | The hosted frontend cannot reach a hosted backend without editing files. | all `js/*.js`, inline templates |
| E2 | **JWT in `localStorage`**; `/auth/logout` and `/auth/refresh` do **not revoke** older tokens. | XSS could exfiltrate the token; a leaked token stays valid until `exp` (~7 days by default). | `app-shell.js`, `auth.py` |
| E3 | **Duplicated inline `<script>` blocks** in `repositories.html`, `settings.html`, `dashboard.html` (several hundred lines each) alongside the `js/` modules. | Harder maintenance; two sources of truth for some helpers. | `templates/*.html` |
| E4 | Some `print()` debugging statements remain next to the logger. | Noisy stdout in production. | `auth.py`, `render.py` |
| E5 | `GroqLLMClient` naming and `GROQ_*` variable names while the default provider is Gemini. | Confusing for new contributors. | `llm_client.py`, `config.py` |
| E6 | `agent_messages.tool_name` is overloaded to store `tool_call_id` for `tool` rows. | Works, but the column name is misleading. | `deploy_agent.py` |
| E7 | **Sync `smtplib`** inside an async background job. | Blocks the event loop for the duration of the SMTP session. | `email_service.py` |
| E8 | Header comment in `deploy_agent.py` says "9 tools" while 11 are defined. | Documentation drift. | `deploy_agent.py` |
| E9 | Two consecutive migrations touch `deployments` (`9f8ae6414de0`, `dece5564cf24`). | Slightly noisy migration history; harmless. | `alembic/versions/` |
| E10 | The Report Agent's `create_pull_request` tool is **not** behind the approval gate. | An analysis run could open a PR without confirmation (it is instructed to only when asked). | `report_agent.py` |
| E11 | Tests are **SQLite-only** and mock all services; no tests for detection heuristics, refresh mapping or the agent loop. | Regressions in business logic may go unnoticed. | `tests/` |
| E12 | Free-tier LLM constraints (8 k-token budgeting) limit how much of a large repo the agents can read per run. | Reports for very large repositories are shallower. | `report_agent.py` |

## 12.3 What has been achieved

| Area | Achievement |
|---|---|
| **End-to-end product** | A working, multi-user web application that turns a GitHub repository into a live URL on two platforms with one click. |
| **Framework-aware automation** | Deterministic detection over a shared repository context; four hardened GitHub Actions templates with package-manager detection, base-path injection, artifact discovery and asset path rewriting; Render command synthesis for FastAPI/Django/Flask/Node/Docker. |
| **Operational tracking** | Unified deployment ledger with state mapping for both platforms, log capture on failure (Actions zip logs and Render deploy logs), redeploy and custom domains with derived DNS records and verification. |
| **Agentic AI without frameworks** | Two hand-written tool-calling agents on the OpenAI SDK; persisted, replayable conversations; a genuine human-in-the-loop confirm-gate; strict secrets rule; token budgeting for free tiers. |
| **Reports pipeline** | Background generation → Markdown → PDF → Cloudinary → e-mail, with quota, status machine and on-demand PDF. |
| **Security engineering** | OAuth with state, JWT sessions, Fernet-encrypted credentials with automatic migration, proxying of third-party APIs, per-user isolation, scope checks, error-body suppression. |
| **Software engineering practice** | Layered FastAPI architecture, Pydantic contracts, async SQLAlchemy, 9 Alembic migrations, 24 async API tests, environment-based configuration with validators, phase documentation, self-hosted frontend via the same Pages workflow the product generates. |
| **Scale of work** | ≈ 10 k lines of backend Python, ≈ 3 k lines of JavaScript, ≈ 15 k lines of HTML/CSS, 41 endpoints, 6 tables, 60 commits by 3 contributors over ~3.5 months. |

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 13                                                    -->
<!-- ============================================================ -->

# CHAPTER 13 — FUTURE ENHANCEMENTS

| Priority | Enhancement | Notes |
|---|---|---|
| High | **Runtime frontend config** — a `config.js` (or `<meta>`) providing `BACKEND_API_URL`, plus a hosted backend (e.g. on Render itself) and its origin in `CORS_ALLOWED_ORIGINS`. | Removes limitation E1; makes the GitHub Pages frontend usable by anyone. |
| High | **Session hardening** — `HttpOnly`/`Secure` cookie session (settings already exist), `jti` denylist table consulted by `get_current_user`, real logout, shorter `exp` with silent refresh. | Removes E2. |
| High | **Scheduled reports UI** — endpoints `POST/DELETE /reports/schedules` writing the `repositories` table, and a toggle in the reports page. | Activates L6. |
| High | **Streaming agent responses** (Server-Sent Events) and per-tool progress events. | Improves L8; the trace list already exists as the data source. |
| Medium | **More platforms** — Vercel and Netlify (both have token-based REST APIs), Railway; abstract a `HostingProvider` interface over `GitHubPagesService`/`RenderService`. | L1 |
| Medium | **More profiles/runtimes** — Hugo, Docusaurus, MkDocs, SvelteKit static; Render Go/Ruby/Rust; static sites on Render. | L2, L3 |
| Medium | **Region/plan/instance selection** and paid-plan warnings in the Render form. | L4 |
| Medium | **Webhooks instead of polling** — GitHub `workflow_run` and Render deploy webhooks → update `deployments` server-side; frontend subscribes via SSE. | Cuts API quota usage; real-time status. |
| Medium | **Per-step approval** and plan editing in the agent card (change branch/service name before approving). | L9 |
| Medium | **Gate the Report Agent's PR tool** through the same plan mechanism. | E10 |
| Medium | **Unit tests for pure logic** — detection decision trees, status mappers, DNS derivation, `_summarize_plan_step`; PostgreSQL test container in CI. | E11 |
| Low | **Refactor duplicated inline scripts** into `js/` modules; ESLint/Prettier; remove `print()`; rename `GroqLLMClient` → `LLMClient` and `GROQ_*` → `LLM_*` (with backwards-compatible aliases). | E3, E4, E5 |
| Low | `aiosmtplib` for async e-mail; `COUNT(*)` for report totals; `tool_call_id` column. | E7, L7, E6 |
| Low | **Team/organisation support** — multiple GitHub accounts, org repos with fine-grained tokens, shared deployment history. | New capability |
| Low | **Observability** — structured JSON logs, request ids, Prometheus metrics, Sentry. | Production readiness |

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 14                                                    -->
<!-- ============================================================ -->

# CHAPTER 14 — CONCLUSION

DeployBridge set out to answer a simple question — *"my code is on GitHub; how do I get a live link without becoming a DevOps engineer?"* — and delivers a complete, working answer. The system inspects a repository, decides between static and server hosting with an explained recommendation, writes the necessary CI configuration or platform service definition on the user's behalf, triggers the deployment, and tracks it to a live URL or to a captured failure log. Custom domains, redeploys and a unified history complete the operational loop.

The project's most distinctive contribution is its **AI layer built from first principles**. Rather than adopting an agent framework, the team implemented tool calling directly on the OpenAI-compatible API, persisted every conversational step in PostgreSQL, and designed a **confirm-gate** in which the model can only *propose* side effects while a human approves them in a separate HTTP request. Coupled with the **secrets rule** — the model sees environment-variable keys but never values — this produces an assistant that is genuinely useful (it reads real logs and quotes real root causes) yet cannot act unsupervised.

From an engineering standpoint the codebase demonstrates modern Python practice: an async FastAPI stack, Pydantic v2 contracts, SQLAlchemy 2 typed models, Alembic migrations, Fernet-encrypted credentials with automatic migration, environment-driven configuration and an async API test suite. The framework-free frontend shows that a polished, themed, animated multi-page application can be built with plain HTML, CSS and JavaScript.

The limitations identified in Chapter 12 are real but tractable: a runtime API URL, cookie sessions with revocation, a schedules UI, streaming responses and broader platform coverage are the natural next steps, and the layered architecture leaves clear seams for each of them. As delivered, DeployBridge is a solid foundation and a strong demonstration of how deterministic automation and agentic AI can be combined responsibly.

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  CHAPTER 15                                                    -->
<!-- ============================================================ -->

# CHAPTER 15 — REFERENCES

1. DeployBridge source repository — https://github.com/gajjarkav/DeployBridge
2. FastAPI documentation — https://fastapi.tiangolo.com/
3. Starlette documentation — https://www.starlette.io/
4. Uvicorn documentation — https://www.uvicorn.org/
5. Pydantic v2 & pydantic-settings — https://docs.pydantic.dev/
6. SQLAlchemy 2.0 (asyncio extension) — https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
7. asyncpg — https://magicstack.github.io/asyncpg/
8. Alembic — https://alembic.sqlalchemy.org/
9. httpx — https://www.python-httpx.org/
10. PyJWT — https://pyjwt.readthedocs.io/
11. cryptography — Fernet (symmetric encryption) — https://cryptography.io/en/latest/fernet/
12. OpenAI Python SDK — https://github.com/openai/openai-python
13. OpenAI Function/Tool Calling guide — https://platform.openai.com/docs/guides/function-calling
14. Google Gemini OpenAI-compatibility — https://ai.google.dev/gemini-api/docs/openai
15. Groq OpenAI-compatible API — https://console.groq.com/docs/openai
16. APScheduler 3.x — https://apscheduler.readthedocs.io/en/3.x/
17. GitHub REST API — https://docs.github.com/en/rest
18. GitHub OAuth Apps (web application flow) — https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
19. GitHub Pages API & custom domains — https://docs.github.com/en/pages
20. GitHub Actions: `actions/configure-pages`, `upload-pages-artifact`, `deploy-pages`, `jekyll-build-pages` — https://github.com/actions
21. Render REST API — https://api-docs.render.com/reference/introduction
22. Cloudinary Python SDK — https://cloudinary.com/documentation/django_integration
23. xhtml2pdf — https://xhtml2pdf.readthedocs.io/
24. Python-Markdown — https://python-markdown.github.io/
25. pytest & pytest-asyncio — https://docs.pytest.org/ , https://pytest-asyncio.readthedocs.io/
26. Tailwind CSS (Play CDN) — https://tailwindcss.com/docs/installation/play-cdn
27. GSAP & ScrollTrigger — https://gsap.com/docs/v3/
28. Lenis smooth scroll — https://github.com/darkroomengineering/lenis
29. marked.js — https://marked.js.org/
30. MDN Web Docs: Fetch API, Web Storage API, View Transitions API — https://developer.mozilla.org/
31. RFC 6749 (OAuth 2.0), RFC 6750 (Bearer Token Usage), RFC 7519 (JSON Web Token) — https://www.rfc-editor.org/
32. Mermaid diagram syntax — https://mermaid.js.org/

<div style="page-break-after: always;"></div>

<!-- ============================================================ -->
<!--  APPENDICES                                                    -->
<!-- ============================================================ -->

# APPENDIX A — ENDPOINT QUICK REFERENCE (41)

| # | Method | Path | Auth | Success | Notes |
|---|---|---|---|---|---|
| 1 | GET | `/v1/health` | — | 200 | liveness |
| 2 | GET | `/v1/auth/login` | — | 200 | `{login_url, state}` |
| 3 | GET | `/v1/auth/callback?code=` | — | 200 | upsert user, returns JWT |
| 4 | GET | `/v1/auth/profile` | JWT | 200 | profile + `render_connected` |
| 5 | PATCH | `/v1/auth/profile` | JWT | 200 | `deploy_branch` |
| 6 | POST | `/v1/auth/refresh` | JWT | 200 | new JWT |
| 7 | POST | `/v1/auth/logout` | — | 200 | no-op |
| 8 | POST | `/v1/github/repos/info` | JWT | 200 | 9-call repository explorer |
| 9 | GET | `/v1/github/user` | JWT | 200 | proxy |
| 10 | GET | `/v1/github/user/repos` | JWT | 200 | proxy with query pass-through |
| 11 | POST | `/v1/github-pages/detect` | JWT | 200 | profile or Render recommendation |
| 12 | POST | `/v1/github-pages/deploy` | JWT | 200 | upsert workflow, configure Pages, dispatch, row `pending` |
| 13 | POST | `/v1/github-pages/custom-domains/{owner}/{repo}` | JWT | 200 | commit CNAME, DNS record |
| 14 | POST | `/v1/github-pages/custom-domains/{owner}/{repo}/{domain}/verify` | JWT | 200 | status + HTTPS enforce |
| 15 | POST | `/v1/render/connect` | JWT | 200 | validate key, store encrypted |
| 16 | DELETE | `/v1/render/connect` | JWT | 200 | forget key |
| 17 | GET | `/v1/render/status` | JWT | 200 | connected? |
| 18 | POST | `/v1/render/detect` | JWT | 200 | runtime + commands |
| 19 | POST | `/v1/render/deploy` | JWT | 200 | create service, row `building` |
| 20 | GET | `/v1/render/services` | JWT | 200 | list |
| 21 | GET | `/v1/render/services/{id}` | JWT | 200 | detail + latest deploy |
| 22 | POST | `/v1/render/services/{id}/redeploy` | JWT | 200 | new deploy |
| 23 | POST | `/v1/render/services/{id}/custom-domain` | JWT | 200 | add domain |
| 24 | POST | `/v1/render/services/{id}/custom-domain/{name}/verify` | JWT | 200 | verify |
| 25 | GET | `/v1/deployments` | JWT | 200 | paginated ≤ 50 |
| 26 | GET | `/v1/deployments/{id}` | JWT | 200 | detail |
| 27 | POST | `/v1/deployments/{id}/refresh` | JWT | 200 | poll platform |
| 28 | POST | `/v1/deployments/{id}/redeploy` | JWT | 200 | re-dispatch / new deploy |
| 29 | DELETE | `/v1/deployments/{id}` | JWT | 200 | delete history row |
| 30 | POST | `/v1/reports/generate` | JWT | **202** | quota 10/24 h → 429 |
| 31 | GET | `/v1/reports/history` | JWT | 200 | paginated |
| 32 | GET | `/v1/reports/{id}` | JWT | 200 | markdown + status |
| 33 | DELETE | `/v1/reports/{id}` | JWT | 200 | |
| 34 | POST | `/v1/reports/{id}/send-email` | JWT | 200 | background resend |
| 35 | GET | `/v1/reports/{id}/pdf` | JWT | 200 | `application/pdf` |
| 36 | POST | `/v1/agent/sessions` | JWT | **201** | optional prefill |
| 37 | GET | `/v1/agent/sessions` | JWT | 200 | paginated |
| 38 | GET | `/v1/agent/sessions/{id}` | JWT | 200 | with messages |
| 39 | DELETE | `/v1/agent/sessions/{id}` | JWT | 200 | cascade |
| 40 | POST | `/v1/agent/sessions/{id}/messages` | JWT | 200 | run loop |
| 41 | POST | `/v1/agent/messages/{id}/approve` | JWT | 200 | approve / cancel plan |

Error codes used: 400 (bad input / missing token / invalid key), 401 (no or bad JWT), 402 (Render quota), 403 (scope / permission), 404 (not found or not owned), 409 (GitHub conflict pass-through), 422 (validation), 429 (quota / rate limit), 500 (decryption / unexpected), 502 (upstream 5xx), 503 (LLM not configured).

<div style="page-break-after: always;"></div>

# APPENDIX B — SETUP & RUN GUIDE

### B.1 Prerequisites

* Python **3.12+**, PostgreSQL (local or hosted), Git.
* A GitHub **OAuth App** (callback URL = the frontend `auth.html` URL, e.g. `http://127.0.0.1:5500/frontend/templates/auth.html`).
* Optional: Gemini or Groq API key; Render API key (per user, entered in Settings); Cloudinary account; SMTP credentials.

### B.2 Backend

```bash
git clone https://github.com/gajjarkav/DeployBridge.git
cd DeployBridge
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # or backend/requirements.txt for API only

cp backend/.env.example backend/.env
# edit backend/.env: DATABASE_URL, GITHUB_CLIENT_ID/SECRET, JWT_SECRET_KEY,
# GITHUB_TOKEN_ENCRYPTION_KEY (python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"),
# GROQ_API_KEY / GROQ_BASE_URL / GROQ_MODEL, optional Cloudinary + SMTP

alembic upgrade head                                   # run from repo root
cd backend
python -m src.main                                     # or: uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# Swagger UI → http://127.0.0.1:8000/docs
```

### B.3 Frontend

Open the `frontend/` folder with VS Code **Live Server** (port 5500/5501 — already in the CORS allow-list) and browse to `frontend/index.html` → *Get started*. If the backend runs elsewhere, change `BACKEND_API_URL` in the JS files and add the frontend origin to `CORS_ALLOWED_ORIGINS`.

### B.4 Tests

```bash
cd backend
pytest -q
```

### B.5 Typical first run

1. Sign in with GitHub (grant `repo` and `workflow`).
2. *Repositories* → click **Deploy** on a static repo → confirm profile → watch it go `pending → building → live` on *Deployments*.
3. *Settings* → paste a Render API key → back to *Repositories* → deploy a FastAPI/Node repo to Render.
4. *Agent* → "Why did my last deploy fail?" or "Deploy owner/repo to Render".
5. *Repositories* → **Generate AI report** → view on *Reports*, download PDF.

<div style="page-break-after: always;"></div>

# APPENDIX C — GLOSSARY

| Term | Meaning in this report |
|---|---|
| **Agent (LLM agent)** | A loop in which a language model chooses *tools* to call, receives their results, and continues until it can answer. |
| **Tool calling / function calling** | The OpenAI API feature where the model returns structured `tool_calls` (name + JSON arguments) instead of text. |
| **Confirm-gate / human-in-the-loop** | DeployBridge's rule that side-effect tools are only *proposed* by the model and executed after a user clicks Approve. |
| **Plan** | The persisted list of proposed side-effect steps (`role=assistant_plan`). |
| **Read-only tool** | A tool that only reads data (detect, read file, logs, lists); auto-executed. |
| **Side-effect tool** | A tool that changes the world (deploy, PR, custom domain); gated. |
| **Profile (Pages)** | The kind of static site: `html`, `jekyll`, `node-static`, `next-static`. |
| **Runtime (Render)** | How Render builds/runs the service: `python`, `node`, `docker`. |
| **Workflow** | A GitHub Actions YAML file under `.github/workflows/`. |
| **workflow_dispatch** | Manually triggering a workflow through the API. |
| **Deployment row** | A record in the `deployments` table tracking one deploy on one platform. |
| **Refresh (pull-on-view)** | Asking the platform for the current status only while the user is looking. |
| **Fernet** | Symmetric authenticated encryption scheme from the `cryptography` library used for stored tokens. |
| **JWT** | JSON Web Token — the signed session token stored in the browser. |
| **OAuth `state`** | Random value that ties the OAuth redirect back to the tab that started it (CSRF protection). |
| **CNAME / A record** | DNS records used to point a custom domain to GitHub Pages or Render. |
| **Alembic revision** | One versioned database schema change. |
| **MPA** | Multi-Page Application — one HTML file per screen, no client-side router. |
| **TPM** | Tokens-per-minute limit imposed by LLM providers; motivates per-step token budgeting. |

---

<div align="center">

*End of Report — DeployBridge · Noble University, Junagadh · 2025–2026*

</div>
