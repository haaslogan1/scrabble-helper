"""user avatars

Revision ID: 008_user_avatars
Revises: 007_game_photos
Create Date: 2026-07-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_user_avatars"
down_revision: Union[str, None] = "007_game_photos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("users")}

    if "google_avatar_url" not in columns:
        op.add_column("users", sa.Column("google_avatar_url", sa.String(length=512), nullable=True))
    if "avatar_storage_key" not in columns:
        op.add_column("users", sa.Column("avatar_storage_key", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_storage_key")
    op.drop_column("users", "google_avatar_url")
