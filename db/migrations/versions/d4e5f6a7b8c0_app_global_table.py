"""Таблица app_global для мирового босса и прочего глобального состояния."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c0"
down_revision: Union[str, None] = "c3d4e5f6a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_global",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text("INSERT INTO app_global (id, payload) VALUES (1, '{}')"),
    )


def downgrade() -> None:
    op.drop_table("app_global")
