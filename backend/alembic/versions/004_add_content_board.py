"""Add the content board and the voice corpus it feeds

Revision ID: 004
Revises: 003
Create Date: 2026-09-12

Four tables: posts, threaded comments, typed reactions, and the harvested
`voice_samples` that the content generator reads as style anchors.

Reaction kinds are stored as plain VARCHAR rather than a native Postgres ENUM.
Adding a sixth reaction later is then a code change instead of a migration, and
SQLite (used for local mock mode and the test suite) gets the same DDL.
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'board_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.Integer(), nullable=False),
        # NULL author means the AI wrote it.
        sa.Column('author_user_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=32), nullable=False, server_default='post'),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('media_paths', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('week', sa.Integer(), nullable=True),
        sa.Column('generated_by', sa.String(length=120), nullable=True),
        sa.Column('allow_training', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_board_posts_league_id', 'board_posts', ['league_id'])
    op.create_index('ix_board_posts_author_user_id', 'board_posts', ['author_user_id'])
    op.create_index('ix_board_posts_created_at', 'board_posts', ['created_at'])
    op.create_index('ix_board_posts_league_created', 'board_posts', ['league_id', 'created_at'])

    op.create_table(
        'board_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('author_user_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['post_id'], ['board_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['board_comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_board_comments_post_id', 'board_comments', ['post_id'])
    op.create_index('ix_board_comments_created_at', 'board_comments', ['created_at'])

    op.create_table(
        'board_reactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('comment_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reaction', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['post_id'], ['board_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['comment_id'], ['board_comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # A reaction belongs to exactly one thing.
        sa.CheckConstraint(
            '(post_id IS NOT NULL AND comment_id IS NULL) OR '
            '(post_id IS NULL AND comment_id IS NOT NULL)',
            name='ck_board_reactions_one_target',
        ),
        # Tapping the same reaction twice is a toggle, not a second vote.
        sa.UniqueConstraint('user_id', 'post_id', 'reaction', name='uq_board_reaction_post'),
        sa.UniqueConstraint('user_id', 'comment_id', 'reaction', name='uq_board_reaction_comment'),
    )
    op.create_index('ix_board_reactions_post_id', 'board_reactions', ['post_id'])
    op.create_index('ix_board_reactions_comment_id', 'board_reactions', ['comment_id'])

    op.create_table(
        'voice_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.Integer(), nullable=False),
        sa.Column('source_post_id', sa.Integer(), nullable=True),
        sa.Column('author_user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_post_id'], ['board_posts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['author_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_voice_samples_league_id', 'voice_samples', ['league_id'])
    op.create_index('ix_voice_samples_league_score', 'voice_samples', ['league_id', 'score'])


def downgrade() -> None:
    op.drop_table('voice_samples')
    op.drop_table('board_reactions')
    op.drop_table('board_comments')
    op.drop_table('board_posts')
