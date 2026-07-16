"""add_milestone4_recommendation_engine

Revision ID: e3f1a8b2c7d9
Revises: d75f7494c7cb
Create Date: 2026-07-06

Adds schema changes for the Milestone 4 Recommendation Engine:
  - users: preference_vector_id, interaction_count, last_feed_at
  - user_profiles: new table (metadata only — no raw vectors)
  - user_recommendation_logs: recommendation_metadata JSON,
                              is_personalized bool, strategy str;
                              removes recommendation_reason str
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e3f1a8b2c7d9"
down_revision = "d75f7494c7cb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users table ──────────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("preference_vector_id", sa.String(36), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "interaction_count",
            sa.Integer(),
            nullable=False,
            server_default="0"
        )
    )
    op.add_column(
        "users",
        sa.Column("last_feed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_users_preference_vector_id", "users", ["preference_vector_id"])

    # ── user_profiles table (new) ─────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True
        ),
        sa.Column("preference_vector_id", sa.String(36), nullable=True),
        sa.Column(
            "interaction_count",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),
        sa.Column("muted_categories", sa.JSON(), nullable=True),
        sa.Column("muted_publishers", sa.JSON(), nullable=True),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
    )
    op.create_index(
        "ix_user_profiles_preference_vector_id",
        "user_profiles",
        ["preference_vector_id"]
    )

    # ── user_recommendation_logs table ────────────────────────────────────────
    # Remove old free-text column
    op.drop_column("user_recommendation_logs", "recommendation_reason")

    # Add structured metadata fields
    op.add_column(
        "user_recommendation_logs",
        sa.Column(
            "strategy",
            sa.String(50),
            nullable=False,
            server_default="cold_start"
        )
    )
    op.add_column(
        "user_recommendation_logs",
        sa.Column(
            "is_personalized",
            sa.Boolean(),
            nullable=False,
            server_default="false"
        )
    )
    op.add_column(
        "user_recommendation_logs",
        sa.Column(
            "recommendation_metadata",
            sa.JSON(),
            nullable=False,
            server_default="{}"
        )
    )
    op.create_index(
        "ix_user_recommendation_logs_story_id",
        "user_recommendation_logs",
        ["story_id"]
    )


def downgrade() -> None:
    # Restore recommendation_reason
    op.add_column(
        "user_recommendation_logs",
        sa.Column("recommendation_reason", sa.String(255), nullable=True)
    )
    op.drop_column("user_recommendation_logs", "recommendation_metadata")
    op.drop_column("user_recommendation_logs", "is_personalized")
    op.drop_column("user_recommendation_logs", "strategy")
    op.drop_index(
        "ix_user_recommendation_logs_story_id",
        table_name="user_recommendation_logs"
    )

    # Drop user_profiles table
    op.drop_index("ix_user_profiles_preference_vector_id", table_name="user_profiles")
    op.drop_table("user_profiles")

    # Remove users columns
    op.drop_index("ix_users_preference_vector_id", table_name="users")
    op.drop_column("users", "last_feed_at")
    op.drop_column("users", "interaction_count")
    op.drop_column("users", "preference_vector_id")
