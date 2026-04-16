"""Таблица promo_offers — промокоды с лимитом и сроком (админка)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_offers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code_key", sa.String(length=48), nullable=False),
        sa.Column("gold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("xp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rune_stones", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_promo_offers_code_key"), "promo_offers", ["code_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_promo_offers_code_key"), table_name="promo_offers")
    op.drop_table("promo_offers")
