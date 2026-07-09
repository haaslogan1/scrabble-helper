"""game ending_at for stale live sweep

Revision ID: 009_game_ending_at
Revises: 008_user_avatars
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_game_ending_at"
down_revision: Union[str, None] = "008_user_avatars"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("games")}

    if "ending_at" not in columns:
        op.add_column("games", sa.Column("ending_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "ending_at")
