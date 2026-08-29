"""Add observability_events table.

Persists structured rag_request/agent_request/tool_call events (already
emitted as JSON log lines by app/core/logging.py) so the observability
dashboard has queryable history instead of only an ephemeral stdout line.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "observability_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_observability_events_event_type", "observability_events", ["event_type"])
    op.create_index("ix_observability_events_user_id", "observability_events", ["user_id"])
    op.create_index("ix_observability_events_created_at", "observability_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_observability_events_created_at", table_name="observability_events")
    op.drop_index("ix_observability_events_user_id", table_name="observability_events")
    op.drop_index("ix_observability_events_event_type", table_name="observability_events")
    op.drop_table("observability_events")
