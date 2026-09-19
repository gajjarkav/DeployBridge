# ------------------------------------------------------------------------------
# WHAT THIS IS
#   6 endpoints for the Deploy Agent chat:
#
#   POST   /v1/agent/sessions                          create a session
#   GET    /v1/agent/sessions                          list user's sessions
#   GET    /v1/agent/sessions/{id}                     one session + messages
#   DELETE /v1/agent/sessions/{id}                    delete
#   POST   /v1/agent/sessions/{id}/messages           send user msg → run loop
#   POST   /v1/agent/messages/{message_id}/approve    approve a gated plan
#
# AUTH
#   Every endpoint requires a valid session JWT (via get_current_user).
#   The LLM API key is read from server-side env vars — the user never
#   supplies it. Env-var VALUES for deploys are sent by the UI form and
#   NEVER enter the LLM conversation (see deploy_agent.py SECRETS RULE).
# ------------------------------------------------------------------------------
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.crypto import TokenDecryptionError
from ...core.exception import GitHubAPIError, RenderError
from ...db.session import get_db
from ...models.agent_session import AgentMessage, AgentSession
from ...models.user import User
from ...schemas.agent import (
    AgentApproveRequest,
    AgentApproveResponse,
    AgentSendMessageRequest,
    AgentSendMessageResponse,
    AgentSessionCreateRequest,
    AgentSessionDetailResponse,
    AgentSessionListResponse,
    AgentSessionResponse,
)
from ...services.deploy_agent import DeployAgentRunner
from ...services.llm_client import LLMClientError
from ..dependencies import get_current_user


router = APIRouter()


# ---------------------------------------------------------------------------
# Sessions: create / list / detail / delete
# ---------------------------------------------------------------------------

@router.post(
    "/sessions",
    response_model=AgentSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new agent chat session",
)
async def create_session(
    payload: AgentSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates an empty session. If `prefill_question` is set, the session
    boots pre-loaded with a user message so the user can hit Send instantly
    (used by the [🤖 Ask Agent] button on failed deployment cards).
    """
    session = AgentSession(
        user_id=current_user.id,
        title=payload.title or "New chat",
    )
    db.add(session)
    await db.flush()

    # If a prefill question was passed, immediately run the agent loop.
    # We DON'T await here — return the session and let the frontend POST
    # /messages explicitly. This keeps the create endpoint fast and
    # side-effect free.
    if payload.prefill_question:
        msg = AgentMessage(
            session_id=session.id,
            user_id=current_user.id,
            role="user",
            content=payload.prefill_question,
        )
        db.add(msg)
        await db.flush()
        session.title = payload.prefill_question[:80]

    return _session_to_response(session)


@router.get(
    "/sessions",
    response_model=AgentSessionListResponse,
    summary="List user's agent chat sessions (paginated)",
)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_stmt = select(func.count(AgentSession.id)).where(
        AgentSession.user_id == current_user.id
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(AgentSession)
        .where(AgentSession.user_id == current_user.id)
        .order_by(desc(AgentSession.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return AgentSessionListResponse(
        items=[_session_to_response(s) for s in rows],
        total=total or 0,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=AgentSessionDetailResponse,
    summary="Get a session with its full message history",
)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _resolve_session_or_404(db, current_user, session_id)
    msg_stmt = (
        select(AgentMessage)
        .where(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.created_at)
    )
    msgs = (await db.execute(msg_stmt)).scalars().all()

    detail = AgentSessionDetailResponse(
        **_session_to_response(session).model_dump(),
        messages=[
            AgentMessageResponseFor(msg) for msg in msgs
        ],
    )
    return detail


@router.delete(
    "/sessions/{session_id}",
    summary="Delete an agent chat session",
)
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _resolve_session_or_404(db, current_user, session_id)
    await db.delete(session)
    await db.flush()
    return {"success": True, "message": "Session deleted."}


# ---------------------------------------------------------------------------
# Messages: send + approve
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/messages",
    response_model=AgentSendMessageResponse,
    summary="Send a user message and run the agent loop",
)
async def send_message(
    session_id: uuid.UUID,
    payload: AgentSendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Appends the user's message, runs the LLM loop, returns final state.

    The loop may either:
      - Return a final text message (session_state=idle)
      - Pause on a side-effect plan (session_state=awaiting_approval) —
        the UI shows an Approve/Cancel card; approving calls
        POST /v1/agent/messages/{id}/approve.
    """
    session = await _resolve_session_or_404(db, current_user, session_id)

    try:
        runner = DeployAgentRunner(db, current_user, session)
    except LLMClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{exc.message}. {exc.detail}" if exc.detail else exc.message,
        ) from exc

    try:
        result = await runner.run_user_message(payload.content)
    except (TokenDecryptionError, LLMClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (RenderError, GitHubAPIError) as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc

    return result


@router.post(
    "/messages/{message_id}/approve",
    response_model=AgentApproveResponse,
    summary="Approve or cancel a gated agent plan",
)
async def approve_message(
    message_id: uuid.UUID,
    payload: AgentApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Executes (or cancels) a plan persisted as role=assistant_plan.

    When `approved=True`, the planned side-effect tools are executed IN
    ORDER, their results are appended to the conversation as role=tool
    messages, and the loop resumes.

    Env-var VALUES (for deploy_render plans) are passed in
    `payload.env_var_values`. They NEVER enter the LLM conversation —
    the runner merges them with the keys the LLM saw at execution time.
    """
    plan_msg = await db.get(AgentMessage, message_id)
    if plan_msg is None or plan_msg.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plan message not found.")
    if plan_msg.role != "assistant_plan":
        raise HTTPException(
            status_code=400,
            detail=f"Message {message_id} is not a plan (role={plan_msg.role}).",
        )

    session = await db.get(AgentSession, plan_msg.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        runner = DeployAgentRunner(db, current_user, session)
        result = await runner.resume_after_approval(
            plan_message_id=message_id,
            approved=payload.approved,
            env_var_values=payload.env_var_values,
        )
    except (TokenDecryptionError, LLMClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (RenderError, GitHubAPIError) as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc

    return AgentApproveResponse(**result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _resolve_session_or_404(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> AgentSession:
    session = await db.get(AgentSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    return session


def _session_to_response(s: AgentSession) -> AgentSessionResponse:
    return AgentSessionResponse(
        id=str(s.id),
        title=s.title,
        state=s.state,  # type: ignore[arg-type]
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


# Forward declaration of AgentMessageResponse builder — kept inline to keep
# the file self-contained.
from ...schemas.agent import AgentMessageResponse as AgentMessageResponseFor  # noqa: E402


def AgentMessageResponseFor(msg: AgentMessage):
    """Convert an AgentMessage row to an AgentMessageResponse. Plans
    (role=assistant_plan) have their `content` JSON parsed and surfaced
    as the `plan` field so the UI can render the Approve card."""
    plan = None
    if msg.role == "assistant_plan" and msg.content:
        try:
            import json as _json
            plan = _json.loads(msg.content)
        except (ValueError, TypeError):
            plan = None
    return AgentMessageResponseFor(
        id=str(msg.id),
        role=msg.role,
        content=msg.content,
        tool_name=msg.tool_name,
        plan=plan,
        prompt_tokens=msg.prompt_tokens,
        completion_tokens=msg.completion_tokens,
        created_at=msg.created_at,
    )
