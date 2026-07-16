"""add_user_password_auth

Revision ID: f120a10df8dc
Revises: 6b10a5e8f8dc
Create Date: 2026-07-11

Adds hashed_password column to users table.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f120a10df8dc"
down_revision = "6b10a5e8f8dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
