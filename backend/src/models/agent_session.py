# ------------------------------------------------------------------------------
# WHAT THIS IS
#   Persistent storage for the Deploy Agent's chat history + tool traces.
#
# WHY PERSIST
#   - Refresh-safe chat (closing the browser doesn't lose context)
#   - Audit trail (every action the agent took is replayable)
#   - Quota story: "N agent actions/day" — reuse the reports quota logic
#
# v1 SHORTCUT
#   If time is short, the agent can run single-shot request/response with
#   no session memory (each user message starts a fresh LLM conversation).
#   The flows still work; the persistence is for UX polish + audit only.
# ------------------------------------------------------------------------------
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db.session import Base


class AgentSession(Base):
    """One chat conversation. A user can have many.

    Think of this as the equivalent of a chat thread in ChatGPT — the
    session_id is what makes the conversation refresh-safe: the user
    closes the browser, comes back tomorrow, picks up where they left off.
    """

    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # A short human-friendly title for the sidebar list, derived from the
    # first user message ("deploy notes-api" → "Deploy: notes-api").
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New chat")

    # Quick filter for the sidebar — the latest state of the session.
    # `idle` (waiting for user input) | `running` (LLM thinking) |
    # `awaiting_approval` (confirm-gate card visible) | `error`
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, default="idle", index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AgentSession {self.id} ({self.state})>"


class AgentMessage(Base):
    """One message in an agent session. Mirrors the OpenAI message format
    so we can pass them straight to the LLM client without translation.

    Roles:
      - "user":      user's input
      - "assistant": LLM's text output (may be empty if a tool call was made)
      - "tool":       result of a tool call (the JSON-serialized string)
      - "system":    only the FIRST message in a session carries role=system

    For tool calls made by the assistant, we ALSO store an extra row with
    role="assistant_tool_call" carrying the raw tool_calls payload — the
    LLM API requires the assistant message with tool_calls to be replayed
    back verbatim in the next request, and we need it for the audit trail.
    """

    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # See roles above. The non-standard roles ("assistant_tool_call",
    # "assistant_plan", "user_approval") are DeployBridge-specific and
    # are skipped when feeding messages back to the LLM.

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For role=tool: the tool result string.
    # For role=assistant_tool_call: the JSON-serialized tool_calls list.
    # For role=assistant_plan: the JSON-serialized plan (confirm-gate).
    # For role=user_approval: "approved" | "cancelled".

    # When role=assistant_tool_call or role=tool — the function name that
    # was invoked. Makes the trace readable in the UI.
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Token accounting, per-message. Sum across the session = total cost.
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AgentMessage {self.role} ({self.tool_name or 'text'})>"
