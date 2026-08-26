"""Add a full-text search (GIN) index on document_chunks.content, for hybrid search.

Hybrid search combines this keyword/BM25-style match with the existing pgvector
cosine-similarity search (see 0001/0002), fused via Reciprocal Rank Fusion in
ChunkRepository.hybrid_search(). No new column is needed: this is a functional
(expression) index over `to_tsvector('english', content)`, computed at query
time by `ChunkRepository.keyword_search()` using the identical expression, so
Postgres can use the index for `@@` full-text queries without any backfill.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_content_fts "
        "ON document_chunks USING GIN (to_tsvector('english', content))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_fts")
