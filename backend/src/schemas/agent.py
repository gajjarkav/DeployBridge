# ------------------------------------------------------------------------------
# WHAT THIS IS
#   Pydantic request/response schemas for the /v1/agent endpoints.
#
# ENDPOINTS (see api/v1/agent.py)
#   POST   /v1/agent/sessions              create a new chat session
#   GET    /v1/agent/sessions              list user's sessions
#   GET    /v1/agent/sessions/{id}        one session with messages
#   DELETE /v1/agent/sessions/{id}         delete a session
#   POST   /v1/agent/sessions/{id}/messages  send a user message + run the loop
#   POST   /v1/agent/messages/{id}/approve  approve a gated plan
#
# THE CONFIRM-GATE
#   When the LLM wants to call a SIDE-EFFECT tool (deploy_render, deploy_pages,
#   create_pull_request, add_render_custom_domain), the loop PAUSES and
#   returns a structured PLAN. The UI renders an [Approve] [Cancel] card.
#   Approve → POST /messages/{plan_message_id}/approve → loop resumes.
# ------------------------------------------------------------------------------
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentSessionCreateRequest(BaseModel):
    """Optional — if `prefill_deployment_id` is set, the session boots
    pre-loaded with the deployment's context so the user can ask
    "why did this fail?" without re-typing the repo name."""
    title: str | None = Field(default=None, description="Optional title for the sidebar")
    prefill_question: str | None = Field(
        default=None,
        description="Pre-fill the first user message (e.g. 'Why did my deploy fail?').",
    )
    prefill_deployment_id: str | None = Field(
        default=None,
        description="When [🤖 Ask Agent] is clicked on a failed card, the "
                    "frontend passes the deployment id so the agent can "
                    "self-contextualize: it reads the row + the logs and "
                    "starts the conversation with a diagnosis.",
    )


class AgentSessionResponse(BaseModel):
    id: str
    title: str
    state: Literal["idle", "running", "awaiting_approval", "error"]
    created_at: datetime
    updated_at: datetime


class AgentSessionListResponse(BaseModel):
    items: list[AgentSessionResponse]
    total: int


class AgentMessageResponse(BaseModel):
    """One message in an agent session, in render-order."""
    id: str
    role: str
    content: str | None = None
    tool_name: str | None = None
    # `plan` is populated only when role="assistant_plan" — it's the
    # structured plan the UI renders an [Approve] [Cancel] card for.
    plan: list[dict[str, Any]] | None = None
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime


class AgentSessionDetailResponse(AgentSessionResponse):
    """A session with its full message history — for the chat UI."""
    messages: list[AgentMessageResponse]


class AgentSendMessageRequest(BaseModel):
    """Body of POST /v1/agent/sessions/{id}/messages."""
    content: str = Field(..., min_length=1, description="The user's message")
    # When approving a plan, the frontend sends the env-var VALUES here.
    # They NEVER enter the LLM conversation — see SECRETS RULE below.
    env_var_values: dict[str, str] | None = Field(
        default=None,
        description="When approving a deploy_render plan, the UI collects "
                    "env var VALUES via a form and sends them here. The LLM "
                    "only ever saw the KEYS (from .env.example). Values are "
                    "merged by Python at execution time and never logged.",
    )


class AgentSendMessageResponse(BaseModel):
    """Returned after the loop runs to completion (or pauses on a plan)."""
    session_state: Literal["idle", "running", "awaiting_approval", "error"]
    # The assistant's final message in this turn — could be plain text
    # OR a structured plan waiting for approval.
    message: AgentMessageResponse | None = None
    # Full trace of tool calls made this turn — same shape as the
    # report_agent's trace, so the UI can reuse the rendering.
    trace: list[str] = Field(default_factory=list)


class AgentApproveRequest(BaseModel):
    """Body of POST /v1/agent/messages/{id}/approve."""
    approved: bool = Field(..., description="True = execute the plan; False = cancel")
    env_var_values: dict[str, str] | None = Field(
        default=None,
        description="Env-var values collected by the UI form when the plan "
                    "is a deploy_render. Never logged, never sent to the LLM.",
    )


class AgentApproveResponse(BaseModel):
    session_state: Literal["idle", "running", "awaiting_approval", "error"]
    message: AgentMessageResponse | None = None
    trace: list[str] = Field(default_factory=list)
