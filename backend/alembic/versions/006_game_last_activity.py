"""game last activity for inactivity timeout

Revision ID: 006_game_last_activity
Revises: 005_feedback
Create Date: 2026-07-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_game_last_activity"
down_revision: Union[str, None] = "005_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("games")}

    if "last_activity_at" not in columns:
        op.add_column("games", sa.Column("last_activity_at", sa.DateTime(), nullable=True))
        op.execute(
            sa.text(
                "UPDATE games SET last_activity_at = started_at "
                "WHERE status = 'active' AND started_at IS NOT NULL"
            )
        )


def downgrade() -> None:
    op.drop_column("games", "last_activity_at")
