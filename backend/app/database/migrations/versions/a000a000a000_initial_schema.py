"""Initial schema for Heimdall Consumer Edition

Revision ID: a000a000a000
Revises: None
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a000a000a000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create Publishers Table ──
    op.create_table(
        'publishers',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column('rss_url', sa.String(length=255), nullable=False),
        sa.Column('credibility_score', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('successful_fetches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_fetches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # ── 2. Create Stories Table ──
    op.create_table(
        'stories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('ai_summary_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('predicted_category', sa.String(length=100), nullable=False),
        sa.Column('region_tags', sa.JSON(), nullable=True),
        sa.Column('first_reported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('publisher_diversity', sa.Integer(), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False),
        sa.Column('importance_score', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('trending_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('has_conflicts', sa.Boolean(), nullable=False),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stories_updated_at', 'stories', ['updated_at'], unique=False)

    # ── 3. Create Users Table ──
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('theme', sa.String(length=20), nullable=False, server_default='dark'),
        sa.Column('preferred_categories', sa.JSON(), nullable=True),
        sa.Column('preferred_publishers', sa.JSON(), nullable=True),
        sa.Column('hidden_categories', sa.JSON(), nullable=True),
        sa.Column('hidden_publishers', sa.JSON(), nullable=True),
        sa.Column('onboarding_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('brief_time', sa.String(length=20), nullable=False, server_default='morning'),
        sa.Column('reset_token_hash', sa.String(length=128), nullable=True),
        sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── 4. Create Articles Table ──
    op.create_table(
        'articles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('story_id', sa.Uuid(), nullable=True),
        sa.Column('publisher_id', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('canonical_url', sa.String(length=512), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('predicted_category', sa.String(length=100), nullable=True),
        sa.Column('image_url', sa.String(length=512), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('article_hash', sa.String(length=64), nullable=False),
        sa.Column('reading_time', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('fetch_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['publisher_id'], ['publishers.id'], ),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_hash')
    )
    op.create_index('ix_articles_content_hash', 'articles', ['content_hash'], unique=False)
    op.create_index('ix_articles_published_at', 'articles', ['published_at'], unique=False)
    op.create_index('ix_articles_story_id', 'articles', ['story_id'], unique=False)

    # ── 5. Create Bookmarks Table ──
    op.create_table(
        'bookmarks',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('story_id', sa.Uuid(), nullable=False),
        sa.Column('bookmarked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'story_id')
    )

    # ── 6. Create Reading History Table ──
    op.create_table(
        'reading_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('story_id', sa.Uuid(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('read_pct', sa.Integer(), nullable=False),
        sa.Column('dwell_seconds', sa.Integer(), nullable=False),
        sa.Column('interaction_type', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reading_history_user_id', 'reading_history', ['user_id'], unique=False)
    op.create_index('ix_reading_history_read_at', 'reading_history', ['read_at'], unique=False)

    # ── 7. Create Story Timelines Table ──
    op.create_table(
        'story_timelines',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('story_id', sa.Uuid(), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('headline', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_story_timelines_event_timestamp', 'story_timelines', ['event_timestamp'], unique=False)
    op.create_index('ix_story_timelines_story_id', 'story_timelines', ['story_id'], unique=False)

    # ── 8. Create Story Relations Table (Forward Compatibility) ──
    op.create_table(
        'story_relations',
        sa.Column('story_id', sa.Uuid(), nullable=False),
        sa.Column('related_story_id', sa.Uuid(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.ForeignKeyConstraint(['related_story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['story_id'], ['stories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('story_id', 'related_story_id')
    )

    # ── 9. Setup PostgreSQL Full-Text Search Indices and Triggers ──
    if op.get_bind().dialect.name == "postgresql":
        op.create_index('idx_stories_search', 'stories', ['search_vector'], unique=False, postgresql_using='gin')
        op.execute(
            "CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE ON stories "
            "FOR EACH ROW EXECUTE FUNCTION tsvector_update_trigger(search_vector, 'pg_catalog.english', title, summary)"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS tsvectorupdate ON stories")
        op.drop_index('idx_stories_search', table_name='stories')

    op.drop_table('story_relations')
    op.drop_index('ix_story_timelines_story_id', table_name='story_timelines')
    op.drop_index('ix_story_timelines_event_timestamp', table_name='story_timelines')
    op.drop_table('story_timelines')
    
    op.drop_index('ix_reading_history_read_at', table_name='reading_history')
    op.drop_index('ix_reading_history_user_id', table_name='reading_history')
    op.drop_table('reading_history')
    
    op.drop_table('bookmarks')
    
    op.drop_index('ix_articles_story_id', table_name='articles')
    op.drop_index('ix_articles_published_at', table_name='articles')
    op.drop_index('ix_articles_content_hash', table_name='articles')
    op.drop_table('articles')
    
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    op.drop_index('ix_stories_updated_at', table_name='stories')
    op.drop_table('stories')
    
    op.drop_table('publishers')
