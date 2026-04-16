"""Таблица game_events — метрики боёв и баланса."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("floor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("class_key", sa.String(length=32), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_events_event_type", "game_events", ["event_type"])
    op.create_index("ix_game_events_created_at", "game_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_game_events_created_at", table_name="game_events")
    op.drop_index("ix_game_events_event_type", table_name="game_events")
    op.drop_table("game_events")
