"""friends and username

Revision ID: 003_friends_username
Revises: 002_email_verification
Create Date: 2026-06-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_friends_username"
down_revision: Union[str, None] = "002_email_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(insp: sa.Inspector, table: str) -> set[str]:
    return {col["name"] for col in insp.get_columns(table)}


def _backfill_usernames(connection) -> None:
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("email", sa.String),
        sa.column("username", sa.String),
    )
    rows = connection.execute(
        sa.select(users.c.id, users.c.email).where(users.c.username.is_(None))
    ).fetchall()
    taken = {
        row[0]
        for row in connection.execute(
            sa.select(users.c.username).where(users.c.username.isnot(None))
        ).fetchall()
    }
    for user_id, email in rows:
        base = (email.split("@")[0] or "user").lower()
        base = "".join(ch for ch in base if ch.isalnum() or ch == "_")[:32] or "user"
        candidate = base
        suffix = 1
        while candidate in taken:
            suffix += 1
            candidate = f"{base}{suffix}"[:32]
        taken.add(candidate)
        connection.execute(
            users.update().where(users.c.id == user_id).values(username=candidate)
        )


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "username" not in _column_names(insp, "users"):
        op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
        op.create_index("ix_users_username", "users", ["username"], unique=True)

    if "players" in tables and "linked_user_id" not in _column_names(insp, "players"):
        op.add_column("players", sa.Column("linked_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_players_linked_user_id_users",
            "players",
            "users",
            ["linked_user_id"],
            ["id"],
        )
        op.create_unique_constraint(
            "uq_players_owner_linked_user",
            "players",
            ["owner_user_id", "linked_user_id"],
        )

    if "friendships" not in tables:
        op.create_table(
            "friendships",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("friend_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["friend_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "friend_user_id"),
        )
        op.create_index("ix_friendships_user_id", "friendships", ["user_id"])
        op.create_index("ix_friendships_friend_user_id", "friendships", ["friend_user_id"])

    _backfill_usernames(bind)


def downgrade() -> None:
    op.drop_index("ix_friendships_friend_user_id", table_name="friendships")
    op.drop_index("ix_friendships_user_id", table_name="friendships")
    op.drop_table("friendships")
    op.drop_constraint("uq_players_owner_linked_user", "players", type_="unique")
    op.drop_constraint("fk_players_linked_user_id_users", "players", type_="foreignkey")
    op.drop_column("players", "linked_user_id")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
