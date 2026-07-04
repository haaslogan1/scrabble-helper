"""feedback submissions

Revision ID: 005_feedback
Revises: 004_notifications
Create Date: 2026-07-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_feedback"
down_revision: Union[str, None] = "004_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "feedback_submissions" not in tables:
        op.create_table(
            "feedback_submissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("page_url", sa.String(length=512), nullable=True),
            sa.Column("game_id", sa.Integer(), nullable=True),
            sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_feedback_submissions_user_created",
            "feedback_submissions",
            ["user_id", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_feedback_submissions_user_created", table_name="feedback_submissions")
    op.drop_table("feedback_submissions")
