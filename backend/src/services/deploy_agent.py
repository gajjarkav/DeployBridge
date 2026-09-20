# ------------------------------------------------------------------------------
# WHAT THIS IS
#   The Deployment Agent — DeployBridge's second LLM agent. The first one
#   (report_agent.py) writes analysis reports; this one drives deploys.
#
#   ┌─────────────┐
#   │     LLM     │  decides WHAT (plan, choose tools, interpret, explain).
#   │  (Gemini)   │  Never touches the internet itself.
#   └──────┬──────┘
#          │ tool calls
#   ┌──────▼─────────────────────────────┐
#   │  AGENT LOOP (this file)             │  MAX_STEPS cap, output truncation,
#   │  tool registry + confirm-gate +     │  secret redaction + trace + full
#   │  secret redaction + trace           │  audit.
#   └──────┬──────────────────────────────┘
#          │
#     ┌────┴─────────┬──────────────┬─────────────┐
#     ▼              ▼              ▼             ▼
#  GitHubPages    Render        GitHub         DB
#  Service        Service       Contents API   (deployments)
#  ────── deterministic Python you already wrote & trust ──────
#
#   "The LLM decides WHAT, the Python decides HOW."
#
# TOOLSET (9 tools, two classes)
#   READ-ONLY (auto-approved, safe):
#     detect_stack, read_repo_file, get_render_status,
#     get_render_logs, list_deployments
#   SIDE-EFFECT (gated — need user confirmation via the confirm-gate):
#     deploy_github_pages, deploy_render,
#     create_pull_request (reuse report agent's, verbatim),
#     add_render_custom_domain
#
# THE CONFIRM-GATE
#   When the LLM wants a side-effect tool, the loop PAUSES. The plan is
#   persisted as a role="assistant_plan" AgentMessage. The UI shows an
#   [Approve] [Cancel] card. Approve → executor runs the real functions
#   → results re-enter the conversation → LLM continues.
#
# SECRETS RULE (subtle, mention it explicitly in the viva)
#   Env-var VALUES never enter the LLM conversation or the trace. The
#   LLM only ever sees the KEYS (from .env.example). Values are collected
#   by the UI form and merged by Python at execution time. Result:
#   nothing sensitive is ever sent to the model provider, and traces
#   are safe to display/store.
# ------------------------------------------------------------------------------
from __future__ import annotations

import json
from typing import Any
import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.crypto import decrypt_secret, TokenDecryptionError
from ..core.exception import GitHubAPIError, GitHubPagesError, RenderError
from ..core.logger import logger
from ..models.agent_session import AgentMessage, AgentSession
from ..models.deployment import Deployment
from ..models.user import User
from ..schemas.render import RenderDeployRequest, RenderEnvVar
from ..schemas.github_pages import GitHubPagesDeployRequest
from ..services.github import GitHubService
from ..services.github_pages import GitHubPagesService
from ..services.render import RenderService
from ..services.llm_client import GroqLLMClient, LLMClientError
from ..services.deployment_service import DeploymentService


# ---------------------------------------------------------------------------
# System prompt — the rules you give the agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are DeployBridge's Deployment Agent.

Your job: help the user deploy GitHub repositories to Render (server apps) or
GitHub Pages (static sites), diagnose failed deploys by reading their logs,
and answer questions about the user's deployment history.

## Operating rules

1. ALWAYS detect the stack before deploying. Run `detect_stack` first — never
   guess a runtime or profile from the repo name alone.

2. NEVER invent env-var values. If `.env.example` lists required keys, you may
   READ the file with `read_repo_file` to enumerate them, but the user must
   supply values. Tell the user which keys are needed and stop. Do not proceed
   to deploy until values are confirmed.

3. CONFIRM before any side-effect. When you want to call a deploy_*, create_pull_request,
   or add_*_custom_domain tool, STOP and return a `plan`. The user will see an
   Approve/Cancel card. After approval, the system re-invokes you with the
   result and you continue.

4. If a deploy failed, READ THE LOGS before guessing. Use `get_render_logs` for
   Render, or use the failed deployment's `error` field for both platforms.
   Quote the actual log line that reveals the root cause, then explain.

5. Always end with EITHER the live URL OR the exact next step the user should take.
   "Your app is live at https://notes-api.onrender.com" OR
   "Add a CNAME record for `notes` pointing to `my-app.onrender.com`, then click Verify."

6. Be brief. Prefer bullet lists over paragraphs. The user is looking at a chat UI.

## Classic failures you will recognize

- Bound to localhost / 127.0.0.1 instead of 0.0.0.0:$PORT (Render)
- Wrong start command / module path (src.main:app vs main:app)
- gunicorn/uvicorn missing from requirements.txt
- npm ci failing on out-of-sync lockfile
- Crash on boot: missing env var (KeyError on os.environ)
- Python version mismatch (e.g. syntax error on 3.10+ only constructs)

## Tool taxonomy

READ-ONLY (auto-approved): detect_stack, read_repo_file, get_render_status,
get_render_logs, list_deployments, list_repositories, analyze_repository.

SIDE-EFFECT (need user approval): deploy_github_pages, deploy_render,
create_pull_request, add_render_custom_domain.

## Output contract

When you want to call a SIDE-EFFECT tool, your final message MUST be a JSON
object with this exact shape:

```
{"plan": [{"tool": "deploy_render", "args": {...}, "summary": "what this will do"}]}
```

The system intercepts this before any tool actually runs, persists it as a
plan, and surfaces an Approve/Cancel card to the user.

For READ-ONLY tools, use normal OpenAI tool-calling — the system runs them
automatically.

Anything else you say is shown to the user as plain text.
"""


MAX_STEPS = 8
MAX_OUTPUT_TOKENS = 4000
# Cap on tool result size that gets fed back to the LLM. Same as report_agent.
MAX_TOOL_RESULT_CHARS = 30000


# ---------------------------------------------------------------------------
# Tool schemas (OpenAI function-calling format)
# ------------------------------------------------------------------------------

# READ-ONLY tools — agent runs them automatically, no approval needed.
READONLY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "detect_stack",
            "description": (
                "Inspect a GitHub repo via the user's GitHub token and recommend "
                "either a Render runtime (python/node/docker) or a GitHub Pages "
                "profile (html/jekyll/node-static/next-static). ALWAYS call this "
                "before deploying — never guess."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner":     {"type": "string", "description": "GitHub username/org"},
                    "repo":      {"type": "string", "description": "Repository name"},
                },
                "required": ["owner", "repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_repo_file",
            "description": (
                "Read the text content of a file from the repo. Use to inspect "
                "code, configs (.env.example, package.json, requirements.txt, "
                "next.config.js), and READMEs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner":  {"type": "string"},
                    "repo":   {"type": "string"},
                    "path":   {"type": "string", "description": "Exact path, e.g. '.env.example'"},
                },
                "required": ["owner", "repo", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_render_status",
            "description": "Get a Render service's current build/live status + latest deploy info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "Render srv-... id"},
                },
                "required": ["service_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_render_logs",
            "description": (
                "Fetch the build/runtime log lines for a Render deploy. Use to "
                "diagnose why a deploy failed — quote the line that reveals the "
                "root cause in your explanation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "deploy_id":  {"type": "string", "description": "Render deploy id (dep-...)"},
                },
                "required": ["service_id", "deploy_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_deployments",
            "description": (
                "List the user's recent deployments from DeployBridge's DB. "
                "Use to answer 'what's the status of my sites?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max rows (default 10)", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_repositories",
            "description": "List the authenticated user's GitHub repositories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of repos to return (default 50)", "default": 50},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_repository",
            "description": "Fetch comprehensive information about a specific GitHub repository, including tech stack, branches, and commits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                },
                "required": ["owner", "repo"],
            },
        },
    },
]

# SIDE-EFFECT tools — agent must return a plan for these; the loop pauses.
SIDEEFFECT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "deploy_github_pages",
            "description": (
                "Deploy a static site repo to GitHub Pages. SIDE-EFFECT: writes "
                "a workflow file to the repo's .github/workflows/, configures "
                "Pages, and dispatches the workflow. Requires user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner":    {"type": "string"},
                    "repo":     {"type": "string"},
                    "profile":  {"type": "string",
                                 "description": "Pages profile; use 'auto' if unsure",
                                 "enum": ["auto", "html", "jekyll", "node-static", "next-static"]},
                },
                "required": ["owner", "repo", "profile"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deploy_render",
            "description": (
                "Create a Render web service and trigger a deploy. SIDE-EFFECT: "
                "creates a real Render service and starts a build. Requires "
                "user approval. Env-var VALUES are NOT in this call — they are "
                "collected separately by the UI and merged server-side."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner":          {"type": "string"},
                    "repo":           {"type": "string"},
                    "branch":         {"type": "string"},
                    "service_name":   {"type": "string", "description": "Becomes <name>.onrender.com"},
                    "runtime":        {"type": "string", "enum": ["python", "node", "docker"]},
                    "build_command":  {"type": "string"},
                    "start_command":  {"type": "string"},
                    "dockerfile_path":{"type": "string", "description": "Required if runtime=docker"},
                    "env_var_keys":   {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Env-var KEYS the deploy needs (e.g. ['DATABASE_URL', 'JWT_SECRET']). "
                                       "VALUES are collected from the user by the UI form — never put "
                                       "values in this list.",
                    },
                },
                "required": ["owner", "repo", "branch", "service_name", "runtime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pull_request",
            "description": (
                "Create a new file (or update an existing one) in a new branch, "
                "then open a PR. Use to suggest a code/config fix the user "
                "should merge. SIDE-EFFECT: writes to the repo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner":          {"type": "string"},
                    "repo":           {"type": "string"},
                    "file_path":      {"type": "string", "description": "Path in the repo to create/update"},
                    "content":        {"type": "string", "description": "Exact file content"},
                    "commit_message": {"type": "string"},
                    "pr_title":       {"type": "string"},
                    "pr_body":        {"type": "string"},
                },
                "required": ["owner", "repo", "file_path", "content", "commit_message", "pr_title", "pr_body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_render_custom_domain",
            "description": (
                "Attach a custom domain to a Render service. SIDE-EFFECT: writes "
                "to Render's API. Returns the CNAME record the user must add at "
                "their DNS provider."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {"type": "string"},
                    "domain":     {"type": "string", "description": "e.g. notes.kumar.dev (no https://, no path)"},
                },
                "required": ["service_id", "domain"],
            },
        },
    },
]

ALL_TOOLS = READONLY_TOOLS + SIDEEFFECT_TOOLS

SIDEEFFECT_TOOL_NAMES = {t["function"]["name"] for t in SIDEEFFECT_TOOLS}


# ---------------------------------------------------------------------------
# Agent runner
# ------------------------------------------------------------------------------

class DeployAgentRunner:
    """One instance per user message. Holds the conversation state.

    Lifecycle:
      1. __init__ loads the user row, decrypts tokens, builds the LLM client.
      2. run_user_message(content) — the entry point. Appends a role=user
         message to the session, runs the loop, returns the final
         assistant message + trace.
      3. resume_after_approval(plan_msg_id, approved, env_var_values) — called
         by the /approve endpoint when the user clicks Approve on a plan.
         Executes the planned side-effects, then continues the loop.
    """

    def __init__(
        self,
        db: AsyncSession,
        user: User,
        session: AgentSession,
    ) -> None:
        self.db = db
        self.user = user
        self.session = session
        self.llm = GroqLLMClient()  # raises LLMClientError if GROQ_API_KEY missing
        self.trace: list[str] = []

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------
    def _github_token(self) -> str:
        if not self.user.github_token:
            raise GitHubAPIError(
                message="GitHub token missing",
                detail="Re-authenticate via GitHub OAuth to use the agent.",
            )
        return decrypt_secret(self.user.github_token)

    def _render_api_key(self) -> str:
        if not self.user.render_api_key:
            raise RenderError(
                message="Render integration not connected",
                detail="Visit Settings → Integrations → Connect Render.",
            )
        return decrypt_secret(self.user.render_api_key)

    # ------------------------------------------------------------------
    # Message helpers
    # ------------------------------------------------------------------
    async def _load_messages_for_llm(self) -> list[dict[str, Any]]:
        """Read every message in this session, rebuild the OpenAI-shape list.

        We skip DeployBridge-specific roles (assistant_plan, user_approval)
        because they're UI state, not LLM context — the LLM only sees
        user / system / assistant / assistant_tool_call / tool rows.
        """
        stmt = (
            select(AgentMessage)
            .where(AgentMessage.session_id == self.session.id)
            .order_by(AgentMessage.created_at)
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        messages: list[dict[str, Any]] = []
        # System prompt: prepend once at the top.
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

        for m in rows:
            if m.role == "user":
                messages.append({"role": "user", "content": m.content or ""})
            elif m.role == "assistant":
                messages.append({"role": "assistant", "content": m.content or ""})
            elif m.role == "assistant_tool_call":
                # Replay the raw tool_calls payload so the LLM remembers what it asked for.
                raw = json.loads(m.content) if m.content else {}
                messages.append({
                    "role": "assistant",
                    "content": raw.get("content", ""),
                    "tool_calls": raw.get("tool_calls", []),
                })
            elif m.role == "tool":
                messages.append({
                    "role": "tool",
                    "tool_call_id": m.tool_name or "",  # we stored the call_id in tool_name
                    "name": m.tool_name or "tool",
                    "content": m.content or "",
                })
            # assistant_plan / user_approval are skipped — they're UI state.

        return messages

    async def _append_message(
        self,
        role: str,
        content: str | None = None,
        *,
        tool_name: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> AgentMessage:
        msg = AgentMessage(
            session_id=self.session.id,
            user_id=self.user.id,
            role=role,
            content=content,
            tool_name=tool_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    # ------------------------------------------------------------------
    # Public entry — POST /v1/agent/sessions/{id}/messages
    # ------------------------------------------------------------------
    async def run_user_message(self, content: str) -> dict[str, Any]:
        """Append the user's message, run the loop, return final state."""
        # If this is the first user message, use it as the session title.
        if self.session.title in ("New chat", ""):
            self.session.title = content[:80]

        await self._append_message("user", content)

        return await self._run_loop()

    # ------------------------------------------------------------------
    # Public entry — POST /v1/agent/messages/{id}/approve
    # ------------------------------------------------------------------
    async def resume_after_approval(
        self,
        plan_message_id,
        approved: bool,
        env_var_values: dict[str, str] | None,
    ) -> dict[str, Any]:
        """User clicked Approve or Cancel on a plan card.

        - approved=True:  execute the planned side-effects, append their
                          tool results, then continue the loop.
        - approved=False: append a role=user_approval="cancelled" row and
                          let the LLM acknowledge the cancellation.
        """
        plan_msg = await self.db.get(AgentMessage, plan_message_id)
        if plan_msg is None or plan_msg.session_id != self.session.id:
            raise LookupError("Plan message not found")

        if not approved:
            await self._append_message(
                "user_approval",
                "cancelled",
                tool_name="user_approval",
            )
            return await self._run_loop()

        # Approved — execute each planned tool call.
        plan = json.loads(plan_msg.content or "[]")
        await self._append_message(
            "user_approval",
            "approved",
            tool_name="user_approval",
        )

        for step in plan:
            tool = step.get("tool")
            args = step.get("args", {})
            self.trace.append(f"exec: {tool}({json.dumps(args)[:120]})")
            try:
                result = await self._execute_sideeffect_tool(
                    tool, args, env_var_values=env_var_values
                )
                # The LLM expects a tool_call_id when we replay these as
                # role=tool messages. We don't have a real one (the LLM
                # returned a plan, not a tool_call), so synthesize one and
                # also store it as a assistant_tool_call so the next loop
                # iteration can find it.
                synth_id = f"planexec_{plan_message_id}_{tool}"
                await self._append_message(
                    "assistant_tool_call",
                    content=json.dumps({
                        "content": "",
                        "tool_calls": [{
                            "id": synth_id,
                            "type": "function",
                            "function": {"name": tool, "arguments": json.dumps(args)},
                        }],
                    }),
                    tool_name=tool,
                )
                await self._append_message(
                    "tool",
                    content=str(result)[:MAX_TOOL_RESULT_CHARS],
                    tool_name=tool,
                )
            except (RenderError, GitHubAPIError, GitHubPagesError) as exc:
                # Surface the error back to the LLM so it can adapt.
                self.trace.append(f"exec error: {tool} → {exc.message}")
                await self._append_message(
                    "tool",
                    content=f"Error executing {tool}: {exc.message}. Detail: {exc.detail}",
                    tool_name=tool,
                )

        return await self._run_loop()

    # ------------------------------------------------------------------
    # THE LOOP
    # ------------------------------------------------------------------
    async def _run_loop(self) -> dict[str, Any]:
        """Runs the LLM ↔ tools ↔ results loop until either:
          - The LLM returns plain text (no tool_calls, no plan) → done
          - The LLM returns a JSON plan → pause, persist as assistant_plan
          - MAX_STEPS is exhausted → force a final summary
        """
        self.session.state = "running"
        await self.db.flush()

        total_prompt = 0
        total_completion = 0
        final_message: AgentMessage | None = None

        for step in range(MAX_STEPS):
            logger.info(f"Agent loop step {step + 1}/{MAX_STEPS} session={self.session.id}")
            messages = await self._load_messages_for_llm()

            try:
                step_max_tokens = min(4000, max(500, 8000 - total_prompt - 500))
                result = await self.llm.chat_completion(
                    messages=messages,
                    temperature=0.2,
                    max_tokens=step_max_tokens,
                    tools=ALL_TOOLS,
                )
            except LLMClientError as exc:
                self.session.state = "error"
                await self.db.flush()
                await self._append_message(
                    "assistant",
                    f"⚠️ The AI provider is unavailable: {exc.message}. "
                    f"Please try again in a moment.",
                )
                return {
                    "session_state": "error",
                    "message": None,
                    "trace": self.trace,
                }

            total_prompt += result.get("prompt_tokens", 0)
            total_completion += result.get("completion_tokens", 0)

            tool_calls = result.get("tool_calls")
            content = (result.get("content") or "").strip()

            # ----- Branch A: side-effect plan -----
            # The LLM signaled intent to call a SIDE-EFFECT tool. We PAUSE
            # here — do NOT execute — and persist the plan as a
            # role=assistant_plan message. The UI shows an Approve/Cancel card.
            if tool_calls:
                sideeffect_calls = [
                    tc for tc in tool_calls
                    if tc.function.name in SIDEEFFECT_TOOL_NAMES
                ]
                readonly_calls = [
                    tc for tc in tool_calls
                    if tc.function.name not in SIDEEFFECT_TOOL_NAMES
                ]

                if sideeffect_calls:
                    plan = [
                        {
                            "tool": tc.function.name,
                            "args": json.loads(tc.function.arguments or "{}"),
                            "summary": self._summarize_plan_step(tc.function.name,
                                                                  json.loads(tc.function.arguments or "{}")),
                        }
                        for tc in sideeffect_calls
                    ]
                    plan_msg = await self._append_message(
                        "assistant_plan",
                        json.dumps(plan),
                        prompt_tokens=total_prompt,
                        completion_tokens=total_completion,
                    )
                    self.session.state = "awaiting_approval"
                    await self.db.flush()
                    return {
                        "session_state": "awaiting_approval",
                        "message": _message_to_response(plan_msg, plan=plan),
                        "trace": self.trace,
                    }

                # If only readonly tools were requested, run them now.
                if readonly_calls:
                    # Replay the assistant message with tool_calls so the
                    # next loop iteration sees a consistent conversation.
                    raw_msg = result.get("raw_message")
                    if raw_msg:
                        await self._append_message(
                            "assistant_tool_call",
                            content=json.dumps({
                                "content": content,
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": "function",
                                        "function": {
                                            "name": tc.function.name,
                                            "arguments": tc.function.arguments,
                                        },
                                    }
                                    for tc in readonly_calls
                                ],
                            }),
                        )
                    for tc in readonly_calls:
                        try:
                            args = json.loads(tc.function.arguments or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        tool_name = tc.function.name
                        self.trace.append(f"{tool_name}({json.dumps(args)[:100]})")
                        try:
                            tool_result = await self._execute_readonly_tool(tool_name, args)
                        except (RenderError, GitHubAPIError, GitHubPagesError) as exc:
                            tool_result = f"Error: {exc.message}. Detail: {exc.detail}"
                        await self._append_message(
                            "tool",
                            content=str(tool_result)[:MAX_TOOL_RESULT_CHARS],
                            tool_name=tc.id,  # store the call_id so _load_messages_for_llm can replay it
                        )
                    continue  # next loop iteration

            # ----- Branch B: final answer -----
            # No tool_calls OR all tool_calls were handled. Treat content
            # as the final answer.
            if content:
                final_message = await self._append_message(
                    "assistant",
                    content,
                    prompt_tokens=total_prompt,
                    completion_tokens=total_completion,
                )
                self.session.state = "idle"
                await self.db.flush()
                return {
                    "session_state": "idle",
                    "message": _message_to_response(final_message),
                    "trace": self.trace,
                }

            # Empty content with no tool_calls — the LLM produced nothing
            # useful. Nudge it once.
            if step < MAX_STEPS - 1:
                await self._append_message(
                    "user",
                    "(Please respond with your next action or your final answer.)",
                )
                continue

            # Out of steps — force a summary.
            break

        # Force a final summary without tools.
        messages = await self._load_messages_for_llm()
        messages.append({
            "role": "user",
            "content": "You have reached the maximum number of tool steps. "
                       "Summarize what you've done so far and what the user should do next.",
        })
        result = await self.llm.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=MAX_OUTPUT_TOKENS,
            tools=None,
        )
        total_prompt += result.get("prompt_tokens", 0)
        total_completion += result.get("completion_tokens", 0)
        final_message = await self._append_message(
            "assistant",
            (result.get("content") or "").strip(),
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
        )
        self.session.state = "idle"
        await self.db.flush()
        return {
            "session_state": "idle",
            "message": _message_to_response(final_message),
            "trace": self.trace,
        }

    # ------------------------------------------------------------------
    # READ-ONLY tool executor — auto-approved
    # ------------------------------------------------------------------
    async def _execute_readonly_tool(self, name: str, args: dict[str, Any]) -> str:
        if name == "detect_stack":
            owner = args.get("owner", "")
            repo = args.get("repo", "")
            output = []
            try:
                pages_det = await GitHubPagesService.detect(
                    github_token=self._github_token(),
                    owner=owner,
                    repository=repo,
                    preferred_branch=self.user.deploy_branch,
                )
                output.append(
                    f"GitHub Pages recommendation: profile={pages_det.detected_profile}, "
                    f"branch={pages_det.branch}, reason={pages_det.reason}, "
                    f"recommended_platform={pages_det.recommended_platform}."
                )
            except GitHubPagesError as exc:
                output.append(f"GitHub Pages detection failed: {exc.message}")

            try:
                render_det = await RenderService.detect(
                    github_token=self._github_token(),
                    owner=owner,
                    repository=repo,
                    preferred_branch=self.user.deploy_branch,
                )
                output.append(
                    f"Render recommendation: runtime={render_det.runtime}, "
                    f"build={render_det.build_command}, start={render_det.start_command}, "
                    f"branch={render_det.branch}, reason={render_det.reason}. "
                    f"Suggested env vars: {list(render_det.env_var_suggestions.keys())}."
                )
            except RenderError as exc:
                output.append(f"Render detection failed: {exc.message}")

            return "\n\n".join(output)

        if name == "read_repo_file":
            owner = args.get("owner", "")
            repo = args.get("repo", "")
            path = args.get("path", "")
            return await GitHubService.read_file_content(
                token=self._github_token(),
                owner=owner,
                repo=repo,
                path=path,
            )

        if name == "get_render_status":
            api_key = self._render_api_key()
            service_id = args.get("service_id", "")
            detail = await RenderService.get_service(api_key=api_key, service_id=service_id)
            return (
                f"Service: {detail.name} ({detail.service_id}). "
                f"Status: {detail.status}, latest deploy: {detail.latest_deploy_status}. "
                f"URL: {detail.url or '(not yet live)'}. "
                f"Deploy id: {detail.latest_deploy_id or 'none'}."
            )

        if name == "get_render_logs":
            api_key = self._render_api_key()
            service_id = args.get("service_id", "")
            deploy_id = args.get("deploy_id", "")
            logs = await RenderService.get_deploy_logs(
                api_key=api_key,
                service_id=service_id,
                deploy_id=deploy_id,
            )
            return logs or "(no log lines returned yet — the deploy may have just started)"

        if name == "list_deployments":
            limit = int(args.get("limit", 10))
            list_resp = await DeploymentService.list_for_user(
                self.db, self.user.id, page=1, page_size=limit
            )
            lines = []
            for d in list_resp.items:
                lines.append(
                    f"- {d.platform}:{d.owner}/{d.repo} status={d.status} "
                    f"profile={d.profile} url={d.url or 'n/a'}"
                )
            return "\n".join(lines) if lines else "No deployments in history."

        if name == "list_repositories":
            limit = int(args.get("limit", 50))
            token = self._github_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
                resp = await client.get(
                    "https://api.github.com/user/repos", 
                    params={"sort": "updated", "per_page": limit},
                    headers=headers
                )
                if resp.status_code == 200:
                    repos = resp.json()
                    summary = []
                    for r in repos:
                        summary.append(f"- {r.get('full_name')} (stars: {r.get('stargazers_count')}, language: {r.get('language')})")
                    if not summary:
                        return "No repositories found."
                    return "\n".join(summary)
                else:
                    return f"Failed to fetch repositories: {resp.status_code} {resp.text}"

        if name == "analyze_repository":
            owner = args.get("owner", "")
            repo = args.get("repo", "")
            token = self._github_token()
            try:
                info = await GitHubService.get_repository_info(token=token, owner=owner, repo=repo)
                if not info.success:
                    return f"Analysis failed: {info.message}"
                
                output = [f"Analysis for {owner}/{repo}:"]
                b = info.basic_info
                if b:
                    output.append(f"Basic: {b.description} | Default branch: {b.default_branch} | Stars: {b.stars_count}")
                if info.tech_stack:
                    output.append(f"Tech Stack: Runtime={info.tech_stack.runtime}, Framework={info.tech_stack.framework}, BuildTool={info.tech_stack.build_tool}")
                if info.languages and info.languages.languages:
                    langs = [f"{l.name} ({l.percentage}%)" for l in info.languages.languages]
                    output.append(f"Languages: {', '.join(langs)}")
                if info.deployment_status:
                    output.append(f"Deploy Status (Pages): enabled={info.deployment_status.enabled}, url={info.deployment_status.url}")
                return "\n".join(output)
            except Exception as exc:
                return f"Analysis error: {str(exc)}"

        return f"Unknown readonly tool: {name}"

    # ------------------------------------------------------------------
    # SIDE-EFFECT tool executor — only called from resume_after_approval
    # ------------------------------------------------------------------
    async def _execute_sideeffect_tool(
        self,
        name: str,
        args: dict[str, Any],
        *,
        env_var_values: dict[str, str] | None,
    ) -> str:
        if name == "deploy_github_pages":
            owner = args.get("owner", "")
            repo = args.get("repo", "")
            profile = args.get("profile", "auto")
            deploy_response = await GitHubPagesService.deploy(
                github_token=self._github_token(),
                owner=owner,
                repository=repo,
                deployment_profile=profile,
                preferred_branch=self.user.deploy_branch,
            )
            # Persist a deployment row so the Deployments page sees it.
            from ..services.github_pages import GitHubPagesService
            pd = GitHubPagesService.PROFILE_DEFINITIONS.get(deploy_response.resolved_profile)
            workflow_filename = pd.workflow_filename if pd else deploy_response.workflow_template
            await DeploymentService.create_from_pages_deploy(
                self.db,
                self.user.id,
                owner=owner,
                repo=repo,
                branch=deploy_response.branch,
                profile=deploy_response.resolved_profile,
                workflow_filename=workflow_filename,
            )
            return (
                f"Pages deploy dispatched: profile={deploy_response.resolved_profile}, "
                f"branch={deploy_response.branch}. Workflow file: {workflow_filename}. "
                f"Site will appear at https://{owner}.github.io/{repo} once the build completes."
            )

        if name == "deploy_render":
            owner = args.get("owner", "")
            repo = args.get("repo", "")
            branch = args.get("branch", "")
            service_name = args.get("service_name", "")
            runtime = args.get("runtime", "python")
            build_command = args.get("build_command")
            start_command = args.get("start_command")
            dockerfile_path = args.get("dockerfile_path")
            env_var_keys = args.get("env_var_keys", []) or []

            # SECRETS RULE: pull values from the user-supplied dict,
            # never from the LLM. Missing values → empty string (Render
            # will reject with a clear error, which the LLM will explain).
            env_vars = []
            for key in env_var_keys:
                value = (env_var_values or {}).get(key, "")
                env_vars.append(RenderEnvVar(key=key, value=value))

            request = RenderDeployRequest(
                owner=owner,
                repository=repo,
                branch=branch,
                service_name=service_name,
                runtime=runtime,
                build_command=build_command,
                start_command=start_command,
                dockerfile_path=dockerfile_path,
                plan="free",
                auto_deploy=True,
                env_vars=env_vars,
            )
            api_key = self._render_api_key()
            owner_id = self.user.render_owner_id
            deploy_response = await RenderService.create_web_service(
                api_key=api_key,
                owner_id=owner_id,
                request=request,
            )
            await DeploymentService.create_from_render_deploy(
                self.db,
                self.user.id,
                owner=owner,
                repo=repo,
                branch=branch,
                runtime=runtime,
                service_id=deploy_response.service_id,
                deploy_id=deploy_response.deploy_id,
                service_url=deploy_response.service_url,
            )
            return (
                f"Render service created: id={deploy_response.service_id}, "
                f"deploy_id={deploy_response.deploy_id}, "
                f"url={deploy_response.service_url or '(pending)'}. "
                f"The build takes 1–3 min; ask me 'what's the status?' to poll."
            )

        if name == "create_pull_request":
            return await GitHubService.create_file_and_pull_request(
                token=self._github_token(),
                owner=args.get("owner", ""),
                repo=args.get("repo", ""),
                file_path=args.get("file_path", ""),
                content=args.get("content", ""),
                commit_message=args.get("commit_message", "DeployBridge AI suggestion"),
                pr_title=args.get("pr_title", "DeployBridge AI suggestion"),
                pr_body=args.get("pr_body", ""),
            )

        if name == "add_render_custom_domain":
            api_key = self._render_api_key()
            response = await RenderService.add_custom_domain(
                api_key=api_key,
                service_id=args.get("service_id", ""),
                domain=args.get("domain", ""),
            )
            return (
                f"Custom domain added. Add a CNAME record: "
                f"Name={response.name.split('.')[0] if response.name else '@'}, "
                f"Value={response.cname_target or '(see Render dashboard)'}. "
                f"Verification status: {response.verification_status}."
            )

        return f"Unknown side-effect tool: {name}"

    # ------------------------------------------------------------------
    # Plan summarizer (for the Approve card)
    # ------------------------------------------------------------------
    def _summarize_plan_step(self, tool: str, args: dict[str, Any]) -> str:
        if tool == "deploy_render":
            env_count = len(args.get("env_var_keys", []))
            return (
                f"Create Render service '{args.get('service_name', '?')}' "
                f"({args.get('runtime', '?')}, free plan, auto-deploy on)"
                + (f" with {env_count} env var(s)" if env_count else "")
            )
        if tool == "deploy_github_pages":
            return (
                f"Deploy {args.get('owner', '?')}/{args.get('repo', '?')} to GitHub Pages "
                f"(profile={args.get('profile', 'auto')})"
            )
        if tool == "create_pull_request":
            return (
                f"Open a PR in {args.get('owner', '?')}/{args.get('repo', '?')} "
                f"to {args.get('file_path', '?')}"
            )
        if tool == "add_render_custom_domain":
            return f"Attach custom domain {args.get('domain', '?')} to Render service"
        return f"Run {tool}"


# ---------------------------------------------------------------------------
# Helpers — convert ORM rows to Pydantic responses
# ------------------------------------------------------------------------------

def _message_to_response(
    msg: AgentMessage,
    *,
    plan: list[dict[str, Any]] | None = None,
):
    from ..schemas.agent import AgentMessageResponse
    return AgentMessageResponse(
        id=str(msg.id),
        role=msg.role,
        content=msg.content,
        tool_name=msg.tool_name,
        plan=plan,
        prompt_tokens=msg.prompt_tokens,
        completion_tokens=msg.completion_tokens,
        created_at=msg.created_at,
    )
