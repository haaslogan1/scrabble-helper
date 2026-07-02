"""notifications and friend requests

Revision ID: 004_notifications
Revises: 003_friends_username
Create Date: 2026-07-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_notifications"
down_revision: Union[str, None] = "003_friends_username"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "friend_requests" not in tables:
        op.create_table(
            "friend_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("from_user_id", sa.Integer(), nullable=False),
            sa.Column("to_user_id", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                sa.Enum("pending", "accepted", "declined", name="friendrequeststatus"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("responded_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["from_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["to_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("from_user_id", "to_user_id"),
        )
        op.create_index("ix_friend_requests_from_user_id", "friend_requests", ["from_user_id"])
        op.create_index("ix_friend_requests_to_user_id", "friend_requests", ["to_user_id"])

    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "type",
                sa.Enum(
                    "friend_request",
                    "friend_request_accepted",
                    "friend_request_declined",
                    "friend_mutual",
                    "live_game_started",
                    "game_completed",
                    name="notificationtype",
                ),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.String(length=512), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("dismissed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_friend_requests_to_user_id", table_name="friend_requests")
    op.drop_index("ix_friend_requests_from_user_id", table_name="friend_requests")
    op.drop_table("friend_requests")
