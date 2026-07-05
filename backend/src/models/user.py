import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    github_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    username: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    github_token: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    github_token_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )    

    github_scope: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def  __repr__(self) -> str:
        return f"<User {self.username} (github_id: {self.github_id})>"