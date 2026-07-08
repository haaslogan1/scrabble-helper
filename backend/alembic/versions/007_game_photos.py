"""game photos

Revision ID: 007_game_photos
Revises: 006_game_last_activity
Create Date: 2026-07-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_game_photos"
down_revision: Union[str, None] = "006_game_last_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

photo_context = sa.Enum("board", "group", "other", name="photocontext")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        photo_context.create(bind, checkfirst=True)

    op.create_table(
        "game_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column(
            "context",
            photo_context,
            nullable=False,
            server_default="board",
        ),
        sa.Column("round_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_photos_game_id", "game_photos", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_game_photos_game_id", table_name="game_photos")
    op.drop_table("game_photos")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        photo_context.drop(bind, checkfirst=True)
