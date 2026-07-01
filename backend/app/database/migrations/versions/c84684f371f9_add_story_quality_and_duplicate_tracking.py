"""add_story_quality_and_duplicate_tracking

Adds story quality signals, XAI formation evidence, Milestone 3 reserved fields,
auto-classification columns on articles, and the article_duplicates provenance table.

Revision ID: c84684f371f9
Revises: f862c00452f7
Create Date: 2026-06-28 00:46:11.466373
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c84684f371f9'
down_revision: Union[str, None] = 'f862c00452f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stories table: new quality and scoring columns ────────────────────────
    op.add_column('stories', sa.Column('title', sa.String(length=512), nullable=True))
    op.add_column('stories', sa.Column('importance_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('stories', sa.Column('trending_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('stories', sa.Column('formation_evidence', sa.JSON(), nullable=True))

    # Milestone 3 reserved — all nullable, no logic yet
    op.add_column('stories', sa.Column('verification_score', sa.Float(), nullable=True))
    op.add_column('stories', sa.Column('credibility_score', sa.Float(), nullable=True))
    op.add_column('stories', sa.Column('first_reported_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('stories', sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=True))

    # ── articles table: category classification + duplicate classification ─────
    op.add_column('articles', sa.Column('predicted_category', sa.String(length=100), nullable=True))
    op.add_column('articles', sa.Column('category_confidence', sa.Float(), nullable=True))
    op.add_column('articles', sa.Column('duplicate_type', sa.String(length=50), nullable=True))

    # ── article_duplicates: new provenance table ──────────────────────────────
    op.create_table(
        'article_duplicates',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('original_article_id', sa.Uuid(), nullable=False),
        sa.Column('duplicate_article_id', sa.Uuid(), nullable=False),
        sa.Column('duplicate_type', sa.String(length=50), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['duplicate_article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['original_article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_article_duplicates_original_article_id'),
        'article_duplicates',
        ['original_article_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_article_duplicates_duplicate_article_id'),
        'article_duplicates',
        ['duplicate_article_id'],
        unique=False
    )


def downgrade() -> None:
    # Reverse in dependency order
    op.drop_index(op.f('ix_article_duplicates_duplicate_article_id'), table_name='article_duplicates')
    op.drop_index(op.f('ix_article_duplicates_original_article_id'), table_name='article_duplicates')
    op.drop_table('article_duplicates')

    op.drop_column('articles', 'duplicate_type')
    op.drop_column('articles', 'category_confidence')
    op.drop_column('articles', 'predicted_category')

    op.drop_column('stories', 'last_updated_at')
    op.drop_column('stories', 'first_reported_at')
    op.drop_column('stories', 'credibility_score')
    op.drop_column('stories', 'verification_score')
    op.drop_column('stories', 'formation_evidence')
    op.drop_column('stories', 'trending_score')
    op.drop_column('stories', 'importance_score')
    op.drop_column('stories', 'title')
