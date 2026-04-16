"""auction_lots.target_char_id — личное предложение игроку."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n9o0p1q2r3s4"
down_revision: Union[str, None] = "m8n9o0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "auction_lots",
        sa.Column("target_char_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_auction_lots_target_char_id", "auction_lots", ["target_char_id"])


def downgrade() -> None:
    op.drop_index("ix_auction_lots_target_char_id", table_name="auction_lots")
    op.drop_column("auction_lots", "target_char_id")
