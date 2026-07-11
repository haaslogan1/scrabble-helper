"""user session version

Revision ID: 009_user_session_version
Revises: 008_user_avatars
Create Date: 2026-07-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_user_session_version"
down_revision: Union[str, None] = "008_user_avatars"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("users")}

    if "session_version" not in columns:
        op.add_column(
            "users",
            sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"),
        )
    if "last_session_user_agent" not in columns:
        op.add_column(
            "users",
            sa.Column("last_session_user_agent", sa.String(length=512), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("users", "last_session_user_agent")
    op.drop_column("users", "session_version")
