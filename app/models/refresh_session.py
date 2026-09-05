"""RefreshSession ORM model — a server-side record of one issued refresh token.

Only `token_hash` (SHA-256 of the raw token) is ever stored — the raw token
itself lives only in the HttpOnly cookie handed to the browser and is never
persisted. Rotation: refreshing marks the current row `revoked_at` and links
it to the new row via `replaced_by_id`, so a rotated-away token being
presented again (replay) is detectable — see RefreshSessionService.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshSession(Base):
    """One issued refresh token, identified only by its hash."""

    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("refresh_sessions.id", ondelete="SET NULL"), nullable=True
    )
