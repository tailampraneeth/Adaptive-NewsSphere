"""add_milestone5_chat_enhancements

Revision ID: 6b10a5e8f8dc
Revises: 5a09b4d8d1cf
Create Date: 2026-07-09

Adds title and message_count columns to chat_sessions,
and prompt_version and metadata JSON columns to chat_messages.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6b10a5e8f8dc"
down_revision = "5a09b4d8d1cf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── chat_sessions table refinements ───────────────────────────────────────
    op.add_column(
        "chat_sessions",
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True
        )
    )
    op.add_column(
        "chat_sessions",
        sa.Column(
            "message_count",
            sa.Integer(),
            nullable=False,
            server_default="0"
        )
    )

    # ── chat_messages table refinements ───────────────────────────────────────
    op.add_column(
        "chat_messages",
        sa.Column(
            "prompt_version",
            sa.String(length=20),
            nullable=False,
            server_default="v1"
        )
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "chat_metadata",
            sa.JSON(),
            nullable=True
        )
    )


def downgrade() -> None:
    # Remove chat_messages columns
    op.drop_column("chat_messages", "chat_metadata")
    op.drop_column("chat_messages", "prompt_version")

    # Remove chat_sessions columns
    op.drop_column("chat_sessions", "message_count")
    op.drop_column("chat_sessions", "title")
