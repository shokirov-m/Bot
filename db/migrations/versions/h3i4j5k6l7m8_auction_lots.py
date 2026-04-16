"""Таблица auction_lots — аукцион предметов."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h3i4j5k6l7m8"
down_revision: Union[str, None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auction_lots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seller_char_id", sa.Integer(), nullable=False),
        sa.Column("item_data", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("start_price", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("current_bid", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("buyer_char_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["buyer_char_id"], ["characters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_char_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auction_lots_seller_char_id", "auction_lots", ["seller_char_id"])
    op.create_index("ix_auction_lots_buyer_char_id", "auction_lots", ["buyer_char_id"])
    op.create_index("ix_auction_lots_status", "auction_lots", ["status"])
    op.create_index("ix_auction_lots_expires_at", "auction_lots", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_auction_lots_expires_at", table_name="auction_lots")
    op.drop_index("ix_auction_lots_status", table_name="auction_lots")
    op.drop_index("ix_auction_lots_buyer_char_id", table_name="auction_lots")
    op.drop_index("ix_auction_lots_seller_char_id", table_name="auction_lots")
    op.drop_table("auction_lots")
