"""local auth columns on users

Revision ID: 001_local_auth
Revises:
Create Date: 2026-06-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_local_auth"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _user_columns(insp: sa.Inspector) -> set[str]:
    if "users" not in insp.get_table_names():
        return set()
    return {col["name"] for col in insp.get_columns("users")}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = _user_columns(insp)
    if "users" not in insp.get_table_names():
        return
    with op.batch_alter_table("users", schema=None) as batch_op:
        if "password_hash" not in cols:
            batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        if "is_admin" not in cols:
            batch_op.add_column(
                sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if "totp_secret" not in cols:
            batch_op.add_column(sa.Column("totp_secret", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("totp_secret")
        batch_op.drop_column("is_admin")
        batch_op.drop_column("password_hash")
