"""Persistent Deployment record.

The frontend's deployments.js currently lives entirely in localStorage --
that means deployments don't survive a browser switch, can't be polled
server-side, and there's no audit trail. This model fixes that: every
deploy (Pages or Render) gets a row, with status updated by polling.

Phase 1 keeps it simple -- the model captures the immutable parts
(platform, repo, branch, profile, service_id, url) plus the latest
status/error. Live status polling is a follow-up task; for now the
frontend can PATCH /deployments/{id} when it learns of a status
change via the platform's own API.
"""
import uuid 
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db.session import Base


class Deployment(Base):
    """
    Cross-platform deployment record.

    One row per deploy attempt (Pages workflow dispatch OR Render
    service create). `platform` discriminates the upstream API used
    to fetch live status; `service_id` carries the platform-specific
    identifier (Pages workflow run id, or Render `srv-...` id).
    """
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    platform: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)

    profile: Mapped[str | None] = mapped_column(String(40), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    service_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

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
        return f"<Deployment {self.platform}:{self.service_id} ({self.status})>"
