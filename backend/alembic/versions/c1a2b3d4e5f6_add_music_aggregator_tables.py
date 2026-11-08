"""add_music_aggregator_tables

Revision ID: c1a2b3d4e5f6
Revises: f497053be66f
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f497053be66f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Playlists
    op.create_table(
        'playlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_playlists_id'), 'playlists', ['id'], unique=False)
    op.create_index(op.f('ix_playlists_user_id'), 'playlists', ['user_id'], unique=False)

    # 2. Playlist tracks
    op.create_table(
        'playlist_tracks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('playlist_id', sa.Integer(), nullable=False),
        sa.Column('service', sa.String(length=30), nullable=False),
        sa.Column('service_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('artist', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('album', sa.String(length=255), nullable=True),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('playback_kind', sa.String(length=50), nullable=True),
        sa.Column('playback_ref', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_playlist_tracks_id'), 'playlist_tracks', ['id'], unique=False)
    op.create_index(op.f('ix_playlist_tracks_playlist_id'), 'playlist_tracks', ['playlist_id'], unique=False)

    # 3. Favorite tracks
    op.create_table(
        'favorite_tracks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service', sa.String(length=30), nullable=False),
        sa.Column('service_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('artist', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('album', sa.String(length=255), nullable=True),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sources', sa.String(length=255), nullable=False, server_default='[]'),
        sa.Column('playback_kind', sa.String(length=50), nullable=True),
        sa.Column('playback_ref', sa.String(length=500), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'service', 'service_id', name='uq_user_service_track'),
    )
    op.create_index(op.f('ix_favorite_tracks_id'), 'favorite_tracks', ['id'], unique=False)
    op.create_index(op.f('ix_favorite_tracks_user_id'), 'favorite_tracks', ['user_id'], unique=False)

    # 4. Favorite albums
    op.create_table(
        'favorite_albums',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service', sa.String(length=30), nullable=False),
        sa.Column('service_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('subtitle', sa.String(length=255), nullable=True),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'service', 'service_id', name='uq_user_service_album'),
    )
    op.create_index(op.f('ix_favorite_albums_id'), 'favorite_albums', ['id'], unique=False)
    op.create_index(op.f('ix_favorite_albums_user_id'), 'favorite_albums', ['user_id'], unique=False)

    # 5. Listening history
    op.create_table(
        'listening_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service', sa.String(length=30), nullable=False),
        sa.Column('service_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('artist', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('album', sa.String(length=255), nullable=True),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('listened_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_listening_history_id'), 'listening_history', ['id'], unique=False)
    op.create_index(op.f('ix_listening_history_user_id'), 'listening_history', ['user_id'], unique=False)

    # 6. User uploads
    op.create_table(
        'user_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('artist', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('file_type', sa.String(length=20), nullable=False, server_default='WAV'),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('edit_summary', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_uploads_id'), 'user_uploads', ['id'], unique=False)
    op.create_index(op.f('ix_user_uploads_user_id'), 'user_uploads', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_uploads_parent_id'), 'user_uploads', ['parent_id'], unique=False)

    # 7. User service preferences
    op.create_table(
        'user_service_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service', sa.String(length=30), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('api_token', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'service', name='uq_user_service_pref'),
    )
    op.create_index(op.f('ix_user_service_preferences_id'), 'user_service_preferences', ['id'], unique=False)
    op.create_index(op.f('ix_user_service_preferences_user_id'), 'user_service_preferences', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('user_service_preferences')
    op.drop_table('user_uploads')
    op.drop_table('listening_history')
    op.drop_table('favorite_albums')
    op.drop_table('favorite_tracks')
    op.drop_table('playlist_tracks')
    op.drop_table('playlists')
