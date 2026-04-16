"""Таблица promo_redemptions для учёта использованных промокодов."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d4e5f6a7b8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_redemptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_key", sa.String(length=48), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "code_key", name="uq_promo_user_code"),
    )
    op.create_index(op.f("ix_promo_redemptions_code_key"), "promo_redemptions", ["code_key"], unique=False)
    op.create_index(op.f("ix_promo_redemptions_user_id"), "promo_redemptions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_promo_redemptions_user_id"), table_name="promo_redemptions")
    op.drop_index(op.f("ix_promo_redemptions_code_key"), table_name="promo_redemptions")
    op.drop_table("promo_redemptions")
