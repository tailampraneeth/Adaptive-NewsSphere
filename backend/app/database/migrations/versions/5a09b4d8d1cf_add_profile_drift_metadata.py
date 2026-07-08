"""add_profile_drift_metadata

Revision ID: 5a09b4d8d1cf
Revises: e3f1a8b2c7d9
Create Date: 2026-07-09

Adds profile drift, updates, decay tracking metadata to user_profiles,
and adds ranking_version tracking to user_recommendation_logs.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5a09b4d8d1cf"
down_revision = "e3f1a8b2c7d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── user_profiles table refinements ───────────────────────────────────────
    op.add_column(
        "user_profiles",
        sa.Column(
            "profile_age_days",
            sa.Integer(),
            nullable=False,
            server_default="0"
        )
    )
    op.add_column(
        "user_profiles",
        sa.Column("last_profile_decay", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user_profiles",
        sa.Column("last_profile_rebuild", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user_profiles",
        sa.Column("last_profile_update", sa.DateTime(timezone=True), nullable=True)
    )

    # ── user_recommendation_logs table refinements ────────────────────────────
    op.add_column(
        "user_recommendation_logs",
        sa.Column(
            "ranking_version",
            sa.String(length=20),
            nullable=False,
            server_default="v1"
        )
    )


def downgrade() -> None:
    # Remove user_recommendation_logs column
    op.drop_column("user_recommendation_logs", "ranking_version")

    # Remove user_profiles columns
    op.drop_column("user_profiles", "last_profile_update")
    op.drop_column("user_profiles", "last_profile_rebuild")
    op.drop_column("user_profiles", "last_profile_decay")
    op.drop_column("user_profiles", "profile_age_days")
